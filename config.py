"""
config.py — Advanced Unified Configuration for Forward Bot
Supports both Ultra-Forward-Bot Config class and module-level constants.
Reads priority:
  1. System environment variables  (Koyeb / Render / Railway / Docker)
  2. .env file                     (Local development)
  3. Hardcoded defaults            (Fallback)
"""
import os
try:
    from dotenv import load_dotenv
    # Load .env only if it exists (doesn't overwrite existing system env vars)
    load_dotenv(override=False)
except ImportError:
    pass

_DEFAULTS = {
    "API_ID":             "34439627",
    "API_HASH":           "e5c7efb57949e742889aa96bf64c4552",
    "BOT_TOKEN":          "8432833653:AAHrsIx0gasQwv7eAJv6DHbyYTjcPRNziyY",
    "BOT_SESSION":        "Auto_Forward",
    "DATABASE_URI":       "mongodb+srv://rajaualkhan33729_db_user:hlYTpjnHZzGDljKX@cluster0.vylyp51.mongodb.net/?appName=Cluster0",
    "DATABASE_NAME":      "UltraForwardBot",
    "BOT_OWNER_ID":       "8349955493",
    "LOG_CHANNEL":        "-1003584084546",
    "DUMP_CHANNEL":       "0",
    "FORCE_SUB_CHANNEL":  "",
    "FORCE_SUB_ON":       "False",
    "PORT":               "8080",
}

def _get(key: str, alt_keys: tuple = ()) -> str:
    """Reads from system env -> alternative env keys -> _DEFAULTS fallback."""
    val = os.environ.get(key)
    if val:
        return val.strip()
    for alt in alt_keys:
        alt_val = os.environ.get(alt)
        if alt_val:
            return alt_val.strip()
    return str(_DEFAULTS.get(key, "")).strip()


class Config:
    API_ID = int(_get("API_ID")) if _get("API_ID").isdigit() else 0
    API_HASH = _get("API_HASH")
    BOT_TOKEN = _get("BOT_TOKEN")
    BOT_SESSION = _get("BOT_SESSION") or "Auto_Forward"
    DATABASE_URI = _get("DATABASE_URI", ("MONGO_URI", "DATABASE"))
    DATABASE_NAME = _get("DATABASE_NAME") or "UltraForwardBot"

    # Multi-admin support: handles space/comma-separated IDs cleanly
    _raw_owners = _get("BOT_OWNER_ID", ("OWNER_ID",)).replace(",", " ")
    BOT_OWNER_ID = [
        int(x) for x in _raw_owners.split()
        if x.lstrip("-").isdigit()
    ]

    _raw_log = _get("LOG_CHANNEL", ("LOG_CHANNEL_ID",))
    LOG_CHANNEL = int(_raw_log) if _raw_log.lstrip("-").isdigit() else 0

    _raw_dump = _get("DUMP_CHANNEL", ("DUMP_CHANNEL_ID",))
    DUMP_CHANNEL = int(_raw_dump) if _raw_dump.lstrip("-").isdigit() else 0

    FORCE_SUB_CHANNEL = _get("FORCE_SUB_CHANNEL")
    FORCE_SUB_ON = _get("FORCE_SUB_ON").lower() in ("true", "1", "yes")
    PORT = int(_get("PORT")) if _get("PORT").isdigit() else 8080


class temp(object):
    lock = {}
    CANCEL = {}
    PAUSE = {}
    LIVE_TASKS = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []


# ── Module-level Aliases for Full Backward Compatibility ────────
API_ID         = Config.API_ID
API_HASH       = Config.API_HASH
BOT_TOKEN      = Config.BOT_TOKEN
BOT_SESSION    = Config.BOT_SESSION
DATABASE_URI   = Config.DATABASE_URI
MONGO_URI      = Config.DATABASE_URI
DATABASE_NAME  = Config.DATABASE_NAME
BOT_OWNER_ID   = Config.BOT_OWNER_ID
OWNER_ID       = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else 0
LOG_CHANNEL    = Config.LOG_CHANNEL
LOG_CHANNEL_ID = Config.LOG_CHANNEL
DUMP_CHANNEL   = Config.DUMP_CHANNEL
FORCE_SUB_CHANNEL = Config.FORCE_SUB_CHANNEL
FORCE_SUB_ON   = Config.FORCE_SUB_ON
PORT           = Config.PORT

# ── Forward Engine Default Presets ─────────────────────────────
FAST_BATCH_SIZE    = 100
FAST_BATCH_COUNT   = 10
FAST_DELAY         = 1.0
FAST_BREAK_SECONDS = 300

SAFE_BATCH_SIZE    = 20
SAFE_BATCH_COUNT   = 10
SAFE_DELAY         = 5.0
SAFE_BREAK_SECONDS = 60
