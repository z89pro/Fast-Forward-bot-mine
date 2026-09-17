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

#===================Run Function===================#

@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if not _bot:
      return await message.reply("<code>__**You didn't add any bot. Please add a bot using /settings !**__</code>")
    channels = await db.get_user_channels(user_id)
    if not channels:
       return await message.reply_text("Please set a target channel in /settings before forwarding")
    
    # Direct range forwarding: /fwd <start_link> <end_link>
    link_regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
    if len(message.command) >= 3:
       start_match = link_regex.match(message.command[1].replace("?single", ""))
       end_match = link_regex.match(message.command[2].replace("?single", ""))
       if start_match and end_match:
          c1 = start_match.group(4)
          c2 = end_match.group(4)
          if c1 != c2:
             return await message.reply("**Both links must be from the same channel!**")
          m1 = int(start_match.group(5))
          m2 = int(end_match.group(5))
          chat_id = int(("-100" + c1)) if c1.isnumeric() else c1
          skip_count = max(0, min(m1, m2) - 1)
          last_msg_id = max(m1, m2)
          toid = channels[0]['chat_id']
          to_title = channels[0]['title']
          try:
              title = (await bot.get_chat(chat_id)).title
          except Exception:
              title = "Source"
          forward_id = f"{user_id}-{message.id}"
          buttons = [[
              InlineKeyboardButton('Yes', callback_data=f"start_public_{forward_id}"),
              InlineKeyboardButton('No', callback_data="close_btn")
          ]]
          reply_markup = InlineKeyboardMarkup(buttons)
          await message.reply_text(
              text=f"**⚡ ᴅɪʀᴇᴄᴛ ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ**\n\n" + Translation.DOUBLE_CHECK.format(botname=_bot['name'], botuname=_bot['username'], from_chat=title, to_chat=to_title, skip=skip_count),
              disable_web_page_preview=True,
              reply_markup=reply_markup
          )
          STS(forward_id).store(chat_id, toid, skip_count, int(last_msg_id))
          return

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
    if fromid.text and not fromid.forward_date:
        match = link_regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int(("-100" + chat_id))
    elif fromid.forward_from_chat and fromid.forward_from_chat.type in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP]:
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if last_msg_id is None:
           return await message.reply_text("**This may be a forwarded message from a group sent by anonymous admin. Instead of this, please send the last message link.**")
    else:
        await message.reply_text("**Invalid source message! Please forward a message from a channel or send a message link.**")
        return 
    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "private" if fromid.text else (fromid.forward_from_chat.title if fromid.forward_from_chat else "Source")
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')
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
    buttons = [[
        InlineKeyboardButton('Yes', callback_data=f"start_public_{forward_id}"),
        InlineKeyboardButton('No', callback_data="close_btn")
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        text=Translation.DOUBLE_CHECK.format(botname=_bot['name'], botuname=_bot['username'], from_chat=title, to_chat=to_title, skip=skip_count),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, skip_count, int(last_msg_id)) 