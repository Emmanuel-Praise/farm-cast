"""Rule engine: pure if/else over named thresholds. No ML."""
from __future__ import annotations

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


def categorize(p48: float, next5: list[float]) -> str:
    if p48 >= settings.P_HEAVY_RAIN:
        return "HEAVY_RAIN"
    if p48 >= settings.P_RAIN:
        return "RAIN"
    if p48 >= settings.P_LIGHT_RAIN:
        return "LIGHT_RAIN"
    if next5 and len(next5) >= 5 and all((d or 0) < settings.DRY_SPELL_DAY_MAX for d in next5[:5]):
        return "DRY_SPELL"
    return "DRY"


def flags(tmin: float, elev: float, wind_max: float,
          p48: float, p24: float) -> list[str]:
    out = []
    if tmin < settings.COLD_TMIN and (elev or 0) > settings.COLD_ELEV_MIN:
        out.append("COLD")
    if (wind_max or 0) > settings.HIGH_WIND_MAX:
        out.append("HIGH_WIND")
    if p48 < settings.PLANT_P48_MAX and p24 > settings.PLANT_P24_MIN:
        out.append("PLANT_WINDOW")
    return out


def next_good_plant_day(daily: list[float]) -> int | None:
    """First day index in next 7 where 3 <= sum <= 25."""
    for i, v in enumerate((daily or [])[:7]):
        if settings.PLANT_DAY_MIN <= (v or 0) <= settings.PLANT_DAY_MAX:
            return i
    return None


def next_good_spray_day(daily: list[float], wind_max: float = 0) -> int | None:
    for i, v in enumerate((daily or [])[:7]):
        if (v or 0) < settings.SPRAY_DAY_MAX and (wind_max or 0) < settings.SPRAY_WIND_MAX:
            return i
    return None


def next_good_fert_day(daily: list[float]) -> int | None:
    for i, v in enumerate((daily or [])[:7]):
        if settings.FERT_MIN <= (v or 0) <= settings.FERT_MAX:
            return i
    return None


DAY_NAMES = ["today", "tomorrow", "in 2 days", "in 3 days",
             "in 4 days", "in 5 days", "in 6 days"]


def day_label(idx: int | None) -> str:
    if idx is None:
        return "none"
    if 0 <= idx < len(DAY_NAMES):
        return DAY_NAMES[idx]
    return f"in {idx} days"
