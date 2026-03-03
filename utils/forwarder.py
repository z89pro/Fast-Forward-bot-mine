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
        # Always start fresh from start_msg_id.
        # Saved progress only used if it matches current source/range.
        progress = await db.get_progress(user_id)
        resume_from = start_msg_id   # default: start fresh
        forwarded   = 0
        if progress and progress.get("source_chat") == str(src_int) \
                    and progress.get("start_msg_id") == start_msg_id:
            # Valid resume: same source + same start point
            saved_from = progress.get("last_msg_id", start_msg_id)
            if saved_from > start_msg_id:
                resume_from = saved_from
                forwarded   = progress.get("forwarded", 0)

        est_total = (end_msg_id - resume_from + 1) if end_msg_id > 0 else 0

        await bot.edit_message_text(
            status_msg.chat.id, status_msg.id,
            f"✅ **{src_name}** — Access confirmed!\n"
            f"🚀 Streaming forward started\n"
            f"_(Fetch 100 msgs → Forward → Next 100 → ...)_"
        )
        await asyncio.sleep(1)
        await db.set_task_active(user_id, True)

        def get_cfg():
            if flood_mgr.is_safe_mode:
                return SAFE_BATCH_SIZE, SAFE_BATCH_COUNT, SAFE_DELAY, SAFE_BREAK_SECONDS, "🐢 Safe"
            return FAST_BATCH_SIZE, FAST_BATCH_COUNT, FAST_DELAY, FAST_BREAK_SECONDS, "⚡ Fast"

        # ── MANUAL PAGINATION LOOP ─────────────────────────────
        # offset_id = where to start this page (exclusive upper bound)
        # Updated after each page to the oldest msg_id seen so far.
        offset_id   = (end_msg_id + 1) if end_msg_id > 0 else 0
        batch_cycle = 0

        while not flood_mgr.stopped:
            batch_size, batch_count, delay, break_sec, mode_name = get_cfg()

            # ── Fetch one page (100 msgs max) ──────────────────
            page = []
            async for msg in user_client.get_chat_history(
                src_int, offset_id=offset_id, limit=100
            ):
                mid = msg.id
                if mid < resume_from:
                    break        # past lower boundary
                if msg.empty:
                    continue     # deleted msg
                page.append(mid) # arrives newest→oldest

            if not page:
                # Find actual message ID range for helpful error
                actual_latest = 0
                actual_oldest = 0
                try:
                    # Peek at latest message
                    async for m in user_client.get_chat_history(src_int, limit=1):
                        actual_latest = m.id
                    # Peek at oldest message
                    async for m in user_client.get_chat_history(src_int, limit=1, offset=-1):
                        actual_oldest = m.id
                except Exception:
                    pass

                range_hint = (
                    f"\n📌 **Your channel's actual message IDs:**\n"
                    f"Oldest: `{actual_oldest}` | Latest: `{actual_latest}`\n"
                    f"→ Use these IDs in start/end!"
                ) if actual_latest else ""

                await flood_mgr._notify(
                    f"❌ **No messages in specified range!**\n\n"
                    f"You entered: end = `{end_msg_id}`\n"
                    f"But messages with ID ≤ `{end_msg_id}` don't exist in this channel.\n"
                    f"{range_hint}\n"
                    f"💡 **Tip:** Use end = `0` to forward ALL messages."
                )

                break  # nothing left to forward

            # page is newest→oldest; reverse → oldest→newest for forwarding
            page.reverse()

            # Update offset for NEXT page = one below the oldest msg we just got
            oldest_in_page = page[0]
            next_offset    = oldest_in_page  # get_chat_history(offset_id=X) → msgs with id < X

            # ── Forward this page message by message ──────────
            idx = 0
            forward_restricted = False  # source has content protection

            while idx < len(page) and not flood_mgr.stopped:
                chunk = page[idx: idx + batch_size]
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
                        # Source has content protection — cannot copy ANY message
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
                        # Could be PeerIdInvalid (e.g. forward restricted on a private chat)
                        # We don't want to stop the whole loop on one bad message, but if it keeps happening,
                        # the chunk error handler below will catch it.
                        last_err = str(e)

                if flood_mgr.stopped or forward_restricted:
                    break

                # Only count ACTUALLY copied messages — never fake progress
                forwarded   += copied
                est_total    = max(est_total, forwarded)
                batch_cycle += 1
                idx         += len(chunk)  # always advance

                if copied > 0:
                    flood_mgr.register_sent(copied)
                    await db.save_progress(user_id, chunk[0], forwarded,
                                           source_chat=str(src_int),
                                           start_msg_id=start_msg_id)
                elif last_err:
                    # Entire chunk failed — show why
                    await flood_mgr._notify(
                        f"⚠️ Chunk failed (skipping): `{last_err}`\n"
                        f"Forwarded so far: **{forwarded:,}**"
                    )
                    await asyncio.sleep(2)
                    continue

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


            # If page is completely empty or we've reached below our requested start_id boundary
            if oldest_in_page < resume_from:
                break

            # Move offset pointer for next page
            offset_id = next_offset

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
        await bot.edit_message_text(
            status_msg.chat.id, status_msg.id,
            f"❌ **Error:** `{e}`\n\nProgress saved. Use /forward to retry."
        )
    finally:
        active_tasks.pop(user_id, None)
        await db.set_task_active(user_id, False)
