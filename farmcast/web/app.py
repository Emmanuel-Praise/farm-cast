"""FastAPI app: WhatsApp webhook + admin JSON + React dashboard (Vite build)."""
from __future__ import annotations
import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from farmcast.web.admin import router as admin_router
from farmcast.web.webhook_whatsapp import answer_query as legacy_query
from farmcast.core.agent import respond as agent_respond
from farmcast.core.channels.whatsapp import send_text, send_audio, get_media_bytes
from farmcast.core import speech as stt
from farmcast.core import ai as farm_ai
from farmcast.core import voice as tts
from farmcast.db import repo

try:
    from config import settings
except ImportError:
    from farmcast.config import settings

app = FastAPI(title="FarmCast")
app.include_router(admin_router)

# Vite dev server origin (local React dev with proxy to this API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/webhook/whatsapp")
def verify(hub_mode: str = "", hub_verify_token: str = "",
           hub_challenge: str = ""):
    if hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge or "")
    return PlainTextResponse("forbidden", status_code=403)


@app.post("/webhook/whatsapp")
async def inbound(req: Request):
    try:
        payload = await req.json()
    except Exception:
        return {"ok": True}
    # Meta Cloud API shape: entry[].changes[].value.messages[]
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    sender = msg.get("from", "")
                    if not sender:
                        continue
                    mtype = msg.get("type", "")
                    reply = ""
                    if mtype == "text":
                        body = ((msg.get("text") or {}).get("body")) or ""
                        try:
                            reply = agent_respond(sender, body)
                        except Exception as e:
                            print(f"[webhook] agent failed, legacy: {e}")
                            reply = legacy_query(sender, body)
                    elif mtype == "audio":
                        data, mime = get_media_bytes((msg.get("audio") or {}).get("id", ""))
                        transcript = stt.transcribe(data, mime or "audio/ogg")
                        if transcript:
                            try:
                                reply = agent_respond(sender, transcript)
                            except Exception as e:
                                print(f"[webhook] agent failed, legacy: {e}")
                                reply = legacy_query(sender, transcript)
                        else:
                            reply = ("Sorry, I could not hear your voice note. "
                                     "Please type your message.")
                    elif mtype == "image":
                        data, mime = get_media_bytes((msg.get("image") or {}).get("id", ""))
                        farmer = repo.find_farmer_by_phone(sender)
                        caption = ((msg.get("image") or {}).get("caption")) or ""
                        reply = (farm_ai.describe_image(data, mime or "image/jpeg",
                                                        farmer, caption)
                                 or "Sorry, I could not see your photo. Please try sending it again.")
                    else:
                        continue
                    if not reply:
                        continue
                    send_text(sender, reply)
                    # optional voice-note reply (OFF unless VOICE_REPLIES=true)
                    if tts.enabled():
                        audio_out = tts.synthesize(reply)
                        if audio_out:
                            send_audio(sender, audio_out)
    except Exception as e:
        print("webhook error:", e)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}


# serve React dashboard build if present (Vite -> frontend/dist),
# else fall back to legacy static dashboard
for cand in ("frontend/dist", "farmcast/dashboard", "dashboard"):
    if os.path.isdir(cand):
        app.mount("/dashboard", StaticFiles(directory=cand, html=True), name="dashboard")
        break
