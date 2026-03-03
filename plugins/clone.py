"""
plugins/clone.py
/clone — Clone a public channel to the user's target.
Does NOT require user session (uses bot client to read public channels).
Falls back to user client for private channels.
"""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.session_manager import get_user_client, resolve_chat
from utils.forwarder import run_forward
import database as db


def register(bot: Client):

    @bot.on_message(filters.command("clone") & filters.private)
    async def clone_cmd(client: Client, msg: Message):
        user_id = msg.from_user.id
        parts = msg.text.split(maxsplit=1)

        if len(parts) < 2:
            await msg.reply(
                "❌ **Usage:** `/clone @sourcechannel`\n\n"
                "Clones all messages from the source to your /target\n\n"
                "**Examples:**\n"
                "`/clone @durov`\n"
                "`/clone -1001234567890`\n\n"
                "_Make sure you've set a target with /target first._"
            )
            return

        source = parts[1].strip()
        session = await db.get_session(user_id)
        if not session:
            await msg.reply("❌ You must /login first.")
            return

        target = await db.get_target(user_id)
        if not target:
            await msg.reply("❌ Set a target first with /target @yourchannel")
            return

        from bot import active_tasks
        if user_id in active_tasks:
            await msg.reply("⚠️ A forward task is already running. Use /stop first.")
            return

        user_client = await get_user_client(user_id)
        if not user_client:
            await msg.reply("❌ Session invalid. Please /login again.")
            return

        # Verify source
        try:
            source_chat = await resolve_chat(user_client, source)
        except Exception as e:
            await msg.reply(f"❌ Cannot access source: `{e}`")
            return

        # Verify target
        try:
            target_chat = await resolve_chat(user_client, target)
        except Exception as e:
            await msg.reply(f"❌ Cannot access target: `{e}`")
            return

        status_msg = await msg.reply(
            f"🚀 **Clone started!**\n\n"
            f"📥 From: **{source_chat.title}**\n"
            f"📨 To: **{target_chat.title}**\n\n"
            f"Scanning messages..."
        )

        asyncio.create_task(
            run_forward(
                user_id=user_id,
                user_client=user_client,
                bot=client,
                source_chat=str(source_chat.id),
                target_chat=str(target_chat.id),
                status_msg=status_msg,
            )
        )
