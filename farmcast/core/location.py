"""Location resolution engine (spec section 4).

resolve_location(query) -> Locality
Steps: normalise -> gazetteer exact -> gazetteer fuzzy -> Open-Meteo geocoding
       -> NW bbox filter -> ambiguity check.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import requests

from .gazetteer import get_default_gazetteer, normalise

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


@dataclass
class Locality:
    name: str
    lat: float
    lon: float
    elevation_m: int = 0
    division: str = ""
    source: str = "gazetteer"   # gazetteer | geocoded
    verified: int = 0
    outside_nw: bool = False
    id: int | None = None


@dataclass
class ResolveResult:
    status: str  # ok | ambiguous | not_found
    locality: Locality | None = None
    options: list[Locality] = field(default_factory=list)
    outside_nw: bool = False


def inside_nw(lat: float, lon: float) -> bool:
    return (settings.NW_LAT_MIN <= lat <= settings.NW_LAT_MAX
            and settings.NW_LON_MIN <= lon <= settings.NW_LON_MAX)


def geocode(query: str, count: int = 5) -> list[dict]:
    try:
        r = requests.get(settings.GEOCODING_URL,
                         params={"name": query, "count": count,
                                 "language": "en", "format": "json"},
                         timeout=15)
        r.raise_for_status()
        return (r.json() or {}).get("results", []) or []
    except Exception:
        return []


def _from_geocode_item(item: dict) -> Locality:
    return Locality(
        name=item.get("name", "?"),
        lat=float(item["latitude"]),
        lon=float(item["longitude"]),
        elevation_m=int(float(item.get("elevation") or 0)),
        division=str(item.get("admin2") or item.get("admin1") or ""),
        source="geocoded",
        verified=0,
    )


def resolve_location(query: str) -> ResolveResult:
    q = (query or "").strip()
    if not q:
        return ResolveResult(status="not_found")

    gaz = get_default_gazetteer()

    hit = gaz.exact(q)
    if hit:
        return ResolveResult(status="ok", locality=Locality(
            name=hit.name, lat=hit.lat, lon=hit.lon,
            elevation_m=hit.elevation_m, division=hit.division,
            source="gazetteer", verified=1))

    hit = gaz.fuzzy(q)
    if hit:
        return ResolveResult(status="ok", locality=Locality(
            name=hit.name, lat=hit.lat, lon=hit.lon,
            elevation_m=hit.elevation_m, division=hit.division,
            source="gazetteer", verified=1))

    results = geocode(q, count=settings.GEO_COUNT)
    if not results:
        return ResolveResult(status="not_found")

    cands = [_from_geocode_item(it) for it in results]
    in_box = [c for c in cands if inside_nw(c.lat, c.lon)]

    # Ambiguity: >1 result inside box -> ask farmer to choose
    pool = in_box if len(in_box) > 1 else (in_box or cands)
    if len(pool) > 1 and len(in_box) > 1:
        return ResolveResult(status="ambiguous", options=pool[:5])

    top = pool[0]
    top.outside_nw = not inside_nw(top.lat, top.lon)
    return ResolveResult(status="ok", locality=top, outside_nw=top.outside_nw)


def main():
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "kumbo"
    res = resolve_location(q)
    print(f"query: {q!r} (normalised: {normalise(q)!r})")
    print(f"status: {res.status}")
    if res.locality:
        L = res.locality
        print(f"  -> {L.name} | {L.division} | lat={L.lat} lon={L.lon} elev={L.elevation_m}m "
              f"| source={L.source} | outside_nw={L.outside_nw}")
    if res.options:
        for i, o in enumerate(res.options, 1):
            print(f"  {i}. {o.name} ({o.division}) lat={o.lat} lon={o.lon}")


if __name__ == "__main__":
    main()
