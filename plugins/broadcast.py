"""
broadcast.py — Advanced Multi-Format Broadcast & Notification Engine for Skinet Verse
──────────────────────────────────────────────────────────────────────────────────────
Features:
  • Multi-Format: Supports replying to ANY message (Media, Text, Stickers, Documents, Polls)
  • Direct Argument: Send direct text via /broadcast <message>
  • Interactive Wizard: Prompts the admin if invoked without reply or arguments
  • Pin Support: Add -pin flag to automatically pin the message in user chats
  • Live Telemetry Card: Real-time progress bar, speed (msgs/sec), ETA, and counters
  • Instant Cancellation: Stop broadcast via /cancelbroadcast or interactive inline button
  • Smart DB Hygiene: Automatically deletes deactivated users and records blocked users
  • Restart Broadcast: /broadcastrestart for one-click system online notifications
"""

import time
import asyncio
from datetime import timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors import InputUserDeactivated, FloodWait, UserIsBlocked
from config import Config
from database import db
from buttons import colored_markup, btn, btn_url

BROADCAST_STATE = {
    "is_running": False,
    "should_cancel": False,
    "started_by": None,
    "start_time": 0.0,
}


def _get_progress_bar(completed: int, total: int, length: int = 12) -> str:
    if total <= 0:
        return "░" * length
    fraction = min(1.0, max(0.0, completed / total))
    filled = int(fraction * length)
    return "█" * filled + "░" * (length - filled)


