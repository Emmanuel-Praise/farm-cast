"""WhatsApp Cloud API — text (+ optional audio). Mock mode when keys are missing.

Every function returns a dict and NEVER raises.
"""
from __future__ import annotations
import requests

try:
    from config import settings
except ImportError:
    from farmcast.config import settings


def configured() -> bool:
    return bool(settings.WHATSAPP_TOKEN and settings.PHONE_NUMBER_ID)


def send_text(to: str, body: str) -> dict:
    """Returns {ok, status, error, mocked}. Never raises."""
    if not configured():
        print(f"[MOCK WhatsApp -> {to}]: {body[:200]}")
        return {"ok": True, "status": "mocked", "mocked": True}
    try:
        url = (f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
               f"{settings.PHONE_NUMBER_ID}/messages")
        r = requests.post(url,
                          headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                                   "Content-Type": "application/json"},
                          json={"messaging_product": "whatsapp", "to": to,
                                "type": "text", "text": {"body": body}},
                          timeout=20)
        if r.status_code in (200, 201):
            return {"ok": True, "status": "sent", "mocked": False,
                    "id": (r.json().get("messages") or [{}])[0].get("id")}
        return {"ok": False, "status": "failed", "error": r.text[:300], "mocked": False}
    except Exception as e:
        return {"ok": False, "status": "failed", "error": str(e)[:300], "mocked": False}


def get_media_bytes(media_id: str) -> tuple[bytes, str]:
    """Download inbound media (voice note / photo). Returns (bytes, mime). Empty on failure."""
    if not configured() or not media_id:
        return b"", ""
    try:
        meta = requests.get(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{media_id}",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            timeout=20).json()
        url = meta.get("url", "")
        if not url:
            return b"", ""
        dl = requests.get(url,
                          headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
                          timeout=60)
        if dl.status_code == 200 and dl.content:
            return dl.content, dl.headers.get("Content-Type", "")
    except Exception as e:
        print(f"[WA media] download failed: {e}")
    return b"", ""


def send_audio(to: str, audio_bytes: bytes, mimetype: str = "audio/mpeg") -> dict:
    """Upload mp3 bytes then send as audio message. Never raises."""
    if not audio_bytes:
        return {"ok": False, "status": "failed", "error": "empty audio"}
    if not configured():
        print(f"[MOCK WhatsApp audio -> {to}]: {len(audio_bytes)} bytes")
        return {"ok": True, "status": "mocked", "mocked": True}
    try:
        up = requests.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.PHONE_NUMBER_ID}/media",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
            files={"file": ("reply.mp3", audio_bytes, mimetype)},
            data={"messaging_product": "whatsapp"},
            timeout=60).json()
        media_id = up.get("id", "")
        if not media_id:
            return {"ok": False, "status": "failed",
                    "error": str(up)[:300], "mocked": False}
        r = requests.post(
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                     "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": to,
                  "type": "audio", "audio": {"id": media_id}},
            timeout=20)
        if r.status_code in (200, 201):
            return {"ok": True, "status": "sent", "mocked": False}
        return {"ok": False, "status": "failed", "error": r.text[:300], "mocked": False}
    except Exception as e:
        return {"ok": False, "status": "failed", "error": str(e)[:300], "mocked": False}
