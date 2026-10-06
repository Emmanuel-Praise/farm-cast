"""Central settings. Every threshold is a named constant here — never hardcode in logic."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

TIMEZONE = os.getenv("TIMEZONE", "Africa/Douala")

DATABASE_PATH = os.getenv("DATABASE_PATH", "./farmcast.db")

# WhatsApp Cloud API (fill in later; empty => mock mode)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "farmcast-verify-token")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")

# --- AI providers: OpenRouter (primary) -> NVIDIA NIM (fallback) -> rules ---
OPENROUTER_API_KEY = os.getenv("PENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
TEXT_MODEL = os.getenv("TEXT_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
VISION_MODEL = os.getenv("VISION_MODEL", "nex-agi/nex-n2.5-pro:free")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_TEXT_MODEL = os.getenv("NVIDIA_TEXT_MODEL", "meta/llama-3.2-11b-vision-instruct")
NVIDIA_VISION_MODEL = os.getenv("NVIDIA_VISION_MODEL", "meta/llama-3.2-11b-vision-instruct")

# --- Speech (inbound voice notes) ---
SPEECH_PROVIDER = os.getenv("SPEECH_PROVIDER", "elevenlabs")
SPEECH_MODEL = os.getenv("SPEECH_MODEL", "scribe_v1")

# --- ElevenLabs TTS (outbound voice notes; OFF unless VOICE_REPLIES=true) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
VOICE_REPLIES = os.getenv("VOICE_REPLIES", "false").strip().lower() in ("1", "true", "yes")

# Northwest Region bounding box (spec section 4)
NW_LAT_MIN, NW_LAT_MAX = 5.65, 7.05
NW_LON_MIN, NW_LON_MAX = 9.75, 11.35

# Rule engine thresholds (spec section 6) — agronomist-editable
P_HEAVY_RAIN = 40.0   # P48 >= 40 => HEAVY_RAIN
P_RAIN = 15.0         # P48 >= 15 => RAIN
P_LIGHT_RAIN = 5.0    # P48 >= 5  => LIGHT_RAIN
DRY_SPELL_DAY_MAX = 5.0   # a day counts as dry if daily sum < 5mm
DRY_SPELL_DAYS = 5        # all next 5 days dry => DRY_SPELL
COLD_TMIN = 10.0          # degC
COLD_ELEV_MIN = 1600      # metres
HIGH_WIND_MAX = 30.0      # km/h
PLANT_P48_MAX = 25.0
PLANT_P24_MIN = 3.0

# Timing windows (on-demand)
SPRAY_DAY_MAX = 2.0
SPRAY_WIND_MAX = 12.0
FERT_MIN, FERT_MAX = 5.0, 20.0
PLANT_DAY_MIN, PLANT_DAY_MAX = 3.0, 25.0

# Cron times (Africa/Douala)
BROADCAST_CRON = "30 5 * * *"   # fetch at 05:30
BROADCAST_SEND_HOUR = 6
RETRY_HOUR = 6
RETRY_MINUTE = 30

# Geocoding
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEO_COUNT = 5

# Clarifications
CLARIFICATION_TTL_MINUTES = 10

# Seed CSV location
SEED_CSV = "config/localities_seed.csv"
