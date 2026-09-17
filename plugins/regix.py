import os
import sys 
import math
import time
import random
import asyncio 
import logging
from .utils import STS
from database import db 
from .test import CLIENT , start_clone_bot

def human_delay(base: float) -> float:
    """Add ±30% random jitter to mimic human timing (reference from Fast-Forward-bot)"""
    jitter = base * 0.3
    return max(0.1, base + random.uniform(-jitter, jitter))

from config import Config, temp
from translation import Translation
from pyrogram import Client, filters 
from pyrogram.errors import FloodWait, MessageNotModified, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Translation.TEXT

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    user = message.from_user.id
    temp.CANCEL[user] = False
    frwd_id = message.data.split("_")[2]
    if temp.lock.get(user) and str(temp.lock.get(user))=="True":
      return await message.answer("ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ᴜɴᴛɪʟʟ ᴘʀᴇᴠɪᴏᴜs ᴛᴀsᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ.", show_alert=True)
    sts = STS(frwd_id)
    if not sts.verify():
      await message.answer("ʏᴏᴜ ᴀʀᴇ ᴄʟɪᴄᴋɪɴɢ ᴏɴ ᴍʏ ᴏɴᴇ ᴏғ ᴏʟᴅ ʙᴜᴛᴛᴏɴ.", show_alert=True)
      return await message.message.delete()
    sts.data[sts.id]['user_id'] = user
    temp.PAUSE[user] = False
    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT:
      return await message.answer("ɪɴ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ ᴛᴀsᴋ ɪs ɪɴ ᴘʀᴏɢʀᴇss. ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ᴜɴᴛɪʟʟ ᴘʀᴇᴠɪᴏᴜs ᴛᴀsᴋ ɪs ᴄᴏᴍᴘʟᴇᴛᴇᴅ.", show_alert=True)
    m = await msg_edit(message.message, "<i><b>vᴇʀɪғʏɪɴɢ ʏᴏᴜʀ ᴅᴀᴛᴀ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ.</b></i>")
    _bot, caption, forward_tag, data, protect, button = await sts.get_data(user)
    if not _bot:
      return await msg_edit(m, "<code>ʏᴏᴜ ᴅɪᴅ ɴᴏᴛ ᴀᴅᴅᴇᴅ ᴀɴʏ ʙᴏᴛ ʏᴇᴛ ᴜsᴇ /settings</code>", wait=True)
    try:
      client = await start_clone_bot(CLIENT.client(_bot))
    except Exception as e:  
      return await m.edit(e)
    await msg_edit(m, "<b>ᴘʀᴏᴄᴇssɪɴɢ..</b>")
    try: 
       await client.get_messages(sts.get("FROM"), sts.get("limit"))
    except:
       await msg_edit(m, f"**sᴏᴜʀᴄᴇ ᴄʜᴀᴛ ᴍᴀʏ ʙᴇ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ / ɢʀᴏᴜᴘ. ᴜsᴇ ᴜsᴇʀ ʙᴏᴛ (ᴜsᴇʀ ᴍᴜsᴛ ʙᴇ ᴍᴇᴍʙᴇʀ ᴏᴠᴇʀ ᴛʜᴇʀᴇ) ᴏʀ ɪғ ᴍᴀᴋᴇ ʏᴏᴜʀ ʙᴏᴛ [Bot](t.me/{_bot['username']}) ᴀɴ ᴀᴅᴍɪɴ ᴏᴠᴇʀ ᴛʜᴇʀᴇ**", retry_btn(frwd_id), True)
       return await stop(client, user)
    try:
       k = await client.send_message(i.TO, "Testing")
       await k.delete()
    except:
       await msg_edit(m, f"**ᴘʟᴇᴀsᴇ [ᴜsᴇʀʙᴏᴛ / ʙᴏᴛ](t.me/{_bot['username']}) ᴀᴅᴍɪɴ ɪɴ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ ᴡɪᴛʜ ғᴜʟʟ ᴘᴇʀᴍɪssɪᴏɴ.**", retry_btn(frwd_id), True)
       return await stop(client, user)
    temp.forwardings += 1
    await db.add_frwd(user)
    await send(client, user, "<b>🚥 ғᴏʀᴡᴀʀᴅɪɴɢ sᴛᴀʀᴛᴇᴅ</b>")
    sts.add(time=True)
    user_configs = await db.get_configs(user)
    clean_caption = user_configs.get('clean_caption', False)
    replace_words = user_configs.get('replace_words', {})
    dump_target, dump_enabled = await db.get_admin_dump()
    if not dump_enabled:
       dump_target = None
    elif dump_target:
       try: dump_target = int(dump_target)
       except Exception: pass
    speed_cfg = user_configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
    base_delay = float(speed_cfg.get('delay', 1.0 if _bot['is_bot'] else 5.0))
    jitter_enabled = bool(speed_cfg.get('jitter', True))
    batch_size = int(speed_cfg.get('batch_size', 100 if base_delay <= 1.0 else 20))
    course_items = []
    if Config.LOG_CHANNEL:
       try:
          await send(client, Config.LOG_CHANNEL,
              f"📊 <b>#ForwardTaskStarted</b>\n\n"
              f"👤 <b>User:</b> <code>{user}</code>\n"
              f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
              f"🎯 <b>Target:</b> <code>{i.TO}</code>\n"
              f"📦 <b>Total:</b> <code>{sts.get('limit')}</code>\n"
              f"⚡ <b>Speed Mode:</b> <code>{speed_cfg.get('mode', 'fast')}</code>"
          )
       except Exception:
          pass
    await msg_edit(m, "<code>ᴘʀᴏᴄᴇssɪɴɢ ...</code>") 
    temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user] = locked = True
    if locked:
        try:
          MSG = []
          pling=0
          await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
          print(f"Starting Forwarding Process... From :{sts.get('FROM')} To: {sts.get('TO')} Total: {sts.get('limit')} stats : {sts.get('skip')})")
          async for message in client.iter_messages(
            client,
            chat_id=sts.get('FROM'), 
            limit=int(sts.get('limit')), 
            offset=int(sts.get('skip')) if sts.get('skip') else 0
            ):
                if await is_cancelled(client, user, m, sts):
                   return
                while temp.PAUSE.get(user) is True:
                   if await is_cancelled(client, user, m, sts):
                      return
                   await asyncio.sleep(2)
                if pling %20 == 0: 
                   await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
                pling += 1
                sts.add('fetched')
                if message == "DUPLICATE":
                   sts.add('duplicate')
                   continue 
                elif message == "FILTERED":
                   sts.add('filtered')
                   continue 
                if message.empty or message.service:
                   sts.add('deleted')
                   continue
                if forward_tag:
                   MSG.append(message.id)
                   notcompleted = len(MSG)
                   completed = sts.get('total') - sts.get('fetched')
                   if ( notcompleted >= batch_size 
                        or completed <= batch_size): 
                      await forward(client, MSG, m, sts, protect, dump_target=dump_target)
                      sts.add('total_files', notcompleted)
                      b_sleep = human_delay(base_delay * 2) if jitter_enabled else (base_delay * 2)
                      await asyncio.sleep(max(1.0, b_sleep))
                      MSG = []
                else:
                   lec_idx = len(course_items) + 1
                   new_caption = custom_caption(message, caption, clean_caption=clean_caption, replace_words=replace_words, user_configs=user_configs, lecture_index=lec_idx)
                   details = {"msg_id": message.id, "media": media(message), "caption": new_caption, 'button': button, "protect": protect, "upload_type": user_configs.get('upload_type', 'media')}
                   sent_id = await copy(client, details, m, sts, dump_target=dump_target)
                   sts.add('total_files')
                   if sent_id:
                      media_obj = getattr(message, message.media.value, None) if message.media else None
                      fname = getattr(media_obj, 'file_name', '') if media_obj else ''
                      c_title = fname or (message.caption[:50] if message.caption else f"Lecture {lec_idx:02d}")
                      course_items.append({'num': lec_idx, 'title': c_title, 'msg_id': sent_id})
                   sleep_time = human_delay(base_delay) if jitter_enabled else base_delay
                   await asyncio.sleep(sleep_time) 
        except Exception as e:
            await msg_edit(m, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
            if sts.TO in temp.IS_FRWD_CHAT:
                temp.IS_FRWD_CHAT.remove(sts.TO)
            return await stop(client, user)
        if sts.TO in temp.IS_FRWD_CHAT:
            temp.IS_FRWD_CHAT.remove(sts.TO)
        if Config.LOG_CHANNEL:
           try:
              await send(client, Config.LOG_CHANNEL,
                  f"✅ <b>#ForwardTaskCompleted</b>\n\n"
                  f"👤 <b>User:</b> <code>{user}</code>\n"
                  f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                  f"🎯 <b>Target:</b> <code>{sts.get('TO')}</code>\n"
                  f"📥 <b>Fetched:</b> <code>{sts.get('fetched') or 0}</code>\n"
                  f"⚙️ <b>Forwarded:</b> <code>{sts.get('total_files') or 0}</code>\n"
                  f"♻️ <b>Duplicate:</b> <code>{sts.get('duplicate') or 0}</code>\n"
                  f"🗑️ <b>Deleted:</b> <code>{sts.get('deleted') or 0}</code>"
              )
           except Exception:
              pass

        # ── Course Seller Mode: Auto Course List Maker ────────
        if (user_configs.get('course_seller_mode') or user_configs.get('auto_course_list')) and course_items:
           try:
              await send_course_index_list(client, user, sts, course_items)
           except Exception as err:
              logger.warning(f"Error sending course list: {err}")

        await send(client, user, "<b>🎉 ғᴏʀᴡᴀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>")
        await edit(m, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "ᴄᴏᴍᴘʟᴇᴛᴇᴅ", sts) 
        await stop(client, user)

async def copy(bot, msg, m, sts, dump_target=None):
   try:                                  
     sent = None
     if msg.get("media") and msg.get("caption"):
        sent = await bot.send_cached_media(
              chat_id=sts.get('TO'),
              file_id=msg.get("media"),
              caption=msg.get("caption"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
        if dump_target:
           try:
              await bot.send_cached_media(
                    chat_id=dump_target,
                    file_id=msg.get("media"),
                    caption=msg.get("caption"))
           except Exception:
              pass
     elif msg.get("caption") and not msg.get("media"):
        sent = await bot.send_message(
              chat_id=sts.get('TO'),
              text=msg.get("caption"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
        if dump_target:
           try:
              await bot.send_message(
                    chat_id=dump_target,
                    text=msg.get("caption"))
           except Exception:
              pass
     else:
        sent = await bot.copy_message(
              chat_id=sts.get('TO'),
              from_chat_id=sts.get('FROM'),    
              caption=msg.get("caption"),
              message_id=msg.get("msg_id"),
              reply_markup=msg.get('button'),
              protect_content=msg.get("protect"))
        if dump_target:
           try:
              await bot.copy_message(
                    chat_id=dump_target,
                    from_chat_id=sts.get('FROM'),
                    caption=msg.get("caption"),
                    message_id=msg.get("msg_id"))
           except Exception:
              pass
     return getattr(sent, 'id', None)
   except FloodWait as e:
     await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
     await asyncio.sleep(e.value + 1)
     await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
     return await copy(bot, msg, m, sts, dump_target=dump_target)
   except Exception as e:
     print(e)
     sts.add('deleted')
     return None

async def send_course_index_list(client, user, sts, course_items):
   to_chat = sts.get('TO')
   from_title = str(sts.get('FROM'))
   clean_chat = str(to_chat).replace("-100", "").replace("-", "")

   header = (
      "📚 <b><u>ᴄᴏᴜʀsᴇ ʟᴇᴄᴛᴜʀᴇs ɪɴᴅᴇx / sʏʟʟᴀʙᴜs</u></b>\n"
      "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
      f"🎯 <b>Source:</b> <code>{from_title}</code>\n"
      f"📦 <b>Total Lectures:</b> <code>{len(course_items)}</code>\n\n"
   )

   chunk_size = 25
   for chunk_idx in range(0, len(course_items), chunk_size):
      chunk = course_items[chunk_idx:chunk_idx + chunk_size]
      lines = []
      for item in chunk:
         num_str = f"{item['num']:02d}"
         title = str(item['title']).replace("<", "&lt;").replace(">", "&gt;")
         if item.get('msg_id'):
            link = f"https://t.me/c/{clean_chat}/{item['msg_id']}"
            lines.append(f"<b>[{num_str}]</b> <a href='{link}'>{title}</a>")
         else:
            lines.append(f"<b>[{num_str}]</b> {title}")

      footer = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚡️ <i>Generated by Skinet Verse (Course Seller Mode)</i>"
      full_text = header + "\n".join(lines) + footer

      try:
         sent_idx = await client.send_message(to_chat, full_text, disable_web_page_preview=True)
         if chunk_idx == 0:
            try:
               await sent_idx.pin(disable_notification=True)
            except Exception:
               pass
      except Exception:
         pass

      try:
         await client.send_message(user, full_text, disable_web_page_preview=True)
      except Exception:
         pass


async def forward(bot, msg, m, sts, protect, dump_target=None):
   try:                             
     await bot.forward_messages(
           chat_id=sts.get('TO'),
           from_chat_id=sts.get('FROM'), 
           protect_content=protect,
           message_ids=msg)
     if dump_target:
        try:
           await bot.forward_messages(
                 chat_id=dump_target,
                 from_chat_id=sts.get('FROM'),
                 message_ids=msg)
        except Exception:
           pass
   except FloodWait as e:
     await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
     await asyncio.sleep(e.value + 1)
     await edit(m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)
     await forward(bot, msg, m, sts, protect, dump_target=dump_target)

PROGRESS = """
📈 ᴘᴇʀᴄᴇɴᴛᴀɢᴇ : {0} %

⭕ ғᴇᴛᴄʜᴇᴅ : {1}

⚙️ ғᴏʀᴡᴀʀᴅᴇᴅ : {2}

🗞️ ʀᴇᴍᴀɴɪɴɢ : {3}

♻️ sᴛᴀᴛᴜs : {4}

⏳️ ᴇᴛᴀ : {5}
"""

async def msg_edit(msg, text, button=None, wait=None):
    try:
        return await msg.edit(text, reply_markup=button)
    except MessageNotModified:
        pass 
    except FloodWait as e:
        if wait:
           await asyncio.sleep(e.value)
           return await msg_edit(msg, text, button, wait)

async def edit(msg, title, status, sts):
   i = sts.get(full=True)
   owner = getattr(i, 'user_id', None) or (sts.verify().get('user_id') if isinstance(sts.verify(), dict) else None)
   is_paused = temp.PAUSE.get(owner, False)
   if is_paused:
       status = '⏸️ ᴘᴀᴜsᴇᴅ'
   elif status == 10:
       status = 'ғᴏʀᴡᴀʀᴅɪɴɢ'
   elif str(status).isnumeric():
       status = f"sʟᴇᴇᴘɪɴɢ {status} s"

   percentage = "{:.0f}".format(float(i.fetched)*100/float(i.total))

   now = time.time()
   diff = int(now - i.start)
   speed = sts.divide(i.fetched, diff)
   elapsed_time = round(diff) * 1000
   time_to_completion = round(sts.divide(i.total - i.fetched, int(speed))) * 1000
   estimated_total_time = elapsed_time + time_to_completion  
   
   progress = "▰{0}{1}".format(
       ''.join(["▰" for _ in range(math.floor(int(percentage) / 10))]),
       ''.join(["▱" for _ in range(10 - math.floor(int(percentage) / 10))]))
   button = [[InlineKeyboardButton(progress, callback_data=f'fwrdstatus#{status}#{estimated_total_time}#{percentage}#{i.id}')]]
   estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
   estimated_total_time = estimated_total_time if estimated_total_time != '' else '0 s'

   text = TEXT.format(i.total, i.fetched, i.total_files, i.duplicate, i.deleted, i.skip, i.filtered, status, percentage, title)
   if status in ["ᴄᴀɴᴄᴇʟʟᴇᴅ", "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"]:
      button.append([InlineKeyboardButton('• ᴄʟᴏsᴇ', callback_data='close_btn')])
   else:
      pause_btn = InlineKeyboardButton('▶️ ʀᴇsᴜᴍᴇ', callback_data=f'resume_frwd#{i.id}') if is_paused else InlineKeyboardButton('⏸️ ᴘᴀᴜsᴇ', callback_data=f'pause_frwd#{i.id}')
      button.append([
         pause_btn,
         InlineKeyboardButton('🛑 ᴄᴀɴᴄᴇʟ', callback_data='terminate_frwd')
      ])
   await msg_edit(msg, text, InlineKeyboardMarkup(button))

async def is_cancelled(client, user, msg, sts):
   if temp.CANCEL.get(user) == True:
      if sts.TO in temp.IS_FRWD_CHAT:
          temp.IS_FRWD_CHAT.remove(sts.TO)
      if Config.LOG_CHANNEL:
         try:
            await send(client, Config.LOG_CHANNEL,
                f"🛑 <b>#ForwardTaskCancelled</b>\n\n"
                f"👤 <b>User:</b> <code>{user}</code>\n"
                f"📡 <b>Source:</b> <code>{sts.get('FROM')}</code>\n"
                f"🎯 <b>Target:</b> <code>{sts.get('TO')}</code>\n"
                f"⚙️ <b>Forwarded:</b> <code>{sts.get('total_files') or 0}</code>"
            )
         except Exception:
            pass
      await edit(msg, "ᴄᴀɴᴄᴇʟʟᴇᴅ", "ᴄᴏᴍᴘʟᴇᴛᴇᴅ", sts)
      await send(client, user, "<b>❌ ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>")
      await stop(client, user)
      return True 
   return False 

async def stop(client, user):
   try:
     await client.stop()
   except:
     pass 
   await db.rmve_frwd(user)
   temp.forwardings -= 1
   temp.lock[user] = False 
   temp.PAUSE[user] = False

async def send(bot, user, text):
   try:
      await bot.send_message(user, text=text)
   except:
      pass 

def clean_caption_advanced(text: str, user_configs: dict = None, lecture_index: int = None, file_name: str = "") -> str:
  if not text:
    text = ""
  user_configs = user_configs or {}
  is_seller = bool(user_configs.get('course_seller_mode', False))
  rem_user = is_seller or bool(user_configs.get('username_remover', False))
  rep_user = user_configs.get('username_replacer')
  rem_link = is_seller or bool(user_configs.get('link_remover', False))
  rep_link = user_configs.get('link_replacer')
  rem_hid = is_seller or bool(user_configs.get('hidden_link_remover', False))
  clean_cap = is_seller or bool(user_configs.get('clean_caption', False))
  replace_words = user_configs.get('replace_words', {})
  auto_num = is_seller or bool(user_configs.get('auto_numbering', False))

  # 1. Hidden link remover & replacer (HTML: <a href="url">text</a>)
  if rem_hid or rem_link:
    if rep_link:
      text = re.sub(r'<a\s+href=["\'][^"\']+["\']>(.*?)</a>', rf'<a href="{rep_link}">\1</a>', text, flags=re.DOTALL)
    else:
      text = re.sub(r'<a\s+href=["\'][^"\']+["\']>(.*?)</a>', r'\1', text, flags=re.DOTALL)

  # 2. Hidden link remover & replacer (Markdown: [text](url))
  if rem_hid or rem_link:
    if rep_link:
      text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', rf'[\1]({rep_link})', text)
    else:
      text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', text)

  # 3. Direct links remover & replacer
  if rem_link or clean_cap:
    if rep_link:
      text = re.sub(r'https?://(?:t\.me|telegram\.me|telegram\.dog)/\S+', rep_link, text)
      text = re.sub(r'https?://\S+|www\.\S+', rep_link, text)
    else:
      text = re.sub(r'https?://(?:t\.me|telegram\.me|telegram\.dog)/\S+', '', text)
      text = re.sub(r'https?://\S+|www\.\S+', '', text)

  # 4. Username remover & replacer
  if rem_user or clean_cap:
    if rep_user:
      text = re.sub(r'@\w+', rep_user, text)
    else:
      text = re.sub(r'@\w+', '', text)

  # 5. Word replacements
  if replace_words:
    for old, new in replace_words.items():
      if old:
        text = text.replace(old, new)

  # 6. Normalize whitespace
  text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text).strip()

  # 7. Lecture numbering prefix
  if auto_num and lecture_index is not None:
    prefix = f"<b>[{lecture_index:02d}]</b> "
    if not text.startswith("[") and not text.startswith("<b>["):
      text = prefix + (text if text else (file_name or f"Lecture {lecture_index:02d}"))

  return text

def clean_caption_text(text: str) -> str:
  return clean_caption_advanced(text, {'clean_caption': True})

def apply_word_replacements(text: str, replace_words: dict) -> str:
  if not text or not replace_words:
    return text
  for old, new in replace_words.items():
    text = text.replace(old, new)
  return text

def custom_caption(msg, caption, clean_caption=False, replace_words=None, user_configs=None, lecture_index=None):
  user_configs = dict(user_configs) if user_configs else {}
  if clean_caption:
    user_configs['clean_caption'] = True
  if replace_words:
    user_configs['replace_words'] = replace_words

  file_name = ''
  file_size = 0
  fcaption = ''

  if msg.media:
    media_val = getattr(msg.media, 'value', str(msg.media))
    media_obj = getattr(msg, media_val, None)
    if media_obj:
      file_name = getattr(media_obj, 'file_name', '') or ''
      file_size = getattr(media_obj, 'file_size', 0) or 0
    if msg.caption:
      fcaption = msg.caption.html if hasattr(msg.caption, 'html') else str(msg.caption)
  elif msg.text:
    fcaption = msg.text.html if hasattr(msg.text, 'html') else str(msg.text)

  cleaned = clean_caption_advanced(fcaption, user_configs, lecture_index=lecture_index, file_name=file_name)

  if caption:
    try:
      res = caption.format(
        filename=file_name,
        size=get_size(file_size),
        caption=cleaned or ""
      )
      return clean_caption_advanced(res, user_configs, lecture_index=None, file_name=file_name)
    except Exception:
      return cleaned
  return cleaned if cleaned else None
  return None

def get_size(size):
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units):
     i += 1
     size /= 1024.0
  return "%.2f %s" % (size, units[i]) 

def media(msg):
  if msg.media:
     media = getattr(msg, msg.media.value, None)
     if media:
        return getattr(media, 'file_id', None)
  return None 

def TimeFormatter(milliseconds: int) -> str:
    try:
        ms = int(float(milliseconds))
    except Exception:
        ms = 0
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(ms) + "ms, ") if ms else "")
    return tmp[:-2] if tmp else "0s"

def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ ʀᴇᴛʀʏ ♻️', f"start_public_{id}")]])

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id 
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True 
    temp.PAUSE[user_id] = False
    await m.answer("ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ !", show_alert=True)

@Client.on_callback_query(filters.regex(r'^pause_frwd'))
async def pause_callback(bot, query):
    user_id = query.from_user.id
    temp.PAUSE[user_id] = True
    await query.answer("⏸️ Forwarding Paused!", show_alert=True)
    frwd_id = query.data.split("#")[1]
    sts = STS(frwd_id)
    if sts.verify():
        await edit(query.message, 'ᴘᴀᴜsᴇᴅ', '⏸️ ᴘᴀᴜsᴇᴅ', sts)

@Client.on_callback_query(filters.regex(r'^resume_frwd'))
async def resume_callback(bot, query):
    user_id = query.from_user.id
    temp.PAUSE[user_id] = False
    await query.answer("▶️ Forwarding Resumed!", show_alert=True)
    frwd_id = query.data.split("#")[1]
    sts = STS(frwd_id)
    if sts.verify():
        await edit(query.message, 'ᴘʀᴏɢʀᴇssɪɴɢ', 10, sts)

@Client.on_callback_query(filters.regex(r'^fwrdstatus'))
async def status_msg(bot, msg):
    _, status, est_time, percentage, frwd_id = msg.data.split("#")
    sts = STS(frwd_id)
    if not sts.verify():
       fetched = forwarded = remaining = skipped = 0
    else:
       total = sts.get('total') or 0
       skipped = sts.get('skip') or 0
       fetched, forwarded = sts.get('fetched') or 0, sts.get('total_files') or 0
       remaining = max(0, total - forwarded - skipped)
    est_time = TimeFormatter(milliseconds=est_time)
    est_time = est_time if (est_time != '' or status not in ['completed', 'cancelled']) else '0 s'
    return await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining, status, est_time), show_alert=True)

