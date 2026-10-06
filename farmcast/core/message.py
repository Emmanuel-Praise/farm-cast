"""Template rendering from config/templates/{lang}.json."""
from __future__ import annotations
import json
import os

try:
    from config import crops as crops_cfg
except ImportError:
    from farmcast.config import crops as crops_cfg

_CACHE: dict[str, dict] = {}


def load_templates(lang: str = "english") -> dict:
    lang = (lang or "english").lower()
    if lang in _CACHE:
        return _CACHE[lang]
    cands = [
        os.path.join("config", "templates", f"{lang}.json"),
        os.path.join("farmcast", "config", "templates", f"{lang}.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "config", "templates", f"{lang}.json"),
    ]
    for c in cands:
        if os.path.exists(c):
            with open(c, encoding="utf-8") as f:
                _CACHE[lang] = json.load(f)
                return _CACHE[lang]
    # fallback to english
    if lang != "english":
        return load_templates("english")
    return {}


def render_broadcast(name: str, place: str, category: str, mm48: float,
                     crop: str, extra: dict | None = None,
                     lang: str = "english") -> str:
    t = load_templates(lang)
    extra = extra or {}
    lines = [t.get("greeting", "Hello {name}.").format(name=name or "farmer")]
    key = {"HEAVY_RAIN": "forecast_heavy", "RAIN": "forecast_rain",
           "LIGHT_RAIN": "forecast_light", "DRY": "forecast_dry",
           "DRY_SPELL": "forecast_dryspell"}.get(category, "forecast_dry")
    lines.append(t.get(key, "{place}: {mm}mm").format(place=place, mm=mm48))
    lines.append(crops_cfg.advice_for(category, crop))
    if "COLD" in (extra.get("flags") or []):
        lines.append(t.get("cold_alert", ""))
    if "HIGH_WIND" in (extra.get("flags") or []):
        lines.append(t.get("wind_alert", ""))
    if extra.get("plant_day"):
        lines.append(t.get("next_plant_day", "{day}").format(day=extra["plant_day"]))
    return "\n".join(l for l in lines if l).strip()


def render_query(intent: str, place: str, category: str, mm48: float,
                 crop: str, extra: dict | None = None,
                 lang: str = "english") -> str:
    t = load_templates(lang)
    extra = extra or {}
    if intent == "PLANT":
        day = extra.get("plant_day") or t.get("no_plant_day", "No good day.")
        return (f"{t.get('forecast_rain', '{place}: {mm}mm').format(place=place, mm=mm48)}\n"
                f"{crops_cfg.advice_for(category, crop)}\n{day}")
    if intent == "SPRAY":
        return extra.get("spray_day") or t.get("no_spray_day", "No safe day.")
    if intent == "FERTILIZER":
        return extra.get("fert_day") or t.get("no_spray_day", "")
    if intent == "DRY":
        return t.get("forecast_dryspell", "") + f" ({place})"
    # FORECAST / default
    return render_broadcast("farmer", place, category, mm48, crop, extra, lang)
