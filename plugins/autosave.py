import re
import asyncio
import logging
from config import Config, temp
from database import db
from translation import Translation
from .test import CLIENT, start_clone_bot
from .regix import custom_caption, copy
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from buttons import colored_markup

logger = logging.getLogger("SkinetAutoSave")

def get_autosave_markup(is_running: bool, count: int):
    status_btn = InlineKeyboardButton("⏹️ sᴛᴏᴘ ᴍᴏɴɪᴛᴏʀ", callback_data="autosave#toggle_monitor") if is_running else InlineKeyboardButton("▶️ sᴛᴀʀᴛ ᴍᴏɴɪᴛᴏʀ", callback_data="autosave#toggle_monitor")
    buttons = [
        [status_btn],
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="autosave#add_channel"),
            InlineKeyboardButton(f"📋 ᴄʜᴀɴɴᴇʟs ({count})", callback_data="autosave#list_channels")
        ],
        [
            InlineKeyboardButton("🎯 sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs", callback_data="autosave#filters"),
            InlineKeyboardButton("📤 ᴜᴘʟᴏᴀᴅ ᴅᴇsᴛɪɴᴀᴛɪᴏɴ", callback_data="autosave#destinations")
        ],
        [
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")
        ]
    ]
    return colored_markup(buttons)

async def build_autosave_text(user_id: int):
    channels = await db.get_user_live_forwards(user_id)
    is_running = user_id in temp.LIVE_TASKS and temp.LIVE_TASKS[user_id].is_connected
    status_str = "🟢 <b>Active & Monitoring 24/7</b>" if is_running else "🔴 <b>Stopped</b>"
    user_channels = await db.get_user_channels(user_id)
    default_dest = user_channels[0]['title'] if user_channels else "None (Set in /settings)"
    
    text = (
        "🚀 <b><u>sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ & ʟɪᴠᴇ ᴍᴏɴɪᴛᴏʀ</u></b> ⚡️\n\n"
        "<i>Powered by Skinet Verse</i>\n\n"
        f"🔥 <b>Status:</b> {status_str}\n"
        f"📡 <b>Monitored Channels:</b> <code>{len(channels)}</code>\n"
        f"📤 <b>Default Destination:</b> <code>{default_dest}</code>\n\n"
        "<b>🌟 Live Monitoring Highlights:</b>\n"
        "✅ <b>Real-time Interception:</b> Captures incoming lectures/files instantly.\n"
        "🎯 <b>Smart Filters:</b> Route only Videos, Notes/PDFs, Audios, or Photos.\n"
        "🛠 <b>Skinet Clean Engine:</b> Strips competitor links, handles & ads automatically.\n"
        "📤 <b>Multi-Channel Routing:</b> Dedicated target channel per source.\n\n"
        "👇 <i>Manage your live monitors using the buttons below:</i>"
    )
    return text, is_running, len(channels)

# ================= COMMAND /autosave =================

@Client.on_message(filters.private & filters.command(["autosave", "live", "monitor"]))
async def autosave_cmd(bot, message):
    user_id = message.from_user.id
    text, is_running, count = await build_autosave_text(user_id)
    await message.reply_text(text, reply_markup=get_autosave_markup(is_running, count))

# ================= CALLBACK HANDLER =================

