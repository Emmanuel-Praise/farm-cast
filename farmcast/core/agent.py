"""Model-first agent: every farmer message goes to the LLM.

Flow per message:
  1. Fast paths (not responses): YES/NO ground-truth logging, pending-clarification
     number selection.
  2. LLM step 1 (classify): does this need weather? which place? which horizon?
     Non-weather messages are answered directly by the model in the same call.
  3. Code executes: resolve place (own area / gazetteer / geocoding), fetch
     Open-Meteo, apply rule thresholds, look up crop advice (agronomist data).
  4. LLM step 2 (compose): model writes the final reply using ONLY the numbers
     it is given. It also asks for the area itself when the place is missing
     or ambiguous.

Nothing user-visible is templated: all reply text is model-composed. The old
regex/template pipeline remains only as a total-AI-outage fallback so a farmer
is never left without an answer.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timedelta, date

from farmcast.db import repo
from farmcast.core.location import resolve_location
from farmcast.core.weather import fetch_places
from farmcast.core import rules as R

try:
    from config import settings
except ImportError:
    from farmcast.config import settings
try:
    from config import crops as crops_cfg
except ImportError:
    from farmcast.config import crops as crops_cfg

from farmcast.core import ai as ai_client
from farmcast.web.webhook_whatsapp import parse_yes_no

CLASSIFY_SYSTEM = (
    "You are the intent parser for FarmCast, a farming advisor in Northwest "
    "Cameroon. Return ONLY a JSON object, no other text. Schema: "
    '{"need_weather": true/false, '
    '"place": "village/town mentioned, or null", '
    '"self_area": true/false (farmer means their own area: my area, my farm, here), '
    '"horizon": "today"|"tomorrow"|"48h"|"week", '
    '"reply_direct": "if need_weather is false, write the full reply here (simple English, '
    'max 500 chars); else empty string"}. '
    "need_weather is true for anything about rain, weather, forecast, planting/spraying/"
    "fertilizer timing, dry spells. Greetings, thanks, and chit-chat get need_weather false "
    "with a warm reply_direct."
)

COMPOSE_SYSTEM = (
    "You are FarmCast, a friendly farming advisor for smallholders in Northwest "
    "Cameroon. Write the reply in simple English, max 600 characters, WhatsApp style. "
    "RULES: (1) Always state the MM figure together with its MM_LABEL, e.g. "
    "'7.8mm in the next 2 days'. Never give a forecast without its number. "
    "(2) Never write internal codes like LIGHT_RAIN, HEAVY_RAIN, DRY_SPELL — use "
    "plain words (light rain, heavy rain, dry spell). "
    "(3) Use ONLY the numbers in WEATHER below — never invent rainfall or "
    "temperature figures. (4) The farmer farms in AREA — never ask which village "
    "they farm in and never mention other villages unless asked. "
    "(5) If ASK_AREA is true, ask which village or town they want the forecast for. "
    "If OPTIONS are given, list them by number and ask them to pick one. "
    "(6) End with one line of practical advice based on ADVICE."
)


def _ctx(farmer: dict) -> dict:
    con = repo.connect()
    L = con.execute("SELECT * FROM localities WHERE id=?",
                    (farmer["locality_id"],)).fetchone()
    con.close()
    L = dict(L)
    return {"name": farmer.get("name") or "farmer",
            "crop": farmer.get("crop") or "maize",
            "area": L["name"], "area_id": L["id"],
            "lat": L["lat"], "lon": L["lon"],
            "elev": L.get("elevation_m") or 0,
            "division": L.get("division") or ""}


def _llm_json(system: str, user: str) -> dict:
    """One classify call with a single retry. Returns {} on failure."""
    for attempt in range(2):
        prompt = user if attempt == 0 else user + "\n\nReturn ONLY the JSON object."
        out = ai_client.chat_raw(system, prompt)
        if out:
            m = re.search(r"\{.*\}", out, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
    return {}


def _pending_options(farmer_id: int) -> tuple[dict | None, list]:
    con = repo.connect()
    row = con.execute(
        "SELECT * FROM pending_clarifications WHERE farmer_id=? ORDER BY id DESC LIMIT 1",
        (farmer_id,)).fetchone()
    con.close()
    if not row:
        return None, []
    row = dict(row)
    try:
        if row.get("expires_at") and datetime.fromisoformat(row["expires_at"]) < datetime.now():
            con = repo.connect()
            con.execute("DELETE FROM pending_clarifications WHERE id=?", (row["id"],))
            con.commit()
            con.close()
            return None, []
    except Exception:
        pass
    try:
        return row, json.loads(row["options"])
    except Exception:
        return None, []


def _pick_option(text: str, options: list) -> dict | None:
    s = (text or "").strip().lower()
    if s.isdigit():
        i = int(s) - 1
        if 0 <= i < len(options):
            return options[i]
    for o in options:
        if o.get("name") and o["name"].lower() in s:
            return o
    return None


def _weather_payload(sel: dict, horizon: str, crop: str) -> dict:
    """Fetch + rules + advice. Pure data for the composer — no reply text."""
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
    p24 = round(fc.p24 * bias, 1)
    p48 = round(fc.p48 * bias, 1)
    cat = R.categorize(p48, fc.daily or [])
    fl = R.flags(fc.tmin, L.get("elevation_m") or 0, fc.wind_max, p48, p24)
    fid = repo.save_forecast(lid, date.today().isoformat(), fc, cat, fl)
    daily = fc.daily or []
    week_sum = round(sum(daily[:7]), 1)
    mm_labels = {"today": "next 24 hours", "tomorrow": "next 2 days",
                 "48h": "next 2 days", "week": "next 7 days"}
    mm = {"today": p24, "tomorrow": p48, "48h": p48, "week": week_sum}.get(
        horizon, p48)
    return {
        "place": L["name"], "horizon": horizon, "mm": mm,
        "mm_label": mm_labels.get(horizon, "next 2 days"),
        "p24": p24, "p48": p48, "week_sum": week_sum,
        "category": cat, "flags": fl,
        "tmin": fc.tmin, "tmax": fc.tmax, "wind_max": fc.wind_max,
        "daily": daily,
        "advice": crops_cfg.advice_for(cat, crop),
        "plant_day": R.day_label(R.next_good_plant_day(fc.daily or [])),
        "forecast_id": fid, "locality_id": lid,
    }


def _compose(farmer_ctx: dict, question: str, weather: dict | None = None,
             ask_area: bool = False, options: list | None = None) -> str:
    user = (f"FARMER: {farmer_ctx['name']} grows {farmer_ctx['crop']} in "
            f"{farmer_ctx['area']}.\nQUESTION: {question}\n")
    key_fact = ""
    if weather:
        key_fact = (f"{weather['mm']}mm in the {weather['mm_label']} "
                    f"in {weather['place']}")
        user += (f"KEY FACT (must appear verbatim in your reply): {key_fact}\n"
                 f"WEATHER: {json.dumps(weather)}\nADVICE: {weather.get('advice', '')}\n")
    if ask_area:
        user += "ASK_AREA: true (no usable place was given)\n"
    if options:
        user += f"OPTIONS: {json.dumps([{'name': o.get('name'), 'division': o.get('division')} for o in options])}\n"
    for attempt in range(2):
        out = ai_client.chat_raw(
            COMPOSE_SYSTEM,
            user if attempt == 0 else user + "\n\nREMINDER: include the KEY FACT verbatim.",
            temperature=0.4 if attempt == 0 else 0.2)
        out = (out or "").strip()
        if not out:
            continue
        if not key_fact or (str(weather["mm"]) in out and weather["place"] in out):
            return out
        print(f"[agent] compose missed key fact ({key_fact}), retrying")
    if out:
        return out
    # Model failed twice: data-driven backstop (only on AI failure, never normal path).
    if weather:
        return (f"{farmer_ctx['name']}, for {weather['place']}: {key_fact}. "
                f"{weather.get('advice', '')}")
    return ""


def _log(farmer_id: int, raw: str, intent: str, lid, body: str, fid=None):
    try:
        con = repo.connect()
        con.execute("INSERT INTO queries(farmer_id,raw_text,intent,resolved_locality_id,"
                    "response) VALUES(?,?,?,?,?)", (farmer_id, raw, intent, lid, body))
        con.commit()
        con.close()
        repo.log_message(farmer_id, fid, "query_reply", body, "sent")
    except Exception as e:
        print(f"[agent] log failed: {e}")


def extract_name(text: str) -> str | None:
    """Pull a plausible name out of a reply. Data extraction, not a response."""
    s = (text or "").strip()
    s = re.sub(r"(?i)\b(my name is|my names are|i am|i'm|im |this is|call me)\b", " ", s)
    s = re.sub(r"[?.,!0-9]", " ", s)
    s = " ".join(s.split())
    if not re.fullmatch(r"[A-Za-z][A-Za-z '\-]{1,39}", s):
        return None
    greetings = {"hello", "hi", "hey", "morning", "afternoon", "evening",
                 "yes", "no", "ok", "okay", "thanks", "thank you", "good"}
    if all(w in greetings for w in s.lower().split()):
        return None
    return s.title()


def _onboard_get(phone: str) -> dict | None:
    con = repo.connect()
    row = con.execute("SELECT * FROM onboarding WHERE phone=?", (phone,)).fetchone()
    con.close()
    return dict(row) if row else None


def _onboard_save(phone: str, step: str, name: str = "", options: list | None = None):
    con = repo.connect()
    con.execute("INSERT INTO onboarding(phone,step,name,options) VALUES(?,?,?,?) "
                "ON CONFLICT(phone) DO UPDATE SET step=excluded.step, name=excluded.name,"
                " options=excluded.options",
                (phone, step, name, json.dumps(options or [])))
    con.commit()
    con.close()


def _onboard_done(phone: str):
    con = repo.connect()
    con.execute("DELETE FROM onboarding WHERE phone=?", (phone,))
    con.commit()
    con.close()


def _onboard_ask_place(text: str) -> str | None:
    """Model extracts the village/town from a free-form reply. Falls back to keywords."""
    out = ai_client.chat_raw(
        "Extract the village, town or area name from the message. "
        "Return ONLY JSON: {\"place\": \"name or null\"}.",
        f"MESSAGE: {text}")
    if out:
        m = re.search(r"\{.*\}", out, re.DOTALL)
        if m:
            try:
                p = json.loads(m.group(0)).get("place")
                if p:
                    return str(p)
            except Exception:
                pass
    from farmcast.web.webhook_whatsapp import extract_place
    return extract_place(text) or None


def _handle_new_sender(phone: str, text: str) -> str:
    """Auto-registration: first text -> name -> location -> daily reports."""
    ob = _onboard_get(phone)
    if not ob:
        _onboard_save(phone, "name")
        out = ai_client.chat_raw(
            COMPOSE_SYSTEM,
            "Someone just texted FarmCast for the first time. Welcome them warmly "
            "and ask their name. Max 300 characters.")
        return out.strip() if out else "Welcome to FarmCast. What is your name?"

    if ob["step"] == "name":
        name = extract_name(text)
        if not name:
            out = ai_client.chat_raw(
                COMPOSE_SYSTEM,
                f"I asked a new farmer for their name and they replied: {text}\n"
                "Ask for their name again, simply.")
            return out.strip() if out else "Sorry, I didn't get your name. What is your name?"
        _onboard_save(phone, "location", name=name)
        out = ai_client.chat_raw(
            COMPOSE_SYSTEM,
            f"New farmer {name} just gave their name. Greet them by name and ask "
            "which village or town their farm is in. Max 300 characters.")
        return out.strip() if out else f"Thanks {name}. Which village or town is your farm in?"

    # step == location
    name = ob.get("name") or "farmer"
    if ob.get("options"):
        try:
            options = json.loads(ob["options"])
        except Exception:
            options = []
        sel = _pick_option(text, options)
        if sel:
            return _finish_onboarding(phone, name, sel)
    place = _onboard_ask_place(text)
    if not place:
        out = ai_client.chat_raw(
            COMPOSE_SYSTEM,
            f"{name} replied '{text}' when asked for their village. "
            "Ask again for the village or town name.")
        return out.strip() if out else f"{name}, which village or town is your farm in?"
    res = resolve_location(place)
    if res.status == "ok":
        L = res.locality
        return _finish_onboarding(phone, name,
                                  {"name": L.name, "lat": L.lat, "lon": L.lon,
                                   "elevation_m": L.elevation_m, "division": L.division})
    if res.status == "ambiguous":
        opts = [{"name": o.name, "lat": o.lat, "lon": o.lon,
                 "elevation_m": o.elevation_m, "division": o.division}
                for o in res.options[:5]]
        _onboard_save(phone, "location", name=name, options=opts)
        body = _compose({"name": name, "crop": "maize", "area": opts[0]["name"]},
                        text, options=opts)
        return body or f"Which one do you mean, {name}? Reply with the number."
    out = ai_client.chat_raw(
        COMPOSE_SYSTEM,
        f"{name} said their farm is in '{place}' but I can't find that place. "
        "Ask them to try another nearby village or town name.")
    return out.strip() if out else f"I couldn't find '{place}'. Try another nearby village name."


def _finish_onboarding(phone: str, name: str, sel: dict) -> str:
    lid = repo.get_or_create_locality(sel["name"], sel["lat"], sel["lon"],
                                      sel.get("elevation_m") or 0,
                                      sel.get("division") or "")
    con = repo.connect()
    con.execute("INSERT OR IGNORE INTO farmers(phone,name,locality_id,crop,language)"
                " VALUES(?,?,?,?,?)", (phone, name, lid, "maize", "english"))
    con.execute("UPDATE farmers SET active=1, locality_id=? WHERE phone=?", (lid, phone))
    con.commit()
    con.close()
    _onboard_done(phone)
    farmer = repo.find_farmer_by_phone(phone)
    payload = _weather_payload({"name": sel["name"], "lat": sel["lat"],
                                "lon": sel["lon"],
                                "elevation_m": sel.get("elevation_m") or 0,
                                "division": sel.get("division") or "", "id": lid},
                               "48h", "maize")
    body = _compose({"name": name, "crop": "maize", "area": sel["name"]},
                    "registration complete", weather=payload)
    if body:
        _log(farmer["id"], "registration", "REGISTER", lid, body,
             payload["forecast_id"])
        return body
    return (f"Welcome {name}. You will now get a weather report every morning "
            f"at 6 o'clock for {sel['name']}.")

def respond(phone: str, text: str) -> str:
    """Main entry: model-first reply. Never raises; never returns empty."""
    text = (text or "").strip()
    if not text:
        return "I didn't catch that. Please send your message again."
    farmer = repo.find_farmer_by_phone(phone)
    if not farmer:
        # Auto-registration: no manual entry, onboarding over chat.
        try:
            return _handle_new_sender(phone, text)
        except Exception as e:
            print(f"[agent] onboarding failed: {e}")
            return "Welcome to FarmCast. What is your name?"

    # Crop update: "my crop is beans"
    m = re.match(r"(?i)^my crop is (.+?)[?.!]*$", text.strip())
    if m:
        crop = m.group(1).strip().lower()
        if crop in crops_cfg.SUPPORTED_CROPS:
            try:
                con = repo.connect()
                con.execute("UPDATE farmers SET crop=? WHERE id=?", (crop, farmer["id"]))
                con.commit()
                con.close()
            except Exception as e:
                print(f"[agent] crop update failed: {e}")
            farmer["crop"] = crop
            body = _compose(_ctx(farmer),
                            f"The farmer now grows {crop}. Confirm briefly.")
            return body or f"Noted. I will give you advice for {crop} from now on."

    ctx = _ctx(farmer)
    pend, options = _pending_options(farmer["id"])
    if options:
        sel = _pick_option(text, options)
        if sel:
            con = repo.connect()
            con.execute("DELETE FROM pending_clarifications WHERE farmer_id=?",
                        (farmer["id"],))
            con.commit()
            con.close()
            payload = _weather_payload(sel, "48h", ctx["crop"])
            body = _compose(ctx, text, weather=payload)
            if body:
                _log(farmer["id"], text, "FORECAST", payload["locality_id"],
                     body, payload["forecast_id"])
                return body

    # Fast path 2: YES/NO ground-truth (functional, not a reply).
    if len(text.split()) <= 6:
        verdict = parse_yes_no(text)
        if verdict in ("YES", "NO"):
            try:
                con = repo.connect()
                con.execute("INSERT INTO reports(farmer_id,locality_id,asked_for_date,"
                            "reply,raw_text) VALUES(?,?,?,?,?)",
                            (farmer["id"], farmer["locality_id"],
                             (date.today()).isoformat(), verdict, text))
                con.commit()
                con.close()
            except Exception as e:
                print(f"[agent] report log failed: {e}")
            body = _compose(ctx, f"The farmer replied '{text}' to our rain check. Thank them briefly.")
            if body:
                return body
            # total AI outage: minimal thanks (only when models are down)
            return "Thank you. Your report has been recorded."

    # Main path: model decides.
    cls = _llm_json(CLASSIFY_SYSTEM,
                    f"FARMER: {ctx['name']} grows {ctx['crop']} in {ctx['area']}.\n"
                    f"MESSAGE: {text}")
    if cls and not cls.get("need_weather"):
        direct = (cls.get("reply_direct") or "").strip()
        if direct:
            _log(farmer["id"], text, "CHAT", ctx["area_id"], direct)
            return direct

    if cls and cls.get("need_weather"):
        from farmcast.web.webhook_whatsapp import is_self_reference
        horizon = cls.get("horizon") or "48h"
        # Own area: model flag OR deterministic phrase match (model is
        # inconsistent on "my area", so the regex decides, not the model).
        if cls.get("self_area") or is_self_reference(text):
            payload = _weather_payload(
                {"name": ctx["area"], "lat": ctx["lat"], "lon": ctx["lon"],
                 "elevation_m": ctx["elev"], "division": ctx["division"],
                 "id": ctx["area_id"]},
                horizon, ctx["crop"])
            body = _compose(ctx, text, weather=payload)
            if body:
                _log(farmer["id"], text, "FORECAST", payload["locality_id"],
                     body, payload["forecast_id"])
                return body
        if cls.get("place"):
            res = resolve_location(cls["place"])
            if res.status == "ok":
                L = res.locality
                payload = _weather_payload(
                    {"name": L.name, "lat": L.lat, "lon": L.lon,
                     "elevation_m": L.elevation_m, "division": L.division},
                    horizon, ctx["crop"])
                prefix = ""
                if res.outside_nw:
                    prefix = f"NOTE: {L.name} is outside Northwest Region. "
                body = _compose(ctx, text, weather=payload)
                if body:
                    _log(farmer["id"], text, "FORECAST", payload["locality_id"],
                         prefix + body, payload["forecast_id"])
                    return prefix + body
            if res.status == "ambiguous":
                opts = [{"name": o.name, "lat": o.lat, "lon": o.lon,
                         "elevation_m": o.elevation_m, "division": o.division}
                        for o in res.options[:5]]
                expires = (datetime.now() + timedelta(
                    minutes=settings.CLARIFICATION_TTL_MINUTES)).isoformat()
                con = repo.connect()
                con.execute("DELETE FROM pending_clarifications WHERE farmer_id=?",
                            (farmer["id"],))
                con.execute("INSERT INTO pending_clarifications(farmer_id,options,expires_at)"
                            " VALUES(?,?,?)",
                            (farmer["id"], json.dumps(opts), expires))
                con.commit()
                con.close()
                body = _compose(ctx, text, options=opts)
                if body:
                    _log(farmer["id"], text, "CLARIFY", None, body)
                    return body
        # No usable place at all: model asks for the area itself.
        body = _compose(ctx, text, ask_area=True)
        if body:
            _log(farmer["id"], text, "ASK_AREA", ctx["area_id"], body)
            return body

    # Total AI outage: legacy pipeline so the farmer still gets an answer.
    try:
        from farmcast.web.webhook_whatsapp import answer_query as legacy
        out = legacy(phone, text)
        if out:
            return out
    except Exception as e:
        print(f"[agent] legacy fallback failed: {e}")
    return "Sorry, I had trouble just now. Please ask again in a moment."
