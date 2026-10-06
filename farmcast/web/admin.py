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
    if settings.ADMIN_TOKEN and token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="bad admin token")


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


@router.get("/zones")
def zones(x_admin_token: str | None = Header(default=None)):
    """Live forecast per zone (division). One batched Open-Meteo call, cached daily."""
    guard(x_admin_token)
    from farmcast.core import zones as Z
    zs = Z.all_zones()
    if not zs:
        return []
    places = [{"key": z["division"], "lat": z["lat"], "lon": z["lon"],
               "elev": z["elev"] or 0} for z in zs]
    fc = fetch_places(places)
    con = repo.connect()
    counts = {r["division"]: r["n"] for r in con.execute(
        """SELECT l.division AS division, COUNT(f.id) AS n FROM localities l
           LEFT JOIN farmers f ON f.locality_id=l.id AND f.active=1
           GROUP BY l.division""").fetchall()}
    elev = {r["division"]: r["sources"] for r in con.execute(
        "SELECT division, GROUP_CONCAT(DISTINCT elev_source) AS sources "
        "FROM localities GROUP BY division").fetchall()}
    con.close()
    out = []
    for z in zs:
        f = fc[z["division"]]
        cat = R.categorize(f.p48, f.daily or [])
        out.append({
            "zone": z["division"], "localities": z["localities"],
            "farmers": counts.get(z["division"], 0),
            "lat": round(z["lat"], 4), "lon": round(z["lon"], 4),
            "elev_m": int(z["elev"] or 0),
            "elev_sources": (elev.get(z["division"]) or "").split(","),
            "p24": f.p24, "p48": f.p48, "p72": f.p72,
            "prob_max": f.prob_max, "tmin": f.tmin, "tmax": f.tmax,
            "wind_max": f.wind_max, "daily": f.daily,
            "category": cat,
            "flags": R.flags(f.tmin, z["elev"] or 0, f.wind_max, f.p48, f.p24),
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
