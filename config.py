"""
config.py — Flexible credential loader

Priority order (highest to lowest):
  1. System environment variables  ← Render / Koyeb / Railway / Docker
  2. .env file                     ← Local development
  3. Hardcoded defaults below      ← Fallback (fill your values here)
"""
import os
from dotenv import load_dotenv

# Load .env only if it exists (doesn't overwrite existing system env vars)
load_dotenv(override=False)

# ─────────────────────────────────────────────
# Fill your values here as fallback defaults.
# On Render/Koyeb, set these as env vars there.
# ─────────────────────────────────────────────
_DEFAULTS = {
    "API_ID":     "34439627",
    "API_HASH":   "e5c7efb57949e742889aa96bf64c4552",
    "BOT_TOKEN":  "8432833653:AAGZlrj1KMflp2zJCQaKKro1fSAiHbo4jeQ",
    "MONGO_URI":  "mongodb+srv://rajaualkhan33729_db_user:hlYTpjnHZzGDljKX@cluster0.vylyp51.mongodb.net/?appName=Cluster0",
    "OWNER_ID":   "7208112327",
}

def _get(key: str) -> str:
    """Reads from system env → .env → hardcoded default."""
    return os.environ.get(key) or _DEFAULTS.get(key, "")

# ── Credentials ───────────────────────────────
API_ID    = int(_get("API_ID"))
API_HASH  = _get("API_HASH")
BOT_TOKEN = _get("BOT_TOKEN")
MONGO_URI = _get("MONGO_URI")
OWNER_ID  = int(_get("OWNER_ID") or 0)

# ── Forward Engine Settings ───────────────────
FAST_BATCH_SIZE    = 100    # msgs per API call (fast mode)
FAST_BATCH_COUNT   = 10     # batches before break (100×10 = 1000 msgs)
FAST_DELAY         = 1.0    # seconds between batches
FAST_BREAK_SECONDS = 300    # 5-min break after 1000 msgs

SAFE_BATCH_SIZE    = 20     # msgs per API call (safe mode)
SAFE_BATCH_COUNT   = 10     # batches before break (20×10 = 200 msgs)
SAFE_DELAY         = 5.0    # seconds between batches
SAFE_BREAK_SECONDS = 60     # 1-min break after 200 msgs

MAX_FLOOD_COUNT    = 3      # floods before switching to safe mode
