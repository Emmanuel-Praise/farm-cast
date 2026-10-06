"""Speech-to-text for inbound farmer voice notes. Never raises.

Provider: ElevenLabs Scribe. Returns transcript "" when unavailable/mock.
Note: ElevenLabs Scribe expects a scribe model id; if SPEECH_MODEL is set to a
whisper id (template default), we map to scribe_v1 so calls don't fail.
"""
from __future__ import annotations
import requests

try:
    from config import settings
except ImportError:
    from farmcast.config import settings

SCRIBE_URL = "https://api.elevenlabs.io/v1/speech-to-text"


def _scribe_model() -> str:
    m = (settings.SPEECH_MODEL or "").strip()
    if m.lower().startswith("scribe"):
        return m
    return "scribe_v1"


def transcribe(audio_bytes: bytes, mime: str = "audio/ogg") -> str:
    if not audio_bytes or not settings.ELEVENLABS_API_KEY:
        return ""
    try:
        files = {"file": ("voice.ogg", audio_bytes, mime)}
        data = {"model_id": _scribe_model()}
        r = requests.post(
            SCRIBE_URL,
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            files=files, data=data, timeout=60,
        )
        if r.status_code == 200:
            j = r.json()
            return (j.get("text") or "").strip()
        print(f"[STT] elevenlabs http {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[STT] failed: {e}")
    return ""
