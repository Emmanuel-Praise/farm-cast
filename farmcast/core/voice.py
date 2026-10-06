"""Text-to-speech (ElevenLabs) for optional voice replies. Never raises.

Outbound replies stay TEXT-ONLY unless VOICE_REPLIES=true in .env, so no
surprise audio costs or behaviour changes. Returns mp3 bytes or b"".
"""
from __future__ import annotations
import requests

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


def enabled() -> bool:
    return (settings.VOICE_REPLIES and bool(settings.ELEVENLABS_API_KEY)
            and bool(settings.WHATSAPP_TOKEN))


def synthesize(text: str) -> bytes:
    if not text or not settings.ELEVENLABS_API_KEY:
        return b""
    try:
        url = (f"https://api.elevenlabs.io/v1/text-to-speech/"
               f"{settings.ELEVENLABS_VOICE_ID}")
        r = requests.post(
            url,
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY,
                     "Content-Type": "application/json"},
            json={"text": text[:1000], "model_id": "eleven_multilingual_v2"},
            timeout=60,
        )
        if r.status_code == 200 and r.content:
            return r.content
        print(f"[TTS] elevenlabs http {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[TTS] failed: {e}")
    return b""
