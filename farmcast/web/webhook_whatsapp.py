"""Inbound message handling: ground-truth YES/NO + on-demand queries. Text-only replies."""
from __future__ import annotations
import json
import re
from datetime import datetime, timedelta

from farmcast.db import repo
from farmcast.core.location import resolve_location
from farmcast.core.weather import fetch_places
from farmcast.core import rules as R
from farmcast.core.message import load_templates, render_broadcast

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


INTENTS = [
    ("PLANT", r"\b(plant|sow|when plant)\b"),
    ("SPRAY", r"\b(spray|herbicide|pesticide)\b"),
    ("FERTILIZER", r"\b(fertili[sz]er|manure|apply)\b"),
    ("DRY", r"\b(dry|drought|water)\b"),
    ("HELP", r"\b(help|menu|what can you do)\b"),
    ("FORECAST", r"\b(rain|weather|how weather|forecast)\b"),
]

TIME_WORDS = {"today": 0, "tomorrow": 1, "week": 7}


def parse_intent(text: str) -> str:
    t = (text or "").lower()
    for name, pat in INTENTS:
        if re.search(pat, t):
            return name
    return "UNKNOWN"


def extract_place(text: str) -> str:
    """Strip intent/time keywords; remainder is the place name."""
    t = (text or "").lower()
    t = re.sub(r"\b(rain|weather|forecast|how weather|plant|sow|when plant|spray|"
               r"herbicide|pesticide|fertili[sz]er|manure|apply|dry|drought|water|"
               r"help|menu|what can you do|for|in|at|today|tomorrow|week|the)\b", " ", t)
    t = re.sub(r"[?.,!]", " ", t)
    return " ".join(t.split())


def parse_yes_no(text: str) -> str:
    t = (text or "").strip().lower()
    if t in ("yes", "y", "yeah") or re.search(r"\brain\b|\bwet\b|\bwater\b", t) and \
            not re.search(r"\bno\b", t):
        # 'rain fall' etc counts as YES; plain YES too
        if t in ("yes", "y", "yeah") or "rain" in t or "wet" in t:
            return "YES"
    if t in ("no", "n", "nah") or re.search(r"\bno\b|\bdry\b|\bsun\b", t):
        # but 'no rain' etc -> NO
        if "rain" not in t or t.startswith("no"):
            # 'no rain here' => NO (did not rain)
            if "rain" in t and "no" in t:
                return "NO"
            if "rain" in t and ("fall" in t or "wet" in t):
                return "YES"
            return "NO" if ("no" in t or "dry" in t or "sun" in t) else "OTHER"
    if re.search(r"\brain\b.*\bfall\b|\bheavy rain\b|\bsteady rain\b|\blight rain\b", t):
        return "YES"
    if re.search(r"\bcompletely dry\b|\bno rain\b|\bnot enough\b", t):
        return "NO"
    return "OTHER"


def answer_query(phone: str, text: str) -> str:
    """Main entry: returns reply text (already sent by caller or returned for sending)."""
    t = load_templates("english")
    farmer = repo.find_farmer_by_phone(phone)
    if not farmer:
        return t.get("not_registered", "Not registered.")

    # 1. pending clarification? (farmer replies "1" / "2")
    con = repo.connect()
    pend = con.execute(
        "SELECT * FROM pending_clarifications WHERE farmer_id=? ORDER BY id DESC LIMIT 1",
        (farmer["id"],)).fetchone()
    con.close()
    stripped = (text or "").strip()
    if pend and stripped in ("1", "2", "3", "4", "5"):
        opts = json.loads(pend["options"])
        idx = int(stripped) - 1
        if 0 <= idx < len(opts):
            sel = opts[idx]
            con = repo.connect()
            con.execute("DELETE FROM pending_clarifications WHERE id=?", (pend["id"],))
            con.commit()
            con.close()
            return _answer_for_locality(farmer, text, "FORECAST", sel, t)
        return t.get("clarify", "Which place?")

    # 2. ground-truth YES/NO (short replies without intent keywords)
    intent = parse_intent(text)
    if intent == "UNKNOWN" and len(stripped.split()) <= 6:
        verdict = parse_yes_no(text)
        if verdict in ("YES", "NO"):
            con = repo.connect()
            loc_id = farmer.get("locality_id")
            yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
            con.execute("INSERT INTO reports(farmer_id,locality_id,asked_for_date,"
                        "reply,raw_text) VALUES(?,?,?,?,?)",
                        (farmer["id"], loc_id, yesterday, verdict, text))
            con.commit()
            con.close()
            return t.get("yes_thanks", "Thank you.")
        # conversational short message -> AI (falls back to menu)
        from farmcast.core import ai as _ai
        return _ai.chat(text, farmer) or t.get("help_menu", "")

    if intent == "HELP":
        return t.get("help_menu", "")
    if intent == "UNKNOWN":
        # longer free text -> AI (falls back to menu)
        from farmcast.core import ai as _ai
        return _ai.chat(text, farmer) or t.get("help_menu", "")

    # 3. on-demand: extract place or default to own locality
    place_q = extract_place(text)
    if not place_q:
        con = repo.connect()
        L = con.execute("SELECT * FROM localities WHERE id=?",
                        (farmer["locality_id"],)).fetchone()
        con.close()
        L = dict(L)
        sel = {"name": L["name"], "lat": L["lat"], "lon": L["lon"],
               "elevation_m": L.get("elevation_m") or 0,
               "division": L.get("division") or "", "id": L["id"]}
        return _answer_for_locality(farmer, text, intent, sel, t)

    res = resolve_location(place_q)
    if res.status == "not_found":
        return t.get("unknown_place", "Unknown place.")
    if res.status == "ambiguous":
        opts = [{"name": o.name, "lat": o.lat, "lon": o.lon,
                 "elevation_m": o.elevation_m, "division": o.division}
                for o in res.options[:5]]
        expires = (datetime.now() +
                   timedelta(minutes=settings.CLARIFICATION_TTL_MINUTES)).isoformat()
        con = repo.connect()
        con.execute("DELETE FROM pending_clarifications WHERE farmer_id=?",
                    (farmer["id"],))
        con.execute("INSERT INTO pending_clarifications(farmer_id,options,expires_at)"
                    " VALUES(?,?,?)", (farmer["id"], json.dumps(opts), expires))
        con.commit()
        con.close()
        lines = [t.get("clarify", "Which place?")]
        for i, o in enumerate(opts, 1):
            lines.append(f"{i}. {o['name']} ({o['division']})")
        return "\n".join(lines)
    L = res.locality
    sel = {"name": L.name, "lat": L.lat, "lon": L.lon,
           "elevation_m": L.elevation_m, "division": L.division}
    prefix = ""
    if res.outside_nw:
        prefix = t.get("outside_nw", "").format(place=L.name) + "\n"
    return prefix + _answer_for_locality(farmer, text, intent, sel, t)


