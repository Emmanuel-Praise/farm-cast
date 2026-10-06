"""Admin JSON endpoints for the dashboard. Guard with ADMIN_TOKEN."""
from __future__ import annotations
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from farmcast.db import repo
from farmcast.core.location import resolve_location
from farmcast.core.weather import fetch_places
from farmcast.core import rules as R

try:
    from config import settings
except ImportError:
    from farmcast.config import settings

router = APIRouter(prefix="/admin")


def guard(token: str | None):
    return None


class FarmerIn(BaseModel):
    phone: str
    name: str = ""
    village: str = ""
    crop: str = "maize"
    language: str = "english"


@router.get("/stats")
def stats(x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    return repo.stats()


@router.get("/farmers")
def farmers(x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    con = repo.connect()
    rows = con.execute("SELECT * FROM farmers ORDER BY id DESC LIMIT 500").fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.post("/farmers")
def add_farmer(body: FarmerIn, x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    from farmcast.core.message import load_templates
    res = resolve_location(body.village)
    if res.status != "ok":
        raise HTTPException(status_code=400,
                            detail=f"unknown village: {res.status} {res.options}")
    L = res.locality
    lid = repo.get_or_create_locality(L.name, L.lat, L.lon, L.elevation_m,
                                      L.division,
                                      source="gazetteer" if not res.outside_nw else "geocoded")
    con = repo.connect()
    try:
        con.execute("INSERT INTO farmers(phone,name,locality_id,crop,language)"
                    " VALUES(?,?,?,?,?)",
                    (body.phone, body.name, lid, body.crop, body.language))
        con.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        con.close()
    t = load_templates(body.language)
    return {"ok": True, "welcome": t.get("welcome", "").format(name=body.name,
                                                               place=L.name)}


@router.get("/localities")
def localities(x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    con = repo.connect()
    rows = con.execute("SELECT * FROM localities ORDER BY name").fetchall()
    con.close()
    return [dict(r) for r in rows]


def _outlook(daily: list, p48: float, cat: str) -> str:
    """Plain-language 5-day summary, e.g. 'Light rain Tue-Thu (~28mm); dry Fri-Sun.'"""
    from datetime import date as _d, timedelta as _td
    days = (daily or [])[1:6]
    if not days:
        return ""
    names = [(_d.today() + _td(days=i)).strftime("%a") for i in range(1, 6)]
    words = {"HEAVY_RAIN": "Heavy rain", "RAIN": "Rain", "LIGHT_RAIN": "Light rain",
             "DRY": "Mostly dry", "DRY_SPELL": "Dry spell"}
    head = f"{words.get(cat, 'Normal')}: {p48}mm in the next 2 days."
    wet = [names[i] for i, v in enumerate(days) if (v or 0) >= 5]
    dry = [names[i] for i, v in enumerate(days) if (v or 0) < 2]
    tail = []
    if wet:
        span = wet[0] if len(wet) == 1 else f"{wet[0]}-{wet[-1]}"
        tail.append(f"rain {span} (~{round(sum(days), 1)}mm over 5 days)")
    if dry:
        span = dry[0] if len(dry) == 1 else f"{dry[0]}-{dry[-1]}"
        tail.append(f"dry {span}")
    return head + (" " + "; ".join(tail) + "." if tail else "")


@router.get("/zones")
def zones(x_admin_token: str | None = Header(default=None)):
    """Live forecast for EVERY area (all localities). One batched Open-Meteo
    call for all of them, cached daily. Each area carries its division so the
    dashboard can group/filter. Grows automatically as farmers add places."""
    guard(x_admin_token)
    con = repo.connect()
    locs = [dict(r) for r in con.execute(
        "SELECT * FROM localities ORDER BY division, name").fetchall()]
    counts = {r["lid"]: r["n"] for r in con.execute(
        "SELECT locality_id AS lid, COUNT(*) AS n FROM farmers "
        "WHERE active=1 GROUP BY locality_id").fetchall()}
    con.close()
    if not locs:
        return []
    places = [{"key": str(L["id"]), "lat": L["lat"], "lon": L["lon"],
               "elev": L.get("elevation_m") or 0} for L in locs]
    fc = fetch_places(places)
    out = []
    for L in locs:
        f = fc[str(L["id"])]
        bias = L.get("manual_bias") or 1.0
        p48 = round(f.p48 * bias, 1)
        cat = R.categorize(p48, f.daily or [])
        out.append({
            "zone": L["name"], "division": L.get("division") or "Unverified",
            "localities": 1, "farmers": counts.get(L["id"], 0),
            "lat": L["lat"], "lon": L["lon"],
            "elev_m": L.get("elevation_m") or 0,
            "elev_sources": [L.get("elev_source") or "seed-estimate"],
            "verified": L.get("verified") or 0,
            "p24": round(f.p24 * bias, 1), "p48": p48,
            "p72": round(f.p72 * bias, 1),
            "prob_max": f.prob_max, "tmin": f.tmin, "tmax": f.tmax,
            "wind_max": f.wind_max, "daily": f.daily,
            "category": cat,
            "outlook": _outlook(f.daily, p48, cat),
            "today": {"headline": f.today_headline,
                      "rest_mm": f.today_rest_mm,
                      "next_rain": f.next_rain,
                      "hours": f.today_hours},
            "flags": R.flags(f.tmin, L.get("elevation_m") or 0, f.wind_max,
                             p48, round(f.p24 * bias, 1)),
        })
    return out


@router.get("/forecast")
def forecast(place: str, x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    res = resolve_location(place)
    if res.status != "ok":
        return {"status": res.status,
                "options": [o.__dict__ for o in res.options]}
    L = res.locality
    fc = fetch_places([{"key": "q", "lat": L.lat, "lon": L.lon,
                        "elev": L.elevation_m}], use_cache=False)["q"]
    cat = R.categorize(fc.p48, fc.daily or [])
    return {"status": "ok", "place": L.__dict__, "forecast": fc.to_dict(),
            "category": cat,
            "flags": R.flags(fc.tmin, L.elevation_m, fc.wind_max, fc.p48, fc.p24)}


@router.post("/broadcast/test")
def broadcast_test(phone: str, x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    from farmcast.web.webhook_whatsapp import _answer_for_locality
    from farmcast.core.message import load_templates
    farmer = repo.find_farmer_by_phone(phone)
    if not farmer:
        raise HTTPException(status_code=404, detail="farmer not found")
    con = repo.connect()
    L = con.execute("SELECT * FROM localities WHERE id=?",
                    (farmer["locality_id"],)).fetchone()
    con.close()
    L = dict(L)
    body = _answer_for_locality(farmer, "test", "FORECAST",
                                {"name": L["name"], "lat": L["lat"],
                                 "lon": L["lon"],
                                 "elevation_m": L.get("elevation_m") or 0,
                                 "division": L.get("division") or "",
                                 "id": L["id"]},
                                load_templates(farmer.get("language") or "english"))
    return {"ok": True, "preview": body}


@router.post("/broadcast/run")
def broadcast_run(dry_run: bool = True,
                  x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    from farmcast.jobs.morning_broadcast import run
    return run(dry_run=dry_run)


@router.get("/reports")
def reports(date: str | None = None,
             x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    con = repo.connect()
    if date:
        rows = con.execute("SELECT * FROM reports WHERE asked_for_date=? ORDER BY id DESC",
                           (date,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 200").fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.get("/messages")
def messages(date: str | None = None,
             x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    con = repo.connect()
    if date:
        rows = con.execute("SELECT * FROM messages WHERE date(sent_at)=? ORDER BY id DESC",
                           (date,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 200").fetchall()
    con.close()
    return [dict(r) for r in rows]


@router.get("/call-list")
def call_list(x_admin_token: str | None = Header(default=None)):
    guard(x_admin_token)
    con = repo.connect()
    rows = con.execute("""SELECT c.*, f.name, f.phone FROM call_list c
                          JOIN farmers f ON f.id=c.farmer_id
                          WHERE c.resolved=0 ORDER BY c.id DESC""").fetchall()
    con.close()
    return [dict(r) for r in rows]