@Client.on_message(filters.command("stop"))
async def stop_forwarding(bot, message):
    user_id = message.from_user.id
    if temp.lock.get(user_id):
        temp.lock[user_id] = False
        temp.CANCEL[user_id] = True
        temp.PAUSE[user_id] = False
        await message.reply("🛑 ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ !", quote=True)
    else:
        await message.reply("❌ ɴᴏ ᴏɴɢᴏɪɴɢ ғᴏʀᴡᴀʀᴅɪɴɢ ᴘʀᴏᴄᴇss ᴛᴏ ᴄᴀɴᴄᴇʟ.", quote=True)

@Client.on_message(filters.command("pause"))
async def pause_command(bot, message):
    user_id = message.from_user.id
    if temp.lock.get(user_id):
        temp.PAUSE[user_id] = True
        await message.reply("⏸️ **ғᴏʀᴡᴀʀᴅɪɴɢ ᴘᴀᴜsᴇᴅ!**\nUse /resume to continue or click the Resume button.", quote=True)
    else:
        await message.reply("❌ **No ongoing forwarding process to pause.**", quote=True)

@Client.on_message(filters.command("resume"))
async def resume_command(bot, message):
    user_id = message.from_user.id
    if temp.PAUSE.get(user_id):
        temp.PAUSE[user_id] = False
        await message.reply("▶️ **ғᴏʀᴡᴀʀᴅɪɴɢ ʀᴇsᴜᴍᴇᴅ!**", quote=True)
    else:
        await message.reply("❌ **Process is not paused or not running.**", quote=True)

@Client.on_callback_query(filters.regex(r'^close_btn$'))
async def close(bot, update):
    await update.answer()
    await update.message.delete() 