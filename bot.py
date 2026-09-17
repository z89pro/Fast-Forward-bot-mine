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
import asyncio
import logging
from pyrogram import Client, __version__ as pyrogram_version
from pyrogram.raw.all import layer
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.types import BotCommand
from config import Config, temp
from database import db
from keep_alive import keep_alive

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
                BotCommand("pause", "Pause ongoing forwarding"),
                BotCommand("resume", "Resume paused forwarding"),
                BotCommand("stop", "Cancel ongoing forwarding"),
                BotCommand("settings", "Configure bot settings"),
                BotCommand("config", "Bot system configuration (Owner)"),
                BotCommand("unequify", "Remove duplicates in channel"),
                BotCommand("reset", "Reset settings to default"),
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

        # Notify users of restart if any ongoing tasks were recorded
        restart_text = "<b>๏[-ิ_•ิ]๏ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ !</b>"
        try:
            users = await db.get_all_frwd()
            async for u in users:
                cid = u.get("user_id")
                if cid:
                    try:
                        await self.send_message(cid, restart_text)
                    except FloodWait as fw:
                        await asyncio.sleep(fw.value + 1)
                        try:
                            await self.send_message(cid, restart_text)
                        except Exception:
                            pass
                    except Exception:
                        pass
            await db.rmve_frwd(all=True)
        except Exception as err:
            logger.debug(f"Restart broadcast cleanup: {err}")

        # Auto-resume live AutoSave channel monitors for all users
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

    # Pre-load persistent system config from MongoDB before Pyrogram starts
    try:
        asyncio.run(db.load_system_config_into_env())
    except Exception as e:
        logger.debug(f"Pre-load config error: {e}")

    app = Bot()
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Process terminated.")