def _answer_for_locality(farmer: dict, raw_text: str, intent: str,
                         sel: dict, t: dict) -> str:
    from datetime import date as _date
    lid = sel.get("id")
    if lid is None:
        lid = repo.get_or_create_locality(sel["name"], sel["lat"], sel["lon"],
                                          sel.get("elevation_m") or 0,
                                          sel.get("division") or "")
    fc = fetch_places([{"key": str(lid), "lat": sel["lat"],
                        "lon": sel["lon"],
                        "elev": sel.get("elevation_m") or 0}])[str(lid)]
    con = repo.connect()
    L = con.execute("SELECT * FROM localities WHERE id=?", (lid,)).fetchone()
    con.close()
    L = dict(L)
    bias = L.get("manual_bias") or 1.0
    p48 = round(fc.p48 * bias, 1)
    cat = R.categorize(p48, fc.daily or [])
    fl = R.flags(fc.tmin, L.get("elevation_m") or 0, fc.wind_max, p48,
                 round(fc.p24 * bias, 1))
    fid = repo.save_forecast(lid, _date.today().isoformat(), fc, cat, fl)

    if intent == "PLANT":
        idx = R.next_good_plant_day(fc.daily or [])
        body = (render_broadcast(farmer.get("name") or "farmer", L["name"],
                                 cat, p48, farmer.get("crop") or "maize",
                                 {"flags": fl}, farmer.get("language") or "english")
                + f"\n{t.get('next_plant_day', '{day}').format(day=R.day_label(idx))}"
                if idx is not None else
                render_broadcast(farmer.get("name") or "farmer", L["name"],
                                 cat, p48, farmer.get("crop") or "maize",
                                 {"flags": fl}, farmer.get("language") or "english")
                + f"\n{t.get('no_plant_day', '')}")
    elif intent == "SPRAY":
        idx = R.next_good_spray_day(fc.daily or [], fc.wind_max)
        body = (t.get("next_spray_day", "{day}").format(day=R.day_label(idx))
                if idx is not None else t.get("no_spray_day", ""))
    elif intent == "FERTILIZER":
        idx = R.next_good_fert_day(fc.daily or [])
        body = (t.get("next_fert_day", "{day}").format(day=R.day_label(idx))
                if idx is not None else t.get("no_spray_day", ""))
    elif intent == "DRY":
        body = f"{t.get('forecast_dryspell', '')} ({L['name']})"
    else:
        body = render_broadcast(farmer.get("name") or "farmer", L["name"],
                                cat, p48, farmer.get("crop") or "maize",
                                {"flags": fl}, farmer.get("language") or "english")
    con = repo.connect()
    con.execute("INSERT INTO queries(farmer_id,raw_text,intent,resolved_locality_id,"
                "response) VALUES(?,?,?, ?,?)",
                (farmer["id"], raw_text, intent, lid, body))
    con.commit()
    con.close()
    repo.log_message(farmer["id"], fid, "query_reply", body, "sent")
    return body
