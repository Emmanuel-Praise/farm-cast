"""Dynamic zones: every locality in the Northwest belongs to a zone.

A zone == a Division (Mezam, Momo, Bui, Boyo, Donga-Mantung, Menchum,
Ngo-Ketunjia, ...). Nothing is hardcoded: the zone list is derived from the
localities table, and any lat/lon is classified by nearest locality
(+ free reverse-geocode fallback). No mock data anywhere.
"""
from __future__ import annotations
import math
import requests

from farmcast.db import repo


def all_zones() -> list[dict]:
    """Zones present in the DB: division + centroid coords + locality count."""
    con = repo.connect()
    rows = con.execute(
        "SELECT division, COUNT(*) n, AVG(lat) lat, AVG(lon) lon, AVG(elevation_m) elev "
        "FROM localities WHERE division IS NOT NULL AND division<>'' "
        "GROUP BY division ORDER BY n DESC").fetchall()
    con.close()
    return [{"division": r["division"], "localities": r["n"],
             "lat": r["lat"], "lon": r["lon"], "elev": r["elev"]} for r in rows]


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    R = 6371.0
    dlat, dlon = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    h = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def nearest_locality(lat: float, lon: float) -> tuple[dict | None, float]:
    """(locality row or None, distance km)."""
    con = repo.connect()
    rows = con.execute("SELECT * FROM localities").fetchall()
    con.close()
    best, best_d = None, float("inf")
    for r in rows:
        d = haversine_km(lat, lon, r["lat"], r["lon"])
        if d < best_d:
            best, best_d = dict(r), d
    return best, best_d


def reverse_geocode(lat: float, lon: float) -> dict:
    """Free reverse geocode (BigDataCloud, no key). Returns {} on failure."""
    try:
        r = requests.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={"latitude": lat, "longitude": lon, "localityLanguage": "en"},
            timeout=15)
        if r.status_code == 200:
            j = r.json()
            return {"name": j.get("city") or j.get("locality") or "",
                    "region": j.get("principalSubdivision") or ""}
    except Exception as e:
        print(f"[zones] reverse geocode failed: {e}")
    return {}


def classify_coords(lat: float, lon: float) -> dict:
    """Classify any lat/lon into a zone. Returns locality-like dict + zone.

    - Nearest DB locality within 30 km -> that locality + its division zone.
    - Else reverse-geocode a real place name, save as new locality, zone =
      nearest division (or 'Unverified' if nothing within 60 km).
    """
    near, dist = nearest_locality(lat, lon)
    if near and dist <= 30:
        near["zone"] = near.get("division") or "Unverified"
        near["matched_km"] = round(dist, 1)
        return near
    rev = reverse_geocode(lat, lon)
    name = rev.get("name") or f"Location {round(lat, 3)}, {round(lon, 3)}"
    zone = near.get("division") if (near and dist <= 60) else "Unverified"
    lid = repo.get_or_create_locality(name, lat, lon, near.get("elevation_m") or 0 if near else 0,
                                      zone, source="gps")
    con = repo.connect()
    row = con.execute("SELECT * FROM localities WHERE id=?", (lid,)).fetchone()
    con.close()
    out = dict(row)
    out["zone"] = out.get("division") or "Unverified"
    out["matched_km"] = round(dist, 1) if near else None
    return out
