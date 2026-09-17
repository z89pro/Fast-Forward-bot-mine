"""
bot.py — Advanced Telegram Forward Bot
Features:
  • Interactive Forwarding with Live Progress Bar & Pause / Resume / Cancel
  • Smart AutoSave Mode with real-time channel monitoring & media filtering
  • Speed Control (Extreme 0.5s, Fast 1.0s, Normal 3.0s, Safe 5.0s, Anti-Ban Jitter)
  • Channel Duplicate Cleaner (/unequify)
  • Stealth Dump Channel & Telemetry Log Channel Dual-Architecture
  • Resilient Startup (prevents Koyeb/Render crash loop on expired tokens)
  • Built-in Web Server for 24/7 keep-alive & health checks
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from platform import python_version
from pyrogram import Client, __version__ as pyrogram_version
from pyrogram.raw.all import layer
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.types import BotCommand
from config import Config, temp
from database import db
from keep_alive import keep_alive
from font_styler import patch_pyrogram_font

# Initialize Universal Small Caps Font Engine
patch_pyrogram_font()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logger = logging.getLogger("ForwardBot")


class Bot(Client):
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=int(Config.API_ID) if Config.API_ID else 0,
            bot_token=Config.BOT_TOKEN,
            sleep_threshold=10,
            workers=200,
            plugins={"root": "plugins"}
        )
        self.log = logging

    async def start(self):
        try:
            await super().start()
        except (AccessTokenExpired, AccessTokenInvalid) as e:
            logger.critical("=" * 70)
            logger.critical("❌ CRITICAL: TELEGRAM BOT_TOKEN HAS EXPIRED OR IS INVALID!")
            logger.critical(f"Telegram error: {e}")
            logger.critical("")
            logger.critical("👉 HOW TO FIX ON KOYEB / RENDER:")
            logger.critical("1. Open Telegram and message @BotFather")
            logger.critical("2. Create a new bot or revoke/regenerate token (/newbot or /token)")
            logger.critical("3. Copy your fresh bot token")
            logger.critical("4. In your Koyeb / Render Dashboard -> App Settings -> Environment Variables:")
            logger.critical("   Set BOT_TOKEN = <your_new_token>")
            logger.critical("5. Redeploy your service.")
            logger.critical("=" * 70)
            logger.info("Keeping web health-check server alive to prevent Koyeb restart loop...")
            while True:
                await asyncio.sleep(3600)
        except Exception as e:
            logger.critical(f"❌ Failed to start bot client: {e}")
            logger.info("Keeping web health-check server alive...")
            while True:
                await asyncio.sleep(3600)

        me = await self.get_me()
        logger.info(f"✅ {me.first_name} (@{me.username}) started! Layer {layer} (Pyrogram {pyrogram_version})")

        # Register bot commands in Telegram Menu
        try:
            await self.set_bot_commands([
                BotCommand("start", "Start bot & check status"),
                BotCommand("forward", "Start message forwarding"),
                BotCommand("fwd", "Direct range forward links"),
                BotCommand("autosave", "Smart AutoSave & live monitoring"),
                BotCommand("plans", "Premium VIP passes & purchase"),
                BotCommand("referral", "Refer friends & earn rewards"),
                BotCommand("verify", "Check verification or get pass"),
                BotCommand("setverify", "Token verification settings (Admin)"),
                BotCommand("pause", "Pause ongoing forwarding"),
                BotCommand("resume", "Resume paused forwarding"),
                BotCommand("stop", "Cancel ongoing forwarding"),
                BotCommand("settings", "Configure bot settings"),
                BotCommand("config", "Bot system configuration (Owner)"),
                BotCommand("unequify", "Remove duplicates in channel"),
                BotCommand("reset", "Reset settings to default"),
                BotCommand("terms", "Terms of service"),
                BotCommand("privacy", "Privacy policy"),
                BotCommand("help", "Help and features guide"),
                BotCommand("status", "Check bot statistics")
            ])
            logger.info("✅ Telegram bot command menu registered.")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")

        # Ensure latest dynamic system configs are active in-memory
        try:
            await db.load_system_config_into_env()
        except Exception as e:
            logger.debug(f"Load system config error: {e}")

        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)

        # ── 1. Process Pending Restart Status (from /restart or config menu) ──
        ist = timezone(timedelta(hours=5, minutes=30))
        stamp = datetime.now(ist).strftime("%d-%b-%Y %I:%M:%S %p")
        restarted_chat_id = None
        reboot_notice = None

        try:
            reboot_notice = await db.get_and_clear_restart_status()
        except Exception as e:
            logger.debug(f"DB restart status query error: {e}")

        if not reboot_notice and os.path.exists('.restart_status.json'):
            try:
                with open('.restart_status.json', 'r') as f:
                    reboot_notice = json.load(f)
                os.remove('.restart_status.json')
            except Exception as e:
                logger.debug(f"Local restart file cleanup error: {e}")

        if reboot_notice:
            r_chat_id = reboot_notice.get('chat_id')
            r_msg_id = reboot_notice.get('message_id')
            if r_chat_id and r_msg_id:
                restarted_chat_id = r_chat_id
                reboot_done_text = (
                    "<blockquote><b>🤖 Bot Has Restarted!</b>\n\n"
                    "✅ <i>System rebooted successfully and all services are online!</i>\n\n"
                    f"⏰ <b>Time:</b> <code>{stamp} IST</code>\n"
                    f"⚡ <b>Engine:</b> <code>Skinet Verse v2.0 Fast Final</code>\n"
                    f"🚀 <b>Status:</b> <code>Active & Ready</code></blockquote>"
                )
                try:
                    await self.edit_message_text(r_chat_id, r_msg_id, reboot_done_text)
                    logger.info(f"Updated restart status message for chat {r_chat_id}")
                except Exception:
                    try:
                        await self.send_message(r_chat_id, reboot_done_text)
                    except Exception:
                        pass

        # ── 2. Broadcast Restart Notice to LOG_CHANNEL ──
        if Config.LOG_CHANNEL:
            log_restart_text = (
                "<blockquote><b>🤖 Bot Has Restarted!</b>\n\n"
                f"<b>Bot:</b> @{self.username} (<code>{self.id}</code>)\n"
                f"<b>Status:</b> <code>Online & Ready ✅</code>\n"
                f"<b>Time:</b> <code>{stamp} IST</code>\n"
                f"<b>Engine:</b> <code>Skinet Verse v2.0 Fast Final</code>\n"
                f"<b>Pyrogram:</b> <code>v{pyrogram_version}</code> | <b>Python:</b> <code>v{python_version()}</code>\n"
                f"<b>Database:</b> <code>MongoDB Connected</code></blockquote>"
            )
            try:
                await self.send_message(Config.LOG_CHANNEL, log_restart_text)
                logger.info(f"Sent restart notice to LOG_CHANNEL: {Config.LOG_CHANNEL}")
            except Exception as e:
                logger.warning(f"Failed to send restart notice to LOG_CHANNEL: {e}")

        # ── 3. Notify Bot Owner(s) if not already notified in active chat ──
        if Config.BOT_OWNER_ID:
            for oid in Config.BOT_OWNER_ID:
                if oid != restarted_chat_id:
                    try:
                        owner_notice = (
                            "<blockquote><b>🤖 Bot Has Restarted!</b>\n\n"
                            f"@{self.username} is back online and ready for tasks.\n\n"
                            f"⏰ <code>{stamp} IST</code></blockquote>"
                        )
                        await self.send_message(oid, owner_notice)
                    except Exception:
                        pass

        # ── 4. Auto-Resume Interrupted Forwarding Tasks from Checkpoint ──
        try:
            from plugins.regix import auto_resume_unfinished_tasks
            asyncio.create_task(auto_resume_unfinished_tasks(self))
            logger.info("✅ Auto-resume forward task recovery worker launched.")
        except Exception as e:
            logger.warning(f"Could not initialize forward auto-resumption: {e}")

        # ── 5. Auto-resume live AutoSave channel monitors for all users ──
        try:
            from plugins.autosave import resume_all_autosave_monitors
            asyncio.create_task(resume_all_autosave_monitors(self))
        except Exception as e:
            logger.debug(f"Could not initialize autosave auto-resumption: {e}")

    async def stop(self, *args):
        logger.info(f"🛑 Bot @{getattr(self, 'username', 'ForwardBot')} stopping...")
        await super().stop()


if __name__ == "__main__":
    # Start web keep-alive server first on Koyeb/Render port
    keep_alive()

    # Explicit event loop setup for Python 3.10/3.11/3.12 compatibility
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Pre-load persistent system config from MongoDB before Pyrogram starts
    try:
        loop.run_until_complete(db.load_system_config_into_env())
    except Exception as e:
        logger.debug(f"Pre-load config error: {e}")

    app = Bot()
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Process terminated.")
