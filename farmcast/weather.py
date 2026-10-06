"""CLI: python -m farmcast.weather --place Kumbo [--no-cache]"""
from farmcast.core.location import resolve_location
from farmcast.core.weather import fetch_places

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", required=True)
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()
    res = resolve_location(a.place)
    if res.status != "ok":
        print(f"status={res.status}")
        for i, o in enumerate(res.options, 1):
            print(f"  {i}. {o.name} lat={o.lat} lon={o.lon}")
        raise SystemExit(1)
    L = res.locality
    fc = fetch_places([{"key": L.name, "lat": L.lat, "lon": L.lon,
                        "elev": L.elevation_m}], use_cache=not a.no_cache)[L.name]
    print(f"{L.name} lat={L.lat} lon={L.lon} elev={L.elevation_m}m outside_nw={L.outside_nw}")
    print(f"P24={fc.p24} P48={fc.p48} P72={fc.p72} prob_max={fc.prob_max} "
          f"tmin={fc.tmin} tmax={fc.tmax} wind_max={fc.wind_max} dry_run={fc.dry_run}")
    print(f"daily={fc.daily}")
