"""
utils/forwarder.py
CORRECT Streaming Forward Engine

How it works:
    while True:
        page = get_history(offset_id=X, limit=100)   ← 1 API call, 100 msgs
        forward(page)                                  ← 1 copy_messages call
        X = oldest_msg_in_page                         ← move pointer backward
        if page < 100: break                           ← last page reached

This way: 1 lakh msgs = 1000 GetHistory + 1000 copy_messages calls.
Pre-scan is completely eliminated. Forwarding starts in seconds.
"""
import asyncio
import logging
from pyrogram import Client
from pyrogram.errors import (
    MessageIdInvalid, ChannelPrivate, ChatWriteForbidden,
    ChatAdminRequired, ChatForwardsRestricted,
)
from utils.flood_manager import FloodManager, countdown_break
from utils.session_manager import resolve_chat
import database as db
from config import (
    FAST_BATCH_SIZE, FAST_BATCH_COUNT, FAST_DELAY, FAST_BREAK_SECONDS,
    SAFE_BATCH_SIZE, SAFE_BATCH_COUNT, SAFE_DELAY, SAFE_BREAK_SECONDS,
)

logger = logging.getLogger("Forwarder")


def _build_status(forwarded: int, total: int, mode: str, flood_count: int) -> str:
    if total > 0:
        pct = int((forwarded / total) * 100)
        bar_filled = pct // 5
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        bar_line = f"`[{bar}]` **{pct}%**\n"
        total_line = f"✅ Forwarded: **{forwarded:,}** / **{total:,}**\n"
    else:
        bar_line = ""
        total_line = f"✅ Forwarded: **{forwarded:,}**\n"
    return (
        f"📤 **Forwarding in Progress**\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"{bar_line}"
        f"{total_line}"
        f"⚡ Mode: **{mode}**\n"
        f"🌊 FloodWaits: **{flood_count}/3**\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"_Send /stop to cancel_"
    )


