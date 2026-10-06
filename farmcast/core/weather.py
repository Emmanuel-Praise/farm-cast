"""Weather fetching: batched Open-Meteo with elevation downscaling + disk cache.

Derived values: P24, P48, P72, prob_max, tmin, tmax, wind_max, dry_run, daily[].
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import date
import requests

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


@dataclass
class Forecast:
    p24: float = 0.0
    p48: float = 0.0
    p72: float = 0.0
    prob_max: float = 0.0
    tmin: float = 0.0
    tmax: float = 0.0
    wind_max: float = 0.0
    dry_run: int = 0
    daily: list = None
    raw: dict = None

    def to_dict(self):
        d = asdict(self)
        return d


def cache_path(run_date: str, key: str) -> str:
    base = os.path.join(os.getcwd(), "farmcast", "cache", "forecasts", run_date)
    if not os.path.isdir(os.path.join(os.getcwd(), "cache")):
        # allow running from inside farmcast/ too
        base = os.path.join("cache", "forecasts", run_date)
    os.makedirs(base, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return os.path.join(base, f"{safe}.json")


def _derive(hourly: dict, daily: dict) -> Forecast:
    precip = hourly.get("precipitation") or []
    prob = hourly.get("precipitation_probability") or []
    wind = hourly.get("wind_speed_10m") or []
    dsum = daily.get("precipitation_sum") or []
    dmin = daily.get("temperature_2m_min") or []
    dmax = daily.get("temperature_2m_max") or []

    def s(vals, a, b):
        return round(sum((vals[a:b] or [])), 1)

    p24 = s(precip, 0, 24)
    p48 = s(precip, 0, 48)
    p72 = s(precip, 0, 72)
    prob_max = max((prob[0:24] or [0]))
    wind_max = round(max((wind[0:24] or [0])), 1)
    tmin = (dmin[1] if len(dmin) > 1 else (dmin[0] if dmin else 0))
    tmax = (dmax[1] if len(dmax) > 1 else (dmax[0] if dmax else 0))
    # dry_run: consecutive days ahead with daily sum < 2mm
    dry_run = 0
    for v in (dsum[1:] or dsum):
        if (v or 0) < 2:
            dry_run += 1
        else:
            break
    return Forecast(p24=p24, p48=p48, p72=p72,
                    prob_max=prob_max, tmin=tmin, tmax=tmax,
                    wind_max=wind_max, dry_run=dry_run,
                    daily=[round(float(x or 0), 1) for x in dsum])


def fetch_places(places: list[dict], run_date: str | None = None,
                 use_cache: bool = True) -> dict[str, Forecast]:
    """places: [{key, lat, lon, elev}]. One batched HTTP call. Returns key->Forecast."""
    run_date = run_date or date.today().isoformat()
    out: dict[str, Forecast] = {}
    todo = []
    for p in places:
        cp = cache_path(run_date, p["key"])
        if use_cache and os.path.exists(cp):
            try:
                with open(cp, encoding="utf-8") as f:
                    data = json.load(f)
                fc = Forecast(**{k: data[k] for k in
                                  ("p24", "p48", "p72", "prob_max", "tmin",
                                   "tmax", "wind_max", "dry_run", "daily") if k in data})
                fc.raw = data.get("raw")
                out[p["key"]] = fc
                continue
            except Exception:
                pass
        todo.append(p)

    if todo:
        lats = ",".join(str(p["lat"]) for p in todo)
        lons = ",".join(str(p["lon"]) for p in todo)
        elevs = ",".join(str(p.get("elev") or 0) for p in todo)
        params = {
            "latitude": lats, "longitude": lons, "elevation": elevs,
            "hourly": "precipitation,precipitation_probability,temperature_2m,wind_speed_10m",
            "daily": "precipitation_sum,temperature_2m_min,temperature_2m_max",
            "past_days": 1, "forecast_days": 5,
            "timezone": "Africa/Douala",
        }
        r = requests.get(settings.FORECAST_URL, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        items = payload if isinstance(payload, list) else [payload]
        for p, item in zip(todo, items):
            hourly = item.get("hourly", {})
            daily = item.get("daily", {})
            fc = _derive(hourly, daily)
            fc.raw = item
            out[p["key"]] = fc
            try:
                with open(cache_path(run_date, p["key"]), "w", encoding="utf-8") as f:
                    json.dump({**fc.to_dict(), "raw": item}, f)
            except Exception:
                pass
    return out


def fetch_single(lat: float, lon: float, elev: float = 0, key: str = "single") -> Forecast:
    return fetch_places([{"key": key, "lat": lat, "lon": lon, "elev": elev}],
                        use_cache=False)[key]
