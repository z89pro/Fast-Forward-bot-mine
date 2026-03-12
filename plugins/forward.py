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

        # ── Step 1: Ask for forwarded first message ──────────
        ask1 = await msg.reply(
            "📤 **Step 1 of 2 — First Message**\n\n"
            "**Forward the first message** from the source channel to me.\n\n"
            "_I will automatically detect the channel and start ID._\n"
            "_Send /cancel to abort._"
        )

        try:
            fwd_first: Message = await client.listen(
                filters.private & filters.user(user_id),
                timeout=120
            )
        except asyncio.TimeoutError:
            await ask1.reply("⌛ Timed out. Send /forward to try again.")
            return

        if fwd_first.text and fwd_first.text.strip().lower() == "/cancel":
            await fwd_first.reply("❌ Cancelled.")
            return

        # Extract source and start ID
        if not fwd_first.forward_from_chat:
            await fwd_first.reply("❌ This message is **not forwarded** or the source is private.\n"
                                  "Please forward a message from a public channel or a channel where your account is a member.")
            return

        source_chat_id = fwd_first.forward_from_chat.id
        start_id = fwd_first.forward_from_message_id

        if not start_id:
            await fwd_first.reply("❌ Could not extract message ID. Make sure 'Forwarded from' is visible.")
            return

        # ── Step 2: Ask for forwarded last message or '0' ─────
        ask2 = await fwd_first.reply(
            f"✅ Source: **{fwd_first.forward_from_chat.title}** (`{source_chat_id}`)\n"
            f"🔢 Start ID: `{start_id}`\n\n"
            f"📥 **Step 2 of 2 — Last Message**\n\n"
            f"**Forward the last message** to forward until,\n"
            f"OR send `0` to forward until the very latest message.\n\n"
            f"_Send /cancel to abort._"
        )

        try:
            fwd_last: Message = await client.listen(
                filters.private & filters.user(user_id),
                timeout=120
            )
        except asyncio.TimeoutError:
            await ask2.reply("⌛ Timed out. Send /forward to try again.")
            return

        if fwd_last.text and fwd_last.text.strip().lower() == "/cancel":
            await fwd_last.reply("❌ Cancelled.")
            return

        end_id = 0
        if fwd_last.text and fwd_last.text.strip() == "0":
            end_id = 0
        elif fwd_last.forward_from_chat:
            if fwd_last.forward_from_chat.id != source_chat_id:
                await fwd_last.reply("❌ Error: You forwarded a message from a **different channel**.\nTry /forward again.")
                return
            end_id = fwd_last.forward_from_message_id
            if not end_id:
                await fwd_last.reply("❌ Could not extract end message ID. Try /forward again.")
                return
        else:
            try:
                end_id = int(fwd_last.text.strip())
            except (ValueError, AttributeError):
                await fwd_last.reply("❌ Invalid input. Forward a message or send `0`.")
                return

        # ── Confirm and launch ─────────────────────────────────
        try:
            target_chat = await resolve_chat(user_client, target)
        except Exception as e:
            await fwd_last.reply(f"❌ Cannot access target: `{e}`\nCheck /target and try again.")
            return
        source_chat_title = fwd_first.forward_from_chat.title

        status_msg = await fwd_last.reply(
            f"🚀 **Forward Starting!**\n\n"
            f"📥 From: **{source_chat_title}** (`{source_chat_id}`)\n"
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
                source_chat=str(source_chat_id),
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
