"""CLI: python -m farmcast.rules --place Kumbo [--crop maize]"""
from farmcast.core.location import resolve_location
from farmcast.core.weather import fetch_places
from farmcast.core import rules as R
from farmcast.core.message import render_broadcast

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", required=True)
    ap.add_argument("--crop", default="maize")
    a = ap.parse_args()
    res = resolve_location(a.place)
    assert res.status == "ok", f"resolve failed: {res.status} {res.options}"
    L = res.locality
    fc = fetch_places([{"key": L.name, "lat": L.lat, "lon": L.lon,
                        "elev": L.elevation_m}])[L.name]
    cat = R.categorize(fc.p48, fc.daily or [])
    fl = R.flags(fc.tmin, L.elevation_m, fc.wind_max, fc.p48, fc.p24)
    msg = render_broadcast("Test Farmer", L.name, cat, fc.p48, a.crop,
                           {"flags": fl, "plant_day": R.day_label(
                               R.next_good_plant_day(fc.daily or []))})
    print(f"category={cat} flags={fl}")
    print("---")
    print(msg)
