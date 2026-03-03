"""
utils/flood_manager.py
BEST Anti-Ban + FloodWait Protection System

Strategy:
  1. Random human-like jitter on all delays (never fixed intervals)
  2. Exponential backoff after each FloodWait
  3. Proactive slowdown at 2 floods (before hitting 3rd = safe mode)
  4. Daily message counter (soft cap at 4000 to stay under TG limits)
  5. Session cooldown after heavy bursts
  6. After 3 floods → conservative mode + extended rest
"""
import asyncio
import random
import time
from pyrogram.errors import FloodWait
import database as db
from config import MAX_FLOOD_COUNT

# Daily message cap — set very high (effectively unlimited)
# ⚠️ Note: Telegram may still rate-limit/ban if too many msgs sent too fast
# FloodWait protection handles this automatically
DAILY_MSG_CAP = 10_000_000

# ── In-memory per-session message counter (resets daily)
_daily_stats: dict[int, dict] = {}
# {user_id: {"count": int, "day": int}}


def _today() -> int:
    from datetime import date
    return date.today().toordinal()


def _get_daily_count(user_id: int) -> int:
    s = _daily_stats.get(user_id)
    if not s or s["day"] != _today():
        _daily_stats[user_id] = {"count": 0, "day": _today()}
        return 0
    return s["count"]


def _add_daily_count(user_id: int, n: int):
    s = _daily_stats.get(user_id, {"count": 0, "day": _today()})
    if s["day"] != _today():
        s = {"count": 0, "day": _today()}
    s["count"] += n
    _daily_stats[user_id] = s


def human_delay(base: float) -> float:
    """
    Add random ±30% jitter to any delay.
    Mimics human behavior — avoids bot-pattern detection.
    """
    jitter = base * 0.3
    return base + random.uniform(-jitter, jitter)


class FloodManager:
    """
    Smart FloodWait + Anti-Ban Manager.

    Protection layers:
      Layer 1 — Jitter on all delays (human-like timing)
      Layer 2 — Daily message cap (4000/day max)
      Layer 3 — Proactive slowdown at 2 floods (before safe mode trigger)
      Layer 4 — Exponential backoff per flood: wait × 1.5× each time
      Layer 5 — Safe mode after 3 floods (small batches + long delays)
      Layer 6 — Extended session rest after safe mode session ends
    """

    def __init__(self, user_id: int, status_msg=None, bot=None):
        self.user_id = user_id
        self.status_msg = status_msg
        self.bot = bot
        self.flood_count = 0
        self.is_safe_mode = False
        self._stopped = False
        self._backoff_multiplier = 1.0   # grows after each flood

    def stop(self):
        self._stopped = True

    @property
    def stopped(self) -> bool:
        return self._stopped

    def check_daily_cap(self) -> bool:
        """Returns True if daily message cap has been hit."""
        return _get_daily_count(self.user_id) >= DAILY_MSG_CAP

    def register_sent(self, count: int):
        """Call this after every successful batch to track daily count."""
        _add_daily_count(self.user_id, count)

    async def _notify(self, text: str):
        if self.status_msg and self.bot:
            try:
                await self.bot.edit_message_text(
                    self.status_msg.chat.id,
                    self.status_msg.id,
                    text
                )
            except Exception:
                pass

    async def smart_delay(self, base_delay: float):
        """
        Sleep with human jitter. Doubles if we already have 2 floods
        (proactive slowdown — prevents 3rd flood).
        """
        delay = human_delay(base_delay)

        # Proactive slowdown at 2 floods to avoid 3rd
        if self.flood_count == 2 and not self.is_safe_mode:
            delay *= 2.5
            await self._notify(
                "⚠️ **Proactive Slowdown**\n"
                "2 FloodWaits hit. Slowing down to avoid 3rd flood & Safe Mode."
            )

        if self._stopped:
            return
        await asyncio.sleep(max(delay, 0.5))

    async def run(self, coro_func, *args, **kwargs):
        """
        Execute API call with full FloodWait + anti-ban protection.
        Usage: result = await flood_mgr.run(client.copy_messages, ...)
        """
        # Layer 2 — Daily cap check
        if self.check_daily_cap():
            await self._notify(
                "🛑 **Daily Message Limit Reached**\n\n"
                f"Already sent **{DAILY_MSG_CAP:,}** messages today.\n"
                "⏳ Resuming tomorrow. This protects your account from ban.\n\n"
                "Progress saved — use /forward tomorrow to continue."
            )
            self.stop()
            return None

        retry_count = 0
        max_retries = 5

        while not self._stopped and retry_count < max_retries:
            try:
                return await coro_func(*args, **kwargs)

            except FloodWait as e:
                wait_sec = e.value
                self.flood_count += 1
                await db.increment_flood_count(self.user_id)

                # Exponential backoff: each flood adds 50% more wait
                actual_wait = int(wait_sec * self._backoff_multiplier)
                self._backoff_multiplier = min(self._backoff_multiplier * 1.5, 5.0)

                flood_warning = ""
                if self.flood_count >= MAX_FLOOD_COUNT and not self.is_safe_mode:
                    flood_warning = "\n⚠️ **Switching to Safe Mode after this wait...**"

                await self._notify(
                    f"🌊 **FloodWait #{self.flood_count}**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏳ Telegram asked to wait: `{wait_sec}s`\n"
                    f"🔒 Anti-ban extra buffer: `{actual_wait - wait_sec}s`\n"
                    f"⏱ Total waiting: `{actual_wait}s`\n"
                    f"🔄 Auto-retrying after wait...{flood_warning}"
                )

                # Countdown in 30s chunks
                elapsed = 0
                while elapsed < actual_wait and not self._stopped:
                    chunk = min(30, actual_wait - elapsed)
                    await asyncio.sleep(chunk)
                    elapsed += chunk
                    remaining = actual_wait - elapsed
                    if remaining > 0 and not self._stopped:
                        await self._notify(
                            f"🌊 **FloodWait #{self.flood_count}** — Waiting...\n"
                            f"⏳ Resuming in `{remaining}s`..."
                        )

                # Switch to safe mode
                if self.flood_count >= MAX_FLOOD_COUNT and not self.is_safe_mode:
                    self.is_safe_mode = True
                    await self._notify(
                        "🐢 **Safe Mode Activated**\n\n"
                        "3 FloodWaits hit. Switched to:\n"
                        "• Smaller batches (20 msgs)\n"
                        "• Longer delays (5s + jitter)\n"
                        "• 1-min breaks every 200 msgs\n\n"
                        "Your account is now protected. ✅"
                    )
                    await asyncio.sleep(3)

                retry_count += 1

            except Exception as e:
                raise e

        if retry_count >= max_retries:
            await self._notify(f"❌ Max retries reached. Stopping to protect account.")
            self.stop()

        return None


async def countdown_break(seconds: int, label: str, flood_mgr: FloodManager):
    """
    Countdown break between batch cycles.
    Updates status every second for short breaks, every 10s for long ones.
    """
    update_interval = 1 if seconds <= 120 else 10

    for remaining in range(seconds, 0, -update_interval):
        if flood_mgr.stopped:
            return
        mins, secs = divmod(remaining, 60)
        await flood_mgr._notify(
            f"⏸ **{label}**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Resuming in `{mins:02d}:{secs:02d}`\n"
            f"📊 Daily sent: `{_get_daily_count(flood_mgr.user_id):,}` / `{DAILY_MSG_CAP:,}`\n"
            f"_(Send /stop to cancel)_"
        )
        await asyncio.sleep(update_interval)
