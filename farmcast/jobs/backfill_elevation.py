"""Backfill REAL elevations from Open-Meteo geocoding API (no mock altitudes).

Usage: python -m farmcast.jobs.backfill_elevation [--force]
Updates localities.elevation_m + elev_source='geocoding-api' for rows still on
'seed-estimate' (or all rows with --force). Safe to re-run.
"""
from __future__ import annotations
import requests

from farmcast.db import repo

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


def ensure_column():
    con = repo.connect()
    cols = [r[1] for r in con.execute("PRAGMA table_info(localities)").fetchall()]
    if "elev_source" not in cols:
        con.execute("ALTER TABLE localities ADD COLUMN elev_source TEXT DEFAULT 'seed-estimate'")
        con.commit()
    con.close()


def lookup_dem(lat: float, lon: float) -> int | None:
    """Real DEM elevation for exact coords (Open-Meteo elevation API, free)."""
    try:
        r = requests.get("https://api.open-meteo.com/v1/elevation",
                         params={"latitude": lat, "longitude": lon}, timeout=15)
        e = (r.json().get("elevation") or [None])[0]
        return int(float(e)) if e is not None else None
    except Exception as e:
        print(f"[elev-dem] {lat},{lon}: {e}")
        return None


def lookup_elevation(name: str) -> int | None:
    try:
        r = requests.get(settings.GEOCODING_URL,
                         params={"name": name, "count": 10, "language": "en", "format": "json"},
                         timeout=15)
        cands = []
        for item in (r.json().get("results") or []):
            lat, lon = float(item["latitude"]), float(item["longitude"])
            if settings.NW_LAT_MIN <= lat <= settings.NW_LAT_MAX and \
               settings.NW_LON_MIN <= lon <= settings.NW_LON_MAX:
                admin = f"{item.get('admin1') or ''} {item.get('country') or ''}".lower()
                local = ("northwest" in admin or "nord-ouest" in admin
                         or "cameroon" in admin or "cameroun" in admin)
                cands.append((local, item))
        cands.sort(key=lambda c: (not c[0]))
        for _, item in cands:
            if item.get("elevation") is not None:
                return int(float(item["elevation"]))
    except Exception as e:
        print(f"[elev] {name}: {e}")
    return None


def run(force: bool = False) -> dict:
    ensure_column()
    con = repo.connect()
    if force:
        rows = con.execute("SELECT id, name, lat, lon FROM localities").fetchall()
    else:
        rows = con.execute("SELECT id, name, lat, lon FROM localities "
                           "WHERE elev_source IS NULL OR elev_source<>'geocoding-api'").fetchall()
    con.close()
    updated, missing = 0, []
    for r in rows:
        elev = lookup_elevation(r["name"])
        source = "geocoding-api"
        if elev is None:
            # village not in geocoding DB: real DEM value for its coords
            elev = lookup_dem(r["lat"], r["lon"])
            source = "dem-api"
        if elev is None:
            missing.append(r["name"])
            continue
        con = repo.connect()
        con.execute("UPDATE localities SET elevation_m=?, elev_source=? WHERE id=?",
                    (elev, source, r["id"]))
        con.commit()
        con.close()
        updated += 1
        print(f"  {r['name']}: {elev}m ({source})")
    out = {"updated": updated, "missing": missing}
    print(out)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    run(force=ap.parse_args().force)