async def run_forward(
    user_id: int,
    user_client: Client,
    bot: Client,
    source_chat: str,
    target_chat: str,
    status_msg,
    start_msg_id: int = 1,
    end_msg_id: int = 0,
):
    flood_mgr = FloodManager(user_id=user_id, status_msg=status_msg, bot=bot)

    from bot import active_tasks
    active_tasks[user_id] = flood_mgr

    try:
        await bot.edit_message_text(
            status_msg.chat.id, status_msg.id,
            "🔍 Connecting to source & target..."
        )

        # ── Resolve peers ──────────────────────────────────────
        try:
            src_obj = await resolve_chat(user_client, source_chat)
        except Exception as e:
            await bot.edit_message_text(status_msg.chat.id, status_msg.id,
                f"❌ **Source Access Failed!**\n\n{e}")
            return

        try:
            await resolve_chat(user_client, target_chat)
        except Exception as e:
            await bot.edit_message_text(status_msg.chat.id, status_msg.id,
                f"❌ **Target Access Failed!**\n\n{e}")
            return

        src_int = src_obj.id
        tgt_int = int(target_chat) if str(target_chat).lstrip('-').isdigit() else target_chat
        src_name = getattr(src_obj, "title", str(source_chat))

        # ── Resume support ─────────────────────────────────────
        # For forward-chronological: resume from the next message after last_msg_id.
        progress = await db.get_progress(user_id)
        resume_from = start_msg_id   # default: start fresh
        forwarded   = 0
        if progress and progress.get("source_chat") == str(src_int) \
                    and progress.get("start_msg_id") == start_msg_id:
            # Valid resume: same source + same start point
            saved_until = progress.get("last_msg_id", 0)
            if saved_until >= start_msg_id:
                resume_from = saved_until + 1
                forwarded   = progress.get("forwarded", 0)

        est_total = (end_msg_id - resume_from + 1) if end_msg_id > 0 and resume_from <= end_msg_id else 0

        # Edge case: resume_from already past end — task is complete
        if end_msg_id > 0 and resume_from > end_msg_id:
            await bot.edit_message_text(
                status_msg.chat.id, status_msg.id,
                f"✅ **Already Complete!**\n\n"
                f"📨 Previously forwarded: **{forwarded:,}** messages\n"
                f"_All messages in range were already forwarded._"
            )
            await db.clear_progress(user_id)
            return

        await db.set_task_active(user_id, True)

        def get_cfg():
            if flood_mgr.is_safe_mode:
                return SAFE_BATCH_SIZE, SAFE_BATCH_COUNT, SAFE_DELAY, SAFE_BREAK_SECONDS, "🐢 Safe"
            return FAST_BATCH_SIZE, FAST_BATCH_COUNT, FAST_DELAY, FAST_BREAK_SECONDS, "⚡ Fast"

        # ═══════════════════════════════════════════════════════
        # PHASE 1 — PRESCAN: Collect all message IDs in range
        # Pyrogram's get_chat_history goes newest→oldest natively.
        # We collect all IDs in that range, then sort them ascending
        # to get the correct chronological (oldest→newest) order.
        # ═══════════════════════════════════════════════════════
        await bot.edit_message_text(
            status_msg.chat.id, status_msg.id,
            f"🔍 **Scanning messages...**\n"
            f"_(Collecting message IDs in range for correct order)_"
        )

        all_ids: list[int] = []
        scan_offset = (end_msg_id + 1) if end_msg_id > 0 else 0
        scan_done   = False

        while not flood_mgr.stopped and not scan_done:
            batch_ids = []
            async for msg in user_client.get_chat_history(
                src_int, offset_id=scan_offset, limit=100
            ):
                mid = msg.id
                if mid < resume_from:
                    scan_done = True
                    break
                if not msg.empty:
                    batch_ids.append(mid)

            if not batch_ids:
                break  # nothing left in channel

            all_ids.extend(batch_ids)

            # Move pointer to the oldest ID in this page (batch_ids is newest→oldest)
            scan_offset = batch_ids[-1]

            # Update scan progress periodically
            if len(all_ids) % 1000 < 100 and len(all_ids) >= 1000:
                await flood_mgr._notify(
                    f"🔍 **Scanning...** `{len(all_ids):,}` messages found so far"
                )

            if scan_done or len(batch_ids) < 100:
                break  # reached boundary or end of channel

        if not all_ids:
            await bot.edit_message_text(
                status_msg.chat.id, status_msg.id,
                f"❌ **No messages found in the specified range!**\n\n"
                f"Make sure your account has access to the source channel."
            )
            return

        # Sort ascending = oldest → newest (chronological)
        all_ids.sort()
        # Only keep up to end_msg_id
        if end_msg_id > 0:
            all_ids = [mid for mid in all_ids if mid <= end_msg_id]

        est_total = len(all_ids)

        await bot.edit_message_text(
            status_msg.chat.id, status_msg.id,
            f"✅ **Scan complete!** Found `{est_total:,}` messages\n"
            f"🚀 **Starting chronological forward...**\n"
            f"_(Oldest → Newest)_"
        )
        await asyncio.sleep(1)

        # ═══════════════════════════════════════════════════════
        # PHASE 2 — FORWARD: Send in chronological order
        # ═══════════════════════════════════════════════════════
        idx         = 0
        batch_cycle = 0
        forward_restricted = False

        while idx < len(all_ids) and not flood_mgr.stopped:
            batch_size, batch_count, delay, break_sec, mode_name = get_cfg()

            chunk = all_ids[idx: idx + batch_size]
            copied = 0
            last_err = None

            for msg_id in chunk:
                if flood_mgr.stopped:
                    break
                try:
                    await flood_mgr.run(
                        user_client.copy_message,
                        tgt_int,
                        src_int,
                        msg_id
                    )
                    copied += 1
                except ChatWriteForbidden:
                    await flood_mgr._notify(
                        "❌ **No post permission in target!**\n"
                        "Ask admin to grant post rights."
                    )
                    flood_mgr.stop(); break
                except ChatAdminRequired:
                    await flood_mgr._notify("❌ **Admin rights required in target!**")
                    flood_mgr.stop(); break
                except ChatForwardsRestricted:
                    await flood_mgr._notify(
                        "❌ **Source has Content Protection enabled!**\n\n"
                        "This channel/group has restricted saving & forwarding.\n"
                        "Cannot copy messages from this source.\n\n"
                        "Ask the admin to disable content protection, or use a different source."
                    )
                    forward_restricted = True
                    flood_mgr.stop(); break
                except (MessageIdInvalid, ChannelPrivate):
                    pass  # deleted/inaccessible — skip silently
                except Exception as e:
                    last_err = str(e)

            if flood_mgr.stopped or forward_restricted:
                break

            forwarded   += copied
            batch_cycle += 1
            idx         += len(chunk)  # always advance

            if copied > 0:
                flood_mgr.register_sent(copied)
                await db.save_progress(user_id, chunk[-1], forwarded,
                                       source_chat=str(src_int),
                                       start_msg_id=start_msg_id)
            elif last_err:
                await flood_mgr._notify(
                    f"⚠️ Chunk skipped: `{last_err}`\n"
                    f"Forwarded so far: **{forwarded:,}**"
                )
                await asyncio.sleep(2)

            # Status update
            await flood_mgr._notify(
                _build_status(forwarded, est_total, mode_name, flood_mgr.flood_count)
            )

            # Anti-ban delay
            await flood_mgr.smart_delay(delay)

            # Break after N batch cycles
            if batch_cycle >= batch_count:
                batch_cycle = 0
                label = (
                    "1-min Safety Break (Safe Mode)"
                    if flood_mgr.is_safe_mode
                    else "5-min Break (1,000 messages sent)"
                )
                await countdown_break(break_sec, label, flood_mgr)


        # ── Done ───────────────────────────────────────────────
        if not flood_mgr.stopped:
            await bot.edit_message_text(
                status_msg.chat.id, status_msg.id,
                f"✅ **Forwarding Complete!**\n\n"
                f"📨 Total Forwarded: **{forwarded:,}** messages\n"
                f"🌊 FloodWaits hit: **{flood_mgr.flood_count}**"
            )
            await db.clear_progress(user_id)
            await db.reset_flood_count(user_id)
        else:
            await bot.edit_message_text(
                status_msg.chat.id, status_msg.id,
                f"⏹ **Forwarding Stopped**\n\n"
                f"📨 Forwarded: **{forwarded:,}** messages\n"
                f"💾 Progress saved. Use /forward to resume."
            )

    except Exception as e:
        logger.exception(f"Forwarder error for user {user_id}: {e}")
        await bot.edit_message_text(
            status_msg.chat.id, status_msg.id,
            f"❌ **Error:** `{e}`\n\nProgress saved. Use /forward to retry."
        )
    finally:
        active_tasks.pop(user_id, None)
        await db.set_task_active(user_id, False)