def _format_time(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


@Client.on_message(filters.private & filters.command(["broadcast", "bcast"]))
async def broadcast_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Restricted to Bot Administrators.", quote=True)

    if BROADCAST_STATE["is_running"]:
        return await message.reply_text(
            "<blockquote><b>⚠️ A broadcast is already running!</b>\n\n"
            "Use <code>/cancelbroadcast</code> to halt the active process.</blockquote>",
            quote=True
        )

    b_msg = message.reply_to_message
    b_text = None
    should_pin = False

    # Check for direct text argument
    cmd_parts = message.text.split(None, 1) if message.text else []
    if len(cmd_parts) > 1:
        raw_text = cmd_parts[1].strip()
        if "-pin" in raw_text:
            should_pin = True
            raw_text = raw_text.replace("-pin", "").strip()
        b_text = raw_text

    # Check for -pin flag in reply caption or text
    if b_msg:
        if b_msg.text and "-pin" in b_msg.text:
            should_pin = True
        elif b_msg.caption and "-pin" in b_msg.caption:
            should_pin = True

    # Interactive wizard if no reply and no direct text
    if not b_msg and not b_text:
        try:
            prompt_msg = await bot.ask(
                chat_id=user_id,
                text=(
                    "<blockquote><b>📢 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴇɴᴛᴇʀ</u></b></blockquote>\n\n"
                    "Please send or forward the message you wish to broadcast to all registered users.\n\n"
                    "• <b>Supported:</b> Text, Photos, Videos, Documents, Audio, Voice, Stickers\n"
                    "• <b>Pin Option:</b> Include <code>-pin</code> in text/caption to auto-pin\n"
                    "• <b>Cancel:</b> Send <code>/cancel</code> to abort."
                ),
                timeout=180
            )
        except Exception:
            return await message.reply_text("⏱ <b>Timeout:</b> Broadcast setup cancelled (3 minutes elapsed).")

        if not prompt_msg or not prompt_msg.text or prompt_msg.text == "/cancel":
            return await message.reply_text("❌ <b>Broadcast setup cancelled.</b>")

        # Check if the prompt response has -pin
        if prompt_msg.text and "-pin" in prompt_msg.text:
            should_pin = True
            prompt_msg.text = prompt_msg.text.replace("-pin", "").strip()
        elif prompt_msg.caption and "-pin" in prompt_msg.caption:
            should_pin = True
            prompt_msg.caption = prompt_msg.caption.replace("-pin", "").strip()

        b_msg = prompt_msg

    # Fetch all user IDs from MongoDB
    try:
        users_cursor = await db.get_all_users()
        user_ids = [u['id'] async for u in users_cursor if 'id' in u and u['id']]
        user_ids = list(dict.fromkeys(user_ids))  # deduplicate
    except Exception as e:
        return await message.reply_text(f"❌ <b>Database Error:</b> Failed to fetch users: <code>{e}</code>")

    total_users = len(user_ids)
    if not total_users:
        return await message.reply_text("⚠️ <b>No users found in database to broadcast to.</b>")

    # Set state
    BROADCAST_STATE["is_running"] = True
    BROADCAST_STATE["should_cancel"] = False
    BROADCAST_STATE["started_by"] = user_id
    BROADCAST_STATE["start_time"] = time.time()

    cancel_btn = colored_markup([[btn("❌ Cancel Broadcast", "bcast_cancel", "red")]])

    status_msg = await message.reply_text(
        f"<blockquote><b>📢 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴɪᴛɪᴀᴛᴇᴅ</u></b></blockquote>\n\n"
        f"👥 <b>Total Target Users:</b> <code>{total_users}</code>\n"
        f"📌 <b>Auto-Pin:</b> <code>{'Enabled ✅' if should_pin else 'Disabled ❌'}</code>\n"
        f"⏳ <b>Status:</b> <code>Dispatching messages...</code>",
        reply_markup=cancel_btn
    )

    done = 0
    success = 0
    blocked = 0
    deleted = 0
    failed = 0
    start_time = time.time()
    last_edit = 0.0

    try:
        for uid in user_ids:
            if BROADCAST_STATE["should_cancel"]:
                break

            try:
                sent_obj = None
                if b_msg:
                    sent_obj = await b_msg.copy(chat_id=uid)
                elif b_text:
                    sent_obj = await bot.send_message(chat_id=uid, text=b_text)

                if should_pin and sent_obj:
                    try:
                        await sent_obj.pin(both_sides=True)
                    except Exception:
                        pass
                success += 1

            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    if b_msg:
                        sent_obj = await b_msg.copy(chat_id=uid)
                    elif b_text:
                        sent_obj = await bot.send_message(chat_id=uid, text=b_text)
                    if should_pin and sent_obj:
                        try:
                            await sent_obj.pin(both_sides=True)
                        except Exception:
                            pass
                    success += 1
                except Exception:
                    failed += 1

            except InputUserDeactivated:
                deleted += 1
                try:
                    await db.delete_user(uid)
                except Exception:
                    pass

            except UserIsBlocked:
                blocked += 1

            except Exception:
                failed += 1

            done += 1

            # Inter-message micro-sleep to prevent flood penalties
            await asyncio.sleep(0.08)

            # Update progress status card throttled every 25 msgs or 3s
            now = time.time()
            if done % 25 == 0 or (now - last_edit >= 3.0) or done == total_users:
                last_edit = now
                elapsed = max(0.1, now - start_time)
                speed = done / elapsed
                pct = int((done / total_users) * 100)
                bar = _get_progress_bar(done, total_users, 10)
                eta = (total_users - done) / speed if speed > 0 else 0

                progress_text = (
                    f"<blockquote><b>📢 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴ ᴘʀᴏɢʀᴇss</u></b></blockquote>\n\n"
                    f"📊 <b>Progress:</b> <code>{pct}% [{bar}]</code>\n"
                    f"👥 <b>Processed:</b> <code>{done} / {total_users}</code>\n"
                    f"✅ <b>Delivered:</b> <code>{success}</code>\n"
                    f"🚫 <b>Blocked:</b> <code>{blocked}</code>\n"
                    f"🗑 <b>Deleted:</b> <code>{deleted}</code>\n"
                    f"⚠️ <b>Failed:</b> <code>{failed}</code>\n\n"
                    f"⚡ <b>Speed:</b> <code>{speed:.1f} msgs/s</code>\n"
                    f"⏰ <b>Elapsed:</b> <code>{_format_time(elapsed)}</code> | ⏳ <b>ETA:</b> <code>{_format_time(eta)}</code>"
                )
                try:
                    await status_msg.edit_text(progress_text, reply_markup=cancel_btn)
                except Exception:
                    pass

    finally:
        total_time = max(0.1, time.time() - start_time)
        avg_speed = done / total_time
        was_cancelled = BROADCAST_STATE["should_cancel"]
        BROADCAST_STATE["is_running"] = False
        BROADCAST_STATE["should_cancel"] = False

        status_title = "🛑 <u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ</u>" if was_cancelled else "✅ <u>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</u>"
        status_sub = "<i>Broadcast halted by administrator.</i>" if was_cancelled else "<i>Broadcast delivered successfully across all users!</i>"

        final_text = (
            f"<blockquote><b>📢 {status_title}</b></blockquote>\n\n"
            f"{status_sub}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>Total Target Users:</b> <code>{total_users}</code>\n"
            f"📥 <b>Total Processed:</b> <code>{done}</code>\n"
            f"✅ <b>Successfully Delivered:</b> <code>{success}</code>\n"
            f"🚫 <b>Blocked the Bot:</b> <code>{blocked}</code>\n"
            f"🗑 <b>Deleted Accounts:</b> <code>{deleted}</code>\n"
            f"⚠️ <b>Failed / Errors:</b> <code>{failed}</code>\n"
            f"⏱ <b>Total Time Taken:</b> <code>{_format_time(total_time)}</code>\n"
            f"⚡ <b>Average Throughput:</b> <code>{avg_speed:.1f} msgs/s</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>⚡ Skinet Verse Automated Telemetry</i>"
        )
        try:
            await status_msg.edit_text(final_text)
        except Exception:
            try:
                await message.reply_text(final_text)
            except Exception:
                pass


@Client.on_message(filters.private & filters.command(["cancelbroadcast", "bcastcancel"]))
async def cancel_broadcast_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Restricted to Bot Administrators.", quote=True)

    if not BROADCAST_STATE["is_running"]:
        return await message.reply_text("ℹ️ <b>No broadcast is currently running.</b>", quote=True)

    BROADCAST_STATE["should_cancel"] = True
    await message.reply_text("🛑 <b>Cancellation signal sent!</b> The broadcast will halt shortly.", quote=True)


@Client.on_callback_query(filters.regex("^bcast_cancel$"))
async def cancel_broadcast_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await db.is_admin(user_id):
        return await query.answer("⚠️ Access Denied: Admin only.", show_alert=True)

    if not BROADCAST_STATE["is_running"]:
        return await query.answer("ℹ️ Broadcast is not currently active.", show_alert=True)

    BROADCAST_STATE["should_cancel"] = True
    await query.answer("🛑 Broadcast is being stopped...", show_alert=True)


@Client.on_message(filters.private & filters.command(["broadcastrestart", "bcastrestart"]))
async def broadcast_restart_notice(bot: Client, message: Message):
    """Convenience command: One-click broadcast announcing system restart & resumption."""
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Restricted to Bot Administrators.", quote=True)

    if BROADCAST_STATE["is_running"]:
        return await message.reply_text("⚠️ A broadcast is already in progress.", quote=True)

    bot_user = getattr(bot, "username", "codexup_bot")
    notice_text = (
        f"<blockquote><b>🤖 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪᴄᴇ</u></b></blockquote>\n\n"
        f"⚡ <b>Status:</b> <code>Online & Fully Operational ✅</code>\n\n"
        f"The bot has completed a core system reboot & maintenance update.\n"
        f"All auto-forwarding pipelines, AutoSave monitors, and channels are active!\n\n"
        f"👇 <i>Click below to open your bot dashboard:</i>"
    )
    bot_markup = colored_markup([[btn_url("🚀 ᴏᴘᴇɴ ʙᴏᴛ ᴅᴀsʜʙᴏᴀʀᴅ", f"https://t.me/{bot_user}?start=start", "green")]])

    users_cursor = await db.get_all_users()
    user_ids = [u['id'] async for u in users_cursor if 'id' in u and u['id']]
    user_ids = list(dict.fromkeys(user_ids))
    total_users = len(user_ids)

    if not total_users:
        return await message.reply_text("⚠️ No users found in database.")

    BROADCAST_STATE["is_running"] = True
    BROADCAST_STATE["should_cancel"] = False
    BROADCAST_STATE["started_by"] = user_id
    BROADCAST_STATE["start_time"] = time.time()

    cancel_btn = colored_markup([[btn("❌ Cancel", "bcast_cancel", "red")]])
    status_msg = await message.reply_text(
        f"<blockquote><b>📢 <u>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ʀᴇsᴛᴀʀᴛ ɴᴏᴛɪᴄᴇ</u></b></blockquote>\n\n"
        f"👥 <b>Target Users:</b> <code>{total_users}</code>\n"
        f"⏳ <b>Status:</b> <code>Dispatching update notice...</code>",
        reply_markup=cancel_btn
    )

    done = 0
    success = 0
    start_time = time.time()

    try:
        for uid in user_ids:
            if BROADCAST_STATE["should_cancel"]:
                break
            try:
                await bot.send_message(chat_id=uid, text=notice_text, reply_markup=bot_markup)
                success += 1
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    await bot.send_message(chat_id=uid, text=notice_text, reply_markup=bot_markup)
                    success += 1
                except Exception:
                    pass
            except Exception:
                pass

            done += 1
            await asyncio.sleep(0.08)

            if done % 30 == 0 or done == total_users:
                pct = int((done / total_users) * 100)
                bar = _get_progress_bar(done, total_users, 10)
                try:
                    await status_msg.edit_text(
                        f"<blockquote><b>📢 <u>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ʀᴇsᴛᴀʀᴛ ɴᴏᴛɪᴄᴇ</u></b></blockquote>\n\n"
                        f"📊 <b>Progress:</b> <code>{pct}% [{bar}]</code>\n"
                        f"👥 <b>Delivered:</b> <code>{success} / {total_users}</code>",
                        reply_markup=cancel_btn
                    )
                except Exception:
                    pass
    finally:
        BROADCAST_STATE["is_running"] = False
        BROADCAST_STATE["should_cancel"] = False
        try:
            await status_msg.edit_text(
                f"<blockquote><b>✅ <u>ʀᴇsᴛᴀʀᴛ ɴᴏᴛɪᴄᴇ ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇ</u></b></blockquote>\n\n"
                f"Delivered update notice to <code>{success}</code> users in <code>{_format_time(time.time() - start_time)}</code>."
            )
        except Exception:
            pass
