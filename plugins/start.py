"""
plugins/start.py
/start and /help commands.
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import database as db


HELP_TEXT = """
🤖 **Telegram Forward Bot** — Help Guide
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🔐 Account**
• `/login` — Login with your Telegram account
• `/logout` — Log out and delete session

**📌 Setup**
• `/target <chat_id or @username>` — Set destination channel/group

**📤 Forwarding**
• `/forward` — Open forward control panel (inline menu)
• `/clone <@source_channel>` — Clone a public channel to your target
• `/stop` — Stop active forwarding immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**⚡ Fast Mode** — 1,000 msgs per cycle → 5-min break → repeat
**🐢 Safe Mode** — Auto-activates after 3 FloodWaits (20 msgs/batch)

**🌊 FloodWait Protection**
• Auto-waits required time with live countdown
• After 3 FloodWaits → switches to Safe Mode
• Safe Mode protects your account from Telegram ban

**📋 Notes**
• Messages are copied (no "Forwarded from" tag)
• Supports ALL content: photos, videos, docs, stickers, audio, polls
• Private groups supported (you must be a member)
• Progress is saved on restart you can resume with /forward
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def register(bot: Client):

    @bot.on_message(filters.command("start") & filters.private)
    async def start_cmd(client: Client, msg: Message):
        session = await db.get_session(msg.from_user.id)
        logged_in = "✅ Logged In" if session else "❌ Not Logged In"

        await msg.reply(
            f"👋 **Welcome to Forward Bot!**\n\n"
            f"Status: {logged_in}\n\n"
            f"Forward messages from **any chat** to your **target channel**, "
            f"including private groups — all without the 'Forwarded from' tag.\n\n"
            f"**Quick Start:**\n"
            f"1️⃣ /login — Connect your Telegram account\n"
            f"2️⃣ /target @yourchannel — Set destination\n"
            f"3️⃣ /forward — Start forwarding\n\n"
            f"Send /help for full command list.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📖 Help", callback_data="help"),
                    InlineKeyboardButton("🔐 Login", callback_data="do_login"),
                ],
                [
                    InlineKeyboardButton("📤 Forward", callback_data="do_forward"),
                ]
            ])
        )

    @bot.on_message(filters.command("help") & filters.private)
    async def help_cmd(client: Client, msg: Message):
        await msg.reply(HELP_TEXT)

    @bot.on_callback_query(filters.regex("^help$"))
    async def help_cb(client, cb):
        await cb.message.edit_text(HELP_TEXT)

    @bot.on_callback_query(filters.regex("^do_login$"))
    async def do_login_cb(client, cb):
        await cb.message.edit_text("Send /login to connect your Telegram account.")

    @bot.on_callback_query(filters.regex("^do_forward$"))
    async def do_forward_cb(client, cb):
        await cb.answer()
        await cb.message.reply("/forward")
