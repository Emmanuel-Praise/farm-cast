"""Weather fetching: batched Open-Meteo with elevation downscaling + disk cache.

Derived values: P24/P48/P72 (next 24/48/72h from now), prob_max, tmin, tmax,
wind_max, dry_run, daily[], plus today's remaining-hours breakdown with a
plain-language headline like "Light rain today around 2PM (4mm)".

NOTE: with past_days=1 the hourly array starts YESTERDAY, so all windows are
sliced by actual timestamps in Africa/Douala — never by raw index.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import requests

try:
    from config import settings
except ImportError:
    from farmcast.config import settings

DOUALA = ZoneInfo("Africa/Douala")


def douala_now() -> datetime:
    return datetime.now(DOUALA)


def _ampm(dt: datetime) -> str:
    return dt.strftime("%I%p").lstrip("0") or "12AM"


def _intensity(max_mm: float) -> str:
    if max_mm < 1:
        return "Light showers"
    if max_mm < 3:
        return "Light rain"
    if max_mm < 8:
        return "Moderate rain"
    return "Heavy rain"


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
    today_hours: list = field(default_factory=list)  # [{t:"14:00", mm, prob}]
    today_rest_mm: float = 0.0
    today_headline: str = ""
    next_rain: str | None = None  # "14:00" today, else None
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


def _derive(hourly: dict, daily: dict, now: datetime | None = None) -> Forecast:
    now = now or douala_now()
    now_h = now.replace(minute=0, second=0, microsecond=0)
    times = hourly.get("time") or []
    precip = hourly.get("precipitation") or []
    prob = hourly.get("precipitation_probability") or []
    wind = hourly.get("wind_speed_10m") or []
    dsum = daily.get("precipitation_sum") or []
    dmin = daily.get("temperature_2m_min") or []
    dmax = daily.get("temperature_2m_max") or []

    dt0 = None
    try:
        dt0 = datetime.strptime(times[0], "%Y-%m-%dT%H:%M").replace(tzinfo=DOUALA)
    except Exception:
        dt0 = None

    def window(hours_ahead: int) -> tuple[list, list, list]:
        """Hourly values in [now, now+hours_ahead). Falls back to index math."""
        if dt0 is None or not times:
            i = 24  # past_days=1 layout: 0-23 yesterday, 24+ today
            return precip[i:i + hours_ahead], prob[i:i + hours_ahead], wind[i:i + hours_ahead]
        out_p, out_q, out_w = [], [], []
        for t, p, q, w in zip(times, precip, prob, wind):
            try:
                dt = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=DOUALA)
            except Exception:
                continue
            if now_h <= dt < now_h + timedelta(hours=hours_ahead):
                out_p.append(p or 0)
                out_q.append(q or 0)
                out_w.append(w or 0)
        return out_p, out_q, out_w

    p24v, q24v, w24v = window(24)
    p48v, _, _ = window(48)
    p72v, _, _ = window(72)
    p24 = round(sum(p24v), 1)
    p48 = round(sum(p48v), 1)
    p72 = round(sum(p72v), 1)
    prob_max = max(q24v or [0])
    wind_max = round(max(w24v or [0]), 1)
    tmin = (dmin[1] if len(dmin) > 1 else (dmin[0] if dmin else 0))
    tmax = (dmax[1] if len(dmax) > 1 else (dmax[0] if dmax else 0))
    # dry_run: consecutive days ahead with daily sum < 2mm
    dry_run = 0
    for v in (dsum[1:] or dsum):
        if (v or 0) < 2:
            dry_run += 1
        else:
            break

    # ---- today's remaining hours ----
    today_hours = []
    if dt0 is not None and times:
        for t, p, q in zip(times, precip, prob):
            try:
                dt = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=DOUALA)
            except Exception:
                continue
            if dt.date() == now.date() and dt >= now_h:
                today_hours.append({"t": dt.strftime("%H:%M"),
                                    "mm": round(p or 0, 1), "prob": q or 0})
    today_rest_mm = round(sum(h["mm"] for h in today_hours), 1)

    # rainy spells today (consecutive hours >= 0.5mm)
    spells = []
    cur = None
    for i, h in enumerate(today_hours):
        if h["mm"] >= 0.5:
            if cur is None:
                cur = {"start": h["t"], "end": h["t"], "mm": 0.0, "max": 0.0}
            cur["end"] = h["t"]
            cur["mm"] = round(cur["mm"] + h["mm"], 1)
            cur["max"] = max(cur["max"], h["mm"])
        elif cur is not None:
            spells.append(cur)
            cur = None
    if cur is not None:
        spells.append(cur)

    def _t12(hhmm: str) -> str:
        try:
            return _ampm(datetime.strptime(hhmm, "%H:%M"))
        except Exception:
            return hhmm

    next_rain = spells[0]["start"] if spells else None
    if spells:
        s0 = spells[0]
        span = _t12(s0["start"]) if s0["start"] == s0["end"] \
            else f"{_t12(s0['start'])}-{_t12(s0['end'])}"
        today_headline = (f"{_intensity(s0['max'])} today around {span} "
                          f"({s0['mm']}mm)")
    elif today_rest_mm > 0:
        today_headline = f"Drizzle possible today ({today_rest_mm}mm total)."
    elif not today_hours:
        today_headline = "Today is over — see tomorrow's outlook."
    else:
        today_headline = "Dry for the rest of today."

    return Forecast(p24=p24, p48=p48, p72=p72,
                    prob_max=prob_max, tmin=tmin, tmax=tmax,
                    wind_max=wind_max, dry_run=dry_run,
                    daily=[round(float(x or 0), 1) for x in dsum],
                    today_hours=today_hours, today_rest_mm=today_rest_mm,
                    today_headline=today_headline, next_rain=next_rain)


def fetch_places(places: list[dict], run_date: str | None = None,
                 use_cache: bool = True) -> dict[str, Forecast]:
    """places: [{key, lat, lon, elev}]. One batched HTTP call. Returns key->Forecast."""
    run_date = run_date or douala_now().date().isoformat()
    out: dict[str, Forecast] = {}
    todo = []
    for p in places:
        cp = cache_path(run_date, p["key"])
        if use_cache and os.path.exists(cp):
            try:
                with open(cp, encoding="utf-8") as f:
                    data = json.load(f)
                if "today_headline" not in data and data.get("raw"):
                    # old cache entry: re-derive (raw hourly/daily are stored)
                    raw = data["raw"]
                    fc = _derive(raw.get("hourly", {}), raw.get("daily", {}))
                    fc.raw = raw
                    with open(cp, "w", encoding="utf-8") as f2:
                        json.dump({**fc.to_dict(), "raw": raw}, f2)
                else:
                    fields = ("p24", "p48", "p72", "prob_max", "tmin",
                              "tmax", "wind_max", "dry_run", "daily",
                              "today_hours", "today_rest_mm",
                              "today_headline", "next_rain")
                    fc = Forecast(**{k: data[k] for k in fields if k in data})
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