@Client.on_callback_query(filters.regex(r"^autosave"))
async def autosave_callback(bot, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data.split("#")[1] if "#" in query.data else "main"

    if data == "main":
        text, is_running, count = await build_autosave_text(user_id)
        await query.message.edit_text(text, reply_markup=get_autosave_markup(is_running, count))

    elif data == "toggle_monitor":
        if user_id in temp.LIVE_TASKS and temp.LIVE_TASKS[user_id].is_connected:
            # Stop monitor
            client = temp.LIVE_TASKS.pop(user_id, None)
            if client:
                try:
                    await client.stop()
                except Exception:
                    pass
            await query.answer("🛑 AutoSave Monitor Stopped!", show_alert=True)
        else:
            # Start monitor
            success, err = await start_autosave_monitor(user_id, bot)
            if success:
                await query.answer("🚀 AutoSave Monitor Started!", show_alert=True)
            else:
                await query.answer(f"Failed to start: {err}", show_alert=True)
        text, is_running, count = await build_autosave_text(user_id)
        await query.message.edit_text(text, reply_markup=get_autosave_markup(is_running, count))

    elif data == "add_channel":
        await query.message.delete()
        _bot = await db.get_bot(user_id)
        if not _bot:
            return await bot.send_message(
                user_id,
                "<b>❌ Please add a Bot or UserBot first in /settings to use AutoSave Monitoring!</b>\n\n"
                "• <b>UserBot (Recommended):</b> Can monitor ANY private or restricted channel you are in.\n"
                "• <b>Bot Token:</b> Can monitor channels where your bot is an Administrator.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Open Settings", callback_data="settings#main")]])
            )
        
        src_msg = await bot.ask(
            user_id,
            text=(
                "<b>📡 Send Source Channel link or Chat ID to monitor:</b>\n\n"
                "Examples:\n"
                "• <code>https://t.me/c/1234567890</code> (Private channel)\n"
                "• <code>https://t.me/public_channel</code> (Public channel)\n"
                "• <code>-1001234567890</code> (Direct Chat ID)\n\n"
                "<i>Send /cancel to abort</i>"
            ),
            timeout=300
        )
        if not src_msg.text or src_msg.text.startswith("/cancel"):
            return await bot.send_message(user_id, "**Process cancelled!**")
        
        src_raw = src_msg.text.strip()
        link_regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)")
        match = link_regex.search(src_raw)
        if match:
            src_id = match.group(4)
            if src_id.isnumeric():
                src_id = int("-100" + src_id)
        elif src_raw.lstrip("-").isdigit():
            src_id = int(src_raw)
        else:
            src_id = src_raw

        # Ask destination
        channels = await db.get_user_channels(user_id)
        default_dest = channels[0]['chat_id'] if channels else None
        default_title = channels[0]['title'] if channels else "Global Default"

        dst_msg = await bot.ask(
            user_id,
            text=(
                f"<b>📤 Send Destination Channel link/ID:</b>\n\n"
                f"Or send <code>/skip</code> to use your default destination:\n"
                f"👉 <b>Default:</b> <code>{default_title}</code>\n\n"
                "<i>Send /cancel to abort</i>"
            ),
            timeout=300
        )
        if not dst_msg.text or dst_msg.text.startswith("/cancel"):
            return await bot.send_message(user_id, "**Process cancelled!**")
        
        if dst_msg.text.lower() == "/skip":
            if not default_dest:
                return await bot.send_message(user_id, "**❌ No default destination found! Please set a channel in /settings first.**")
            dst_id = default_dest
            dst_title = default_title
        else:
            dst_raw = dst_msg.text.strip()
            dst_match = link_regex.search(dst_raw)
            if dst_match:
                dst_id = dst_match.group(4)
                if dst_id.isnumeric():
                    dst_id = int("-100" + dst_id)
            elif dst_raw.lstrip("-").isdigit():
                dst_id = int(dst_raw)
            else:
                dst_id = dst_raw
            dst_title = str(dst_id)

        src_title = str(src_id)
        try:
            chat = await bot.get_chat(src_id)
            src_title = chat.title or str(src_id)
        except Exception:
            pass

        await db.add_live_forward(user_id, src_id, dst_id, src_title, dst_title)
        
        # If running, restart monitor with new channel
        if user_id in temp.LIVE_TASKS:
            await start_autosave_monitor(user_id, bot)

        await bot.send_message(
            user_id,
            f"<b>✅ Channel Added to Live Monitoring!</b>\n\n"
            f"📡 <b>Source:</b> <code>{src_title}</code>\n"
            f"📤 <b>Destination:</b> <code>{dst_title}</code>\n"
            f"⚡️ <b>Engine:</b> Skinet Verse AutoSave\n\n"
            "<i>Click 'Start Monitor' to begin listening for new posts in real-time.</i>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ sᴛᴀʀᴛ ᴍᴏɴɪᴛᴏʀ", callback_data="autosave#toggle_monitor")],
                [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴀᴜᴛᴏsᴀᴠᴇ", callback_data="autosave#main")]
            ])
        )

    elif data == "list_channels":
        channels = await db.get_user_live_forwards(user_id)
        if not channels:
            return await query.answer("No channels currently monitored!", show_alert=True)
        
        buttons = []
        for ch in channels:
            f_chat = ch.get('from_chat')
            title = ch.get('from_title', str(f_chat))
            active = "🟢" if ch.get('active', True) else "🔴"
            buttons.append([
                InlineKeyboardButton(f"{active} {title}", callback_data=f"autosave#toggle_chan_{f_chat}"),
                InlineKeyboardButton("🗑️", callback_data=f"autosave#del_chan_{f_chat}")
            ])
        buttons.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main")])
        await query.message.edit_text(
            "📋 **ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs**\n\nClick on a channel to Toggle ON/OFF or click 🗑️ to Delete:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("del_chan_"):
        f_chat = data.split("del_chan_")[1]
        await db.remove_live_forward(user_id, f_chat)
        await query.answer("Channel removed from monitoring!", show_alert=True)
        if user_id in temp.LIVE_TASKS:
            await start_autosave_monitor(user_id, bot)
        channels = await db.get_user_live_forwards(user_id)
        if not channels:
            text, is_running, count = await build_autosave_text(user_id)
            return await query.message.edit_text(text, reply_markup=get_autosave_markup(is_running, count))
        buttons = []
        for ch in channels:
            fc = ch.get('from_chat')
            title = ch.get('from_title', str(fc))
            active = "🟢" if ch.get('active', True) else "🔴"
            buttons.append([
                InlineKeyboardButton(f"{active} {title}", callback_data=f"autosave#toggle_chan_{fc}"),
                InlineKeyboardButton("🗑️", callback_data=f"autosave#del_chan_{fc}")
            ])
        buttons.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main")])
        await query.message.edit_text(
            "📋 **ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs**\n\nClick on a channel to Toggle ON/OFF or click 🗑️ to Delete:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("toggle_chan_"):
        f_chat = data.split("toggle_chan_")[1]
        new_val = await db.toggle_live_status(user_id, f_chat)
        status_txt = "Active 🟢" if new_val else "Paused 🔴"
        await query.answer(f"Channel is now {status_txt}", show_alert=True)
        channels = await db.get_user_live_forwards(user_id)
        buttons = []
        for ch in channels:
            fc = ch.get('from_chat')
            title = ch.get('from_title', str(fc))
            active = "🟢" if ch.get('active', True) else "🔴"
            buttons.append([
                InlineKeyboardButton(f"{active} {title}", callback_data=f"autosave#toggle_chan_{fc}"),
                InlineKeyboardButton("🗑️", callback_data=f"autosave#del_chan_{fc}")
            ])
        buttons.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main")])
        await query.message.edit_text(
            "📋 **ᴍᴏɴɪᴛᴏʀᴇᴅ ᴄʜᴀɴɴᴇʟs**\n\nClick on a channel to Toggle ON/OFF or click 🗑️ to Delete:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "filters":
        configs = await db.get_configs(user_id)
        filters_cfg = configs.get('filters', {})
        
        def mark(key):
            return "✅" if filters_cfg.get(key, True) else "❌"

        buttons = [
            [
                InlineKeyboardButton(f"🎥 ᴠɪᴅᴇᴏs {mark('video')}", callback_data="autosave#toggle_filter_video"),
                InlineKeyboardButton(f"📸 ᴘʜᴏᴛᴏs {mark('photo')}", callback_data="autosave#toggle_filter_photo")
            ],
            [
                InlineKeyboardButton(f"📁 ᴅᴏᴄᴜᴍᴇɴᴛs {mark('document')}", callback_data="autosave#toggle_filter_document"),
                InlineKeyboardButton(f"🎵 ᴀᴜᴅɪᴏs {mark('audio')}", callback_data="autosave#toggle_filter_audio")
            ],
            [
                InlineKeyboardButton(f"💬 ᴛᴇxᴛs {mark('text')}", callback_data="autosave#toggle_filter_text"),
                InlineKeyboardButton(f"🎞️ ɢɪғs {mark('animation')}", callback_data="autosave#toggle_filter_animation")
            ],
            [
                InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main")
            ]
        ]
        await query.message.edit_text(
            "🎯 **sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs**\n\nChoose what types of media you want AutoSave to automatically capture and forward:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("toggle_filter_"):
        filter_key = data.split("toggle_filter_")[1]
        configs = await db.get_configs(user_id)
        filters_cfg = configs.get('filters', {})
        current = filters_cfg.get(filter_key, True)
        filters_cfg[filter_key] = not current
        configs['filters'] = filters_cfg
        await db.update_configs(user_id, configs)
        await query.answer(f"{filter_key.title()} filter updated!")

        def mark(key):
            return "✅" if filters_cfg.get(key, True) else "❌"

        buttons = [
            [
                InlineKeyboardButton(f"🎥 ᴠɪᴅᴇᴏs {mark('video')}", callback_data="autosave#toggle_filter_video"),
                InlineKeyboardButton(f"📸 ᴘʜᴏᴛᴏs {mark('photo')}", callback_data="autosave#toggle_filter_photo")
            ],
            [
                InlineKeyboardButton(f"📁 ᴅᴏᴄᴜᴍᴇɴᴛs {mark('document')}", callback_data="autosave#toggle_filter_document"),
                InlineKeyboardButton(f"🎵 ᴀᴜᴅɪᴏs {mark('audio')}", callback_data="autosave#toggle_filter_audio")
            ],
            [
                InlineKeyboardButton(f"💬 ᴛᴇxᴛs {mark('text')}", callback_data="autosave#toggle_filter_text"),
                InlineKeyboardButton(f"🎞️ ɢɪғs {mark('animation')}", callback_data="autosave#toggle_filter_animation")
            ],
            [
                InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main")
            ]
        ]
        await query.message.edit_text(
            "🎯 **sᴍᴀʀᴛ ᴍᴇᴅɪᴀ ғɪʟᴛᴇʀs**\n\nChoose what types of media you want AutoSave to automatically capture and forward:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "destinations":
        channels = await db.get_user_live_forwards(user_id)
        text = "📤 **ᴄᴜsᴛᴏᴍ ᴜᴘʟᴏᴀᴅ ᴅᴇsᴛɪɴᴀᴛɪᴏɴs**\n\n"
        if not channels:
            text += "No monitored channels yet! Use ➕ **Add Channel** first."
        else:
            for ch in channels:
                text += f"• **{ch.get('from_title', 'Source')}** ➡️ `{ch.get('to_title', 'Target')}`\n"
        buttons = [[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="autosave#main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# ================= BACKGROUND MONITOR ENGINE =================

async def start_autosave_monitor(user_id: int, bot_client: Client):
    _bot = await db.get_bot(user_id)
    if not _bot:
        return False, "Please add a Bot or UserBot in /settings first."

    monitored = await db.get_user_live_forwards(user_id)
    active_channels = [ch for ch in monitored if ch.get('active', True)]
    if not active_channels:
        return False, "No active channels to monitor. Use ➕ Add Channel first."

    # Stop any existing monitor task
    if user_id in temp.LIVE_TASKS:
        old = temp.LIVE_TASKS.pop(user_id, None)
        if old:
            try:
                await old.stop()
            except Exception:
                pass

    try:
        userbot = await start_clone_bot(CLIENT().client(_bot))
    except Exception as e:
        logger.error(f"Failed to start client for autosave: {e}")
        return False, str(e)

    # Map monitored chat IDs to their destination info
    chat_map = {}
    for ch in active_channels:
        from_c = ch.get('from_chat')
        try:
            from_c_id = int(from_c)
        except Exception:
            from_c_id = from_c
        chat_map[from_c_id] = ch
        chat_map[str(from_c)] = ch

    # Register real-time incoming message handler
    @userbot.on_message()
    async def incoming_live_message(client: Client, message: Message):
        chat_id = message.chat.id
        match_info = chat_map.get(chat_id) or chat_map.get(str(chat_id)) or (chat_map.get(f"@{message.chat.username}") if message.chat.username else None)
        if not match_info:
            return

        # Check Smart Media Filters
        user_configs = await db.get_configs(user_id)
        filters_cfg = user_configs.get('filters', {})
        
        if message.video and not filters_cfg.get('video', True):
            return
        if message.photo and not filters_cfg.get('photo', True):
            return
        if message.document and not filters_cfg.get('document', True):
            return
        if message.audio and not filters_cfg.get('audio', True):
            return
        if message.text and not filters_cfg.get('text', True):
            return
        if message.animation and not filters_cfg.get('animation', True):
            return

        to_chat = match_info.get('to_chat')
        try:
            to_chat = int(to_chat)
        except Exception:
            pass

        try:
            clean_cap = user_configs.get('clean_caption', False)
            rep_words = user_configs.get('replace_words', {})
            cap = custom_caption(
                message, 
                user_configs.get('caption'), 
                clean_caption=clean_cap, 
                replace_words=rep_words,
                user_configs=user_configs
            )
            
            dump_target = await db.get_effective_dump_channel()

            if user_configs.get('forward_tag'):
                await client.forward_messages(
                    chat_id=to_chat,
                    from_chat_id=chat_id,
                    message_ids=message.id,
                    protect_content=user_configs.get('protect')
                )
                if dump_target and str(dump_target) != str(to_chat):
                    try:
                        await client.forward_messages(chat_id=dump_target, from_chat_id=chat_id, message_ids=message.id)
                    except Exception:
                        pass
            else:
                if message.media:
                    media_attr = getattr(message, message.media.value, None)
                    file_id = getattr(media_attr, 'file_id', None) if media_attr else None
                    if file_id and cap:
                        await client.send_cached_media(
                            chat_id=to_chat,
                            file_id=file_id,
                            caption=cap,
                            protect_content=user_configs.get('protect')
                        )
                        if dump_target and str(dump_target) != str(to_chat):
                            try:
                                await client.send_cached_media(chat_id=dump_target, file_id=file_id, caption=cap)
                            except Exception:
                                pass
                    else:
                        await client.copy_message(
                            chat_id=to_chat,
                            from_chat_id=chat_id,
                            message_id=message.id,
                            caption=cap,
                            protect_content=user_configs.get('protect')
                        )
                        if dump_target and str(dump_target) != str(to_chat):
                            try:
                                await client.copy_message(chat_id=dump_target, from_chat_id=chat_id, message_id=message.id, caption=cap)
                            except Exception:
                                pass
                elif message.text:
                    await client.send_message(
                        chat_id=to_chat,
                        text=cap or message.text,
                        protect_content=user_configs.get('protect')
                    )
                    if dump_target and str(dump_target) != str(to_chat):
                        try:
                            await client.send_message(chat_id=dump_target, text=cap or message.text)
                        except Exception:
                            pass
            logger.info(f"Skinet AutoSave: Forwarded new message {message.id} from {chat_id} to {to_chat}")
            if Config.LOG_CHANNEL:
                try:
                    await bot_client.send_message(
                        chat_id=Config.LOG_CHANNEL,
                        text=f"📡 <b>#AutoSaveCaptured</b>\n\n⚡️ <b>Engine:</b> Skinet Verse\n👤 <b>User:</b> <code>{user_id}</code>\n📡 <b>Source:</b> <code>{chat_id}</code>\n🎯 <b>Destination:</b> <code>{to_chat}</code>\n🆔 <b>Message ID:</b> <code>{message.id}</code>"
                    )
                except Exception:
                    pass
        except Exception as err:
            logger.error(f"AutoSave Error on message {message.id}: {err}")

    temp.LIVE_TASKS[user_id] = userbot
    return True, None

async def resume_all_autosave_monitors(bot_client: Client):
    try:
        active_forwards = await db.get_all_active_live_forwards()
        if not active_forwards:
            return
        user_ids = list(set([doc['user_id'] for doc in active_forwards if 'user_id' in doc]))
        logger.info(f"Resuming AutoSave live monitors for {len(user_ids)} users...")
        for uid in user_ids:
            try:
                success, err = await start_autosave_monitor(uid, bot_client)
                if success:
                    logger.info(f"✅ AutoSave monitor resumed for user {uid}")
                else:
                    logger.warning(f"⚠️ AutoSave resume failed for user {uid}: {err}")
            except Exception as e:
                logger.error(f"Error resuming autosave for user {uid}: {e}")
    except Exception as e:
        logger.error(f"AutoSave resume routine error: {e}")
