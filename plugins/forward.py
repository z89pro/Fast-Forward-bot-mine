"""
plugins/forward.py
New flow:
  /forward → asks source channel ID (numeric) → start msg ID → end msg ID → starts
/target   → set destination
/stop     → cancel active task
"""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UsernameNotOccupied, PeerIdInvalid
from utils.session_manager import get_user_client, resolve_chat
from utils.forwarder import run_forward
import database as db


def register(bot: Client):

    # ── /target ────────────────────────────────────────────────
    @bot.on_message(filters.command("target") & filters.private)
    async def target_cmd(client: Client, msg: Message):
        user_id = msg.from_user.id
        parts = msg.text.split(maxsplit=1)

        if len(parts) < 2:
            await msg.reply(
                "❌ **Usage:**\n"
                "`/target -100xxxxxxxxxx`\n"
                "`/target @username`\n\n"
                "_Tip: Use the numeric chat ID (e.g. `-1003587966792`)_"
            )
            return

        if not await db.get_session(user_id):
            await msg.reply("❌ You must /login first.")
            return

        raw = parts[1].strip()

        # Normalize: try to resolve via user client (optional, soft fail)
        user_client = await get_user_client(user_id)
        chat_title = None
        saved_id = raw  # fallback: save as-is

        if user_client:
            try:
                # Convert numeric string properly
                chat_input = int(raw) if raw.lstrip('-').isdigit() else raw
                chat = await resolve_chat(user_client, raw)
                saved_id = str(chat.id)
                chat_title = chat.title
            except Exception:
                # get_chat failed (user not member, etc.) — save raw and continue
                saved_id = raw

        await db.set_target(user_id, saved_id)

        if chat_title:
            await msg.reply(
                f"✅ **Target set!**\n\n"
                f"📨 Destination: **{chat_title}** (`{saved_id}`)\n\n"
                f"_Use /forward to start._"
            )
        else:
            await msg.reply(
                f"✅ **Target saved:** `{saved_id}`\n\n"
                f"⚠️ Could not verify chat info right now\n"
                f"_(Make sure your account has access when forwarding)_\n\n"
                f"_Use /forward to start._"
            )

    # ── /forward — Step-by-step conversation ──────────────────
    @bot.on_message(filters.command("forward") & filters.private)
    async def forward_cmd(client: Client, msg: Message):
        user_id = msg.from_user.id

        if not await db.get_session(user_id):
            await msg.reply("❌ You must /login first before forwarding.")
            return

        target = await db.get_target(user_id)
        if not target:
            await msg.reply("❌ Set a target first: `/target -100xxxxxxxxxx`")
            return

        user_client = await get_user_client(user_id)
        if not user_client:
            await msg.reply("❌ Session invalid. Please /login again.")
            return

        from bot import active_tasks
        if user_id in active_tasks:
            await msg.reply("⚠️ A forward task is already running!\nSend /stop to cancel it first.")
            return

        # ── Step 1: Ask source channel numeric ID ──────────────
        ask1 = await msg.reply(
            "📥 **Step 1 of 3 — Source Chat**\n\n"
            "Send the **numeric ID** of the source channel/group:\n"
            "Example: `-1001234567890`\n\n"
            "_(To get a group ID: forward any message from it to @userinfobot)_\n"
            "_Send /cancel to abort._"
        )

        try:
            src_msg: Message = await client.listen(
                filters.text & filters.private & filters.user(user_id),
                timeout=120
            )
        except asyncio.TimeoutError:
            await ask1.reply("⌛ Timed out. Send /forward to try again.")
            return

        if src_msg.text.strip().lower() == "/cancel":
            await src_msg.reply("❌ Cancelled.")
            return

        source_input = src_msg.text.strip()

        # Verify source is accessible
        try:
            source_chat = await resolve_chat(user_client, source_input)
        except Exception as e:
            await src_msg.reply(f"❌ Cannot access source: `{e}`\nTry again with /forward")
            return

        # ── Step 2: Ask start message ID ──────────────────────
        ask2 = await src_msg.reply(
            f"✅ Source: **{source_chat.title}** (`{source_chat.id}`)\n\n"
            f"📩 **Step 2 of 3 — Start Message ID**\n\n"
            f"Send the **message ID to start from**:\n"
            f"_(Right-click any message → Copy Message Link → last number is the ID)_\n"
            f"_Send `1` to start from the very beginning._"
        )

        try:
            start_msg: Message = await client.listen(
                filters.text & filters.private & filters.user(user_id),
                timeout=120
            )
        except asyncio.TimeoutError:
            await ask2.reply("⌛ Timed out. Send /forward to try again.")
            return

        if start_msg.text.strip().lower() == "/cancel":
            await start_msg.reply("❌ Cancelled.")
            return

        try:
            start_id = int(start_msg.text.strip())
        except ValueError:
            await start_msg.reply("❌ Invalid message ID. Must be a number. Try /forward again.")
            return

        # ── Step 3: Ask end message ID ─────────────────────────
        ask3 = await start_msg.reply(
            f"📩 **Step 3 of 3 — End Message ID**\n\n"
            f"Send the **message ID to stop at**:\n"
            f"_Send `0` to forward till the last message._"
        )

        try:
            end_msg: Message = await client.listen(
                filters.text & filters.private & filters.user(user_id),
                timeout=120
            )
        except asyncio.TimeoutError:
            await ask3.reply("⌛ Timed out. Send /forward to try again.")
            return

        if end_msg.text.strip().lower() == "/cancel":
            await end_msg.reply("❌ Cancelled.")
            return

        try:
            end_id = int(end_msg.text.strip())
        except ValueError:
            await end_msg.reply("❌ Invalid message ID. Must be a number. Try /forward again.")
            return

        # ── Confirm and launch ─────────────────────────────────
        target_chat = await resolve_chat(user_client, target)

        status_msg = await end_msg.reply(
            f"🚀 **Forward Starting!**\n\n"
            f"📥 From: **{source_chat.title}** (`{source_chat.id}`)\n"
            f"📨 To:   **{target_chat.title}** (`{target_chat.id}`)\n"
            f"🔢 Range: `{start_id}` → `{'last' if end_id == 0 else end_id}`\n\n"
            f"Scanning messages...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏹ Stop Forward", callback_data="stop_forward")]
            ])
        )

        asyncio.create_task(
            run_forward(
                user_id=user_id,
                user_client=user_client,
                bot=client,
                source_chat=str(source_chat.id),
                target_chat=str(target_chat.id),
                status_msg=status_msg,
                start_msg_id=start_id,
                end_msg_id=end_id,
            )
        )

    # ── /stop ──────────────────────────────────────────────────
    @bot.on_message(filters.command("stop") & filters.private)
    async def stop_cmd(client: Client, msg: Message):
        user_id = msg.from_user.id
        from bot import active_tasks
        mgr = active_tasks.get(user_id)
        if mgr:
            mgr.stop()
            await msg.reply("⏹ **Forwarding stopped.** Progress saved — use /forward to resume.")
        else:
            await msg.reply("ℹ️ No active forwarding task found.")

    # ── Stop via inline button ─────────────────────────────────
    @bot.on_callback_query(filters.regex("^stop_forward$"))
    async def cb_stop(client: Client, cb: CallbackQuery):
        user_id = cb.from_user.id
        from bot import active_tasks
        mgr = active_tasks.get(user_id)
        if mgr:
            mgr.stop()
            await cb.answer("⏹ Stopping...", show_alert=True)
        else:
            await cb.answer("ℹ️ No active task.", show_alert=True)
