"""
bot.py — Main entry point
Flask keep_alive runs first so Render/Koyeb marks the service healthy,
then the Pyrogram bot starts in the same asyncio event loop.
"""
import asyncio
import logging
from pyrogram import Client
from pyrogram.types import BotCommand
from config import API_ID, API_HASH, BOT_TOKEN
from utils.flood_manager import FloodManager
from utils.listener import patch_client, register_listener
from keep_alive import keep_alive

# Patch Pyrogram Client to add .listen() natively
patch_client()
# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ForwardBot")

# Global active task tracker: {user_id: FloodManager}
active_tasks: dict[int, FloodManager] = {}


async def main():
    bot = Client(
        name="ForwardBot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )

    import plugins.start as start_plugin
    import plugins.login as login_plugin
    import plugins.forward as forward_plugin
    import plugins.clone as clone_plugin

    # Register our native listener to handle .listen() events
    register_listener(bot)
    
    start_plugin.register(bot)
    login_plugin.register(bot)
    forward_plugin.register(bot)
    clone_plugin.register(bot)

    logger.info("Starting Forward Bot...")

    async with bot:
        me = await bot.get_me()
        logger.info(f"✅ Bot running as @{me.username}")

        # Register commands in Telegram UI (shows in command menu)
        await bot.set_bot_commands([
            BotCommand("start",   "Start the bot & see status"),
            BotCommand("login",   "Login with your Telegram account"),
            BotCommand("logout",  "Logout and delete session"),
            BotCommand("target",  "Set target channel/group"),
            BotCommand("forward", "Start forwarding messages"),
            BotCommand("clone",   "Clone a channel"),
            BotCommand("stop",    "Stop active forwarding"),
            BotCommand("help",    "Show help guide"),
        ])
        logger.info("✅ Bot commands registered in Telegram")

        await asyncio.Event().wait()   # run forever


if __name__ == "__main__":
    keep_alive()          # Start Flask in daemon thread (port 8080)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user.")
