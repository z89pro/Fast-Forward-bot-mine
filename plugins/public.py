import re
import asyncio 
from .utils import STS
from database import db
from config import temp 
from translation import Translation
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from buttons import btn, row, markup, colored_markup

#===================Run Function===================#

@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id
    from plugins.verify import is_user_verified, send_verify_prompt
    if not await is_user_verified(user_id):
        return await send_verify_prompt(bot, message, user_id)
    _bot = await db.get_bot(user_id)
    if not _bot:
      return await message.reply("<code>__**You didn't add any bot. Please add a bot using /settings !**__</code>")
    channels = await db.get_user_channels(user_id)
    if not channels:
       return await message.reply_text("Please set a target channel in /settings before forwarding")
    
    from plugins.range_parser import parse_multi_ranges, format_ranges_summary, calculate_total_messages

    # Direct multi-range or link forwarding: /fwd <link/ranges...>
    raw_args = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    if raw_args:
        try:
            parsed_chat, parsed_ranges = parse_multi_ranges(raw_args)
            if parsed_chat and parsed_ranges:
                toid = channels[0]['chat_id']
                to_title = channels[0]['title']
                try:
                    title = (await bot.get_chat(parsed_chat)).title
                except Exception:
                    title = "Source"
                
                total_msgs = calculate_total_messages(parsed_ranges)
                summary_str = format_ranges_summary(parsed_ranges)
                forward_id = f"{user_id}-{message.id}"
                reply_markup = markup(
                    row(
                        btn('✅ ʏᴇs, sᴛᴀʀᴛ', f"start_public_{forward_id}", "green"),
                        btn('❌ ɴᴏ, ᴄᴀɴᴄᴇʟ', "close_btn", "red")
                    )
                )
                await message.reply_text(
                    text=f"⚡ <b><u>ᴍᴜʟᴛɪ-ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ</u></b>\n\n"
                         f"🤖 <b>ʙᴏᴛ:</b> <code>{_bot['name']}</code> (@{_bot['username']})\n"
                         f"📡 <b>ғʀᴏᴍ:</b> <code>{title}</code>\n"
                         f"🎯 <b>ᴛᴏ:</b> <code>{to_title}</code>\n"
                         f"📑 <b>ʀᴀɴɢᴇs:</b> <code>{summary_str}</code>\n"
                         f"📦 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:</b> <code>{total_msgs}</code>\n\n"
                         f"<i>ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ ᴛʜᴇsᴇ ʀᴀɴɢᴇs?</i>",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
                first_start = parsed_ranges[0][0]
                last_end = parsed_ranges[-1][1]
                STS(forward_id).store(parsed_chat, toid, skip=first_start, limit=last_end, ranges=parsed_ranges)
                return
        except Exception as parse_err:
            return await message.reply_text(f"⚠️ <b>ᴇʀʀᴏʀ ɪɴ ʀᴀɴɢᴇ ᴘᴀʀsɪɴɢ:</b> {parse_err}")

    if len(channels) > 1:
       for channel in channels:
          buttons.append([KeyboardButton(f"{channel['title']}")])
          btn_data[channel['title']] = channel['chat_id']
       buttons.append([KeyboardButton("cancel")]) 
       _toid = await bot.ask(message.chat.id, Translation.TO_MSG.format(_bot['name'], _bot['username']), reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))
       if _toid.text and _toid.text.startswith(('/', 'cancel')):
          return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
       to_title = _toid.text
       toid = btn_data.get(to_title)
       if not toid:
          return await message.reply_text("Wrong channel chosen!", reply_markup=ReplyKeyboardRemove())
    else:
       toid = channels[0]['chat_id']
       to_title = channels[0]['title']
    fromid = await bot.ask(message.chat.id, Translation.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return 

    detected_ranges = None

    if fromid.text and not fromid.forward_date and not getattr(fromid, "forward_origin", None):
        # Check if user sent range links or multi-ranges in the prompt
        try:
            p_chat, p_ranges = parse_multi_ranges(fromid.text)
            if p_chat and p_ranges and (len(p_ranges) > 1 or p_ranges[0][0] != p_ranges[0][1]):
                chat_id = p_chat
                detected_ranges = p_ranges
                last_msg_id = p_ranges[-1][1]
                skip_count = p_ranges[0][0]
            else:
                from plugins.forward_parser import resolve_channel_input
                res = await resolve_channel_input(fromid, bot)
                if not res.get("chat_id") or not res.get("last_msg_id"):
                    return await message.reply('Invalid link specified.')
                chat_id = res["chat_id"]
                last_msg_id = res["last_msg_id"]
        except Exception:
            from plugins.forward_parser import resolve_channel_input
            res = await resolve_channel_input(fromid, bot)
            if not res.get("chat_id") or not res.get("last_msg_id"):
                return await message.reply('Invalid link specified.')
            chat_id = res["chat_id"]
            last_msg_id = res["last_msg_id"]
    else:
        from plugins.forward_parser import resolve_channel_input
        res = await resolve_channel_input(fromid, bot)
        if not res.get("chat_id"):
            return await message.reply_text(f"❌ **Invalid source message!** {res.get('error', 'Please forward a message from a channel or send a message link.')}")
        chat_id = res["chat_id"]
        last_msg_id = res.get("last_msg_id")
        if last_msg_id is None:
            return await message.reply_text("**This forwarded message has no message ID. Please send the direct message link instead.**")

    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = res.get("chat_title") if res.get("chat_title") else "Source"
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        title = res.get("chat_title") or "Source"

    if detected_ranges:
        total_msgs = calculate_total_messages(detected_ranges)
        summary_str = format_ranges_summary(detected_ranges)
        forward_id = f"{user_id}-{fromid.id}"
        reply_markup = markup(
            row(
                btn('✅ ʏᴇs, sᴛᴀʀᴛ', f"start_public_{forward_id}", "green"),
                btn('❌ ɴᴏ, ᴄᴀɴᴄᴇʟ', "close_btn", "red")
            )
        )
        await message.reply_text(
            text=f"⚡ <b><u>ᴍᴜʟᴛɪ-ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ</u></b>\n\n"
                 f"🤖 <b>ʙᴏᴛ:</b> <code>{_bot['name']}</code> (@{_bot['username']})\n"
                 f"📡 <b>ғʀᴏᴍ:</b> <code>{title}</code>\n"
                 f"🎯 <b>ᴛᴏ:</b> <code>{to_title}</code>\n"
                 f"📑 <b>ʀᴀɴɢᴇs:</b> <code>{summary_str}</code>\n"
                 f"📦 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:</b> <code>{total_msgs}</code>\n\n"
                 f"<i>ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴛᴀʀᴛ ғᴏʀᴡᴀʀᴅɪɴɢ ᴛʜᴇsᴇ ʀᴀɴɢᴇs?</i>",
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        STS(forward_id).store(chat_id, toid, skip=skip_count, limit=last_msg_id, ranges=detected_ranges)
        return

    skipno = await bot.ask(message.chat.id, Translation.SKIP_MSG)
    if not skipno.text or skipno.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return
    skip_val = skipno.text.strip()
    if not skip_val.isdigit():
        await message.reply("Invalid number! Please enter digits only.")
        return
    skip_count = int(skip_val)
    forward_id = f"{user_id}-{skipno.id}"
    reply_markup = markup(
        row(
            btn('✅ ʏᴇs, sᴛᴀʀᴛ', f"start_public_{forward_id}", "green"),
            btn('❌ ɴᴏ, ᴄᴀɴᴄᴇʟ', "close_btn", "red")
        )
    )
    await message.reply_text(
        text=Translation.DOUBLE_CHECK.format(botname=_bot['name'], botuname=_bot['username'], from_chat=title, to_chat=to_title, skip=skip_count),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, skip_count, int(last_msg_id)) 