"""AI responder: OpenRouter (primary) -> NVIDIA NIM (fallback) -> None (rules reply).

Contract: these functions NEVER raise. On total failure they return "" and the
caller falls back to the deterministic rule-based text, so a farmer ALWAYS gets
an answer. Weather numbers always come from the rule engine, never from the LLM.
"""
from __future__ import annotations
import base64
import requests

try:
    from config import settings
except ImportError:
    from farmcast.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are FarmCast, a friendly farming advisor for smallholder farmers in "
    "Northwest Cameroon. Reply in simple English, max 600 characters. "
    "Give practical, local advice (maize, beans, cassava, Irish potato, coffee, "
    "vegetables). NEVER invent rainfall numbers or forecasts — if asked about "
    "rain, tell them to send RAIN, PLANT, SPRAY or DRY with their village name. "
    "No medical, legal or financial advice beyond the farm."
)


def _post(url: str, headers: dict, payload: dict, timeout: int = 25) -> str:
    last = ""
    for _ in range(2):  # one retry per provider
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                return (r.json()["choices"][0]["message"].get("content") or "").strip()
            last = f"http {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = str(e)[:200]
    print(f"[AI] provider failed {url}: {last}")
    return ""


def _run(messages: list, max_tokens: int = 300, temperature: float = 0.6) -> str:
    """OpenRouter -> NVIDIA chain. Returns "" when all providers fail."""
    if settings.OPENROUTER_API_KEY:
        out = _post(
            OPENROUTER_URL,
            {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
             "Content-Type": "application/json"},
            {"model": settings.TEXT_MODEL, "messages": messages,
             "max_tokens": max_tokens, "temperature": temperature},
        )
        if out:
            return out
    if settings.NVIDIA_API_KEY:
        out = _post(
            NVIDIA_URL,
            {"Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
             "Content-Type": "application/json"},
            {"model": settings.NVIDIA_TEXT_MODEL, "messages": messages,
             "max_tokens": max_tokens, "temperature": temperature},
        )
        if out:
            return out
    return ""


def chat_raw(system: str, user: str, max_tokens: int = 400,
             temperature: float = 0.6) -> str:
    """Direct system+user call for agent steps. Never raises, "" on failure."""
    if not (user or "").strip():
        return ""
    try:
        return _run([{"role": "system", "content": system},
                     {"role": "user", "content": user}],
                    max_tokens=max_tokens, temperature=temperature)
    except Exception as e:
        print(f"[AI] chat_raw failed: {e}")
        return ""


def chat(text: str, farmer: dict | None = None) -> str:
    """Conversational reply for non-weather messages. Returns "" if unavailable."""
    farmer = farmer or {}
    user = text.strip()
    if not user:
        return ""
    context = (
        f"Farmer: {farmer.get('name') or 'farmer'}, "
        f"crop: {farmer.get('crop') or 'maize'}."
    )
    return _run(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": f"{context}\nMessage: {user}"}],
        max_tokens=300, temperature=0.6)


def describe_image(image_bytes: bytes, mime: str = "image/jpeg",
                   farmer: dict | None = None, caption: str = "") -> str:
    """Describe a farmer-sent photo (crop problem, field, etc.). Returns "" if unavailable."""
    if not image_bytes:
        return ""
    b64 = base64.b64encode(image_bytes).decode()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text":
             f"A farmer ({(farmer or {}).get('crop') or 'maize'} grower) sent this photo"
             + (f" with caption: {caption}" if caption else "") +
             ". Describe what you see and give 2-3 practical next steps. Max 600 characters."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]},
    ]
    if settings.OPENROUTER_API_KEY:
        out = _post(
            OPENROUTER_URL,
            {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
             "Content-Type": "application/json"},
            {"model": settings.VISION_MODEL, "messages": messages,
             "max_tokens": 400, "temperature": 0.5},
        )
        if out:
            return out
    if settings.NVIDIA_API_KEY:
        out = _post(
            NVIDIA_URL,
            {"Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
             "Content-Type": "application/json"},
            {"model": settings.NVIDIA_VISION_MODEL, "messages": messages,
             "max_tokens": 400, "temperature": 0.5},
        )
        if out:
            return out
    return ""
