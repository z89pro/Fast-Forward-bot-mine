import os
import re 
import sys
import typing
import asyncio 
import logging 
from database import db 
from config import Config, temp
from pyrogram import Client, filters, types
from pyrogram.raw.all import layer
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.errors import (
    FloodWait,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    ListenerTimeout,
    PhoneNumberBanned,
    PhoneCodeEmpty,
    PhoneNumberUnoccupied,
    BadRequest
)
from config import Config
from translation import Translation
from typing import Union, Optional, AsyncGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
BOT_TOKEN_TEXT = "<b>1) create a bot using @BotFather\n2) Then you will get a message with bot token\n3) Forward that message to me</b>"
SESSION_STRING_SIZE = 351

async def start_clone_bot(FwdBot, data=None):
   await FwdBot.start()
   #
   async def iter_messages(
      self, 
      chat_id: Union[int, str], 
      limit: int, 
      offset: int = 0,
      search: str = None,
      filter: "types.TypeMessagesFilter" = None,
      ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1
   #
   FwdBot.iter_messages = iter_messages
   return FwdBot

class CLIENT: 
  def __init__(self):
     self.api_id = int(Config.API_ID) if (Config.API_ID and str(Config.API_ID).isdigit()) else Config.API_ID
     self.api_hash = Config.API_HASH
    
  def client(self, data, user=None):
     if user == None and data.get('is_bot') == False:
        return Client(f"USERBOT_{data.get('user_id', 'client')}", self.api_id, self.api_hash, session_string=data.get('session'), in_memory=True)
     elif user == True:
        return Client("USERBOT", self.api_id, self.api_hash, session_string=data, in_memory=True)
     elif user != False:
        data = data.get('token')
     return Client("BOT", self.api_id, self.api_hash, bot_token=data, in_memory=True)

  async def add_bot(self, bot, message):
     user_id = int(message.from_user.id)
     try:
        msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT, timeout=300)
     except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
        await bot.send_message(user_id, "Time limit reached (5 minutes).\nPlease start again.")
        return None
     if not msg or not msg.text or msg.text=='/cancel':
        await bot.send_message(user_id, '<b>process cancelled !</b>')
        return None
     elif not msg.forward_date:
        await bot.send_message(user_id, "<b>This is not a forward message</b>")
        return None
     elif not msg.forward_from or str(msg.forward_from.id) != "93372553":
        await bot.send_message(user_id, "<b>This message was not forward from bot father</b>")
        return None
     bot_token = re.findall(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', msg.text, re.IGNORECASE)
     bot_token = bot_token[0] if bot_token else None
     if not bot_token:
        await bot.send_message(user_id, "<b>There is no bot token in that message</b>")
        return None
     try:
        _client = await start_clone_bot(self.client(bot_token, False), True)
     except Exception as e:
        await bot.send_message(user_id, f"<b>BOT ERROR:</b> `{e}`")
        return None
     _bot = _client.me
     details = {
       'id': _bot.id,
       'is_bot': True,
       'user_id': user_id,
       'name': _bot.first_name,
       'token': bot_token,
       'username': _bot.username 
     }
     await db.add_bot(details)
     return True

  async def add_login(self, bot, message):
    user_id = int(message.from_user.id)
    api_id = self.api_id or Config.API_ID
    api_hash = self.api_hash or Config.API_HASH
    disclaimer_text = "<b><blockquote>**<u>⚠️ Warning ⚠️</u>**:\n\n If you already have a session string, please use the add user bot. Otherwise, you can use login.</blockquote></b>"
    await bot.send_message(user_id, text=disclaimer_text)

    client = Client(name=f":memory:{user_id}", api_id=api_id, api_hash=api_hash, in_memory=True)
    try:
        await client.connect()
    except Exception as e:
        await bot.send_message(user_id, f"<b>Failed to connect:</b> `{e}`")
        return None

    try:
        # Step 1: Phone number (up to 3 attempts)
        phone_number = None
        code = None
        max_phone_attempts = 3

        for p_attempt in range(1, max_phone_attempts + 1):
            p_attempts_left = max_phone_attempts - p_attempt
            if p_attempt == 1:
                t = (
                    "➫ ᴘʟᴇᴀsᴇ sᴇɴᴅ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ ғᴏʀ ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ sᴇssɪᴏɴ\n"
                    "➫ ᴇxᴀᴍᴘʟᴇ: +910000000000\n"
                    "/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜɪs ᴘʀᴏᴄᴇss"
                )
            else:
                t = (
                    f"➫ Please enter your phone number with country code.\n"
                    f"⚠️ You have {p_attempts_left + 1} attempt(s) left.\n"
                    f"/cancel - To cancel"
                )

            try:
                phone_number_msg = await bot.ask(user_id, t, filters=filters.text, timeout=300)
            except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
                await bot.send_message(user_id, "Time limit reached (5 minutes).\n\nPlease start generating your session again.")
                return None

            if not phone_number_msg or not phone_number_msg.text or phone_number_msg.text.startswith('/'):
                await bot.send_message(user_id, "<b>Process cancelled!</b>")
                return None

            raw_phone = re.sub(r'[\s\-]', '', phone_number_msg.text)
            if not (raw_phone.startswith('+') or raw_phone.isdigit()):
                if p_attempts_left > 0:
                    await bot.send_message(user_id, f"<b>Invalid phone number format!</b> Please include country code (e.g. +910000000000).\nAttempts left: {p_attempts_left}")
                    continue
                else:
                    await bot.send_message(user_id, "<b>Invalid phone number format!</b> Maximum attempts reached.")
                    return None

            await bot.send_message(user_id, "ᴛʀʏɪɴɢ ᴛᴏ sᴇɴᴅ ᴏᴛᴩ ᴀᴛ ᴛʜᴇ ɢɪᴠᴇɴ ɴᴜᴍʙᴇʀ...")
            try:
                code = await client.send_code(raw_phone)
                phone_number = raw_phone
                break
            except PhoneNumberInvalid:
                if p_attempts_left > 0:
                    await bot.send_message(user_id, f"The phone number you've sent doesn't belong to any Telegram account.\n⚠️ You have {p_attempts_left} attempt(s) left.")
                    continue
                else:
                    await bot.send_message(user_id, "The phone number you've sent doesn't belong to any Telegram account.\nMaximum attempts reached.")
                    return None
            except PhoneNumberBanned:
                await bot.send_message(user_id, "This phone number is banned on Telegram.")
                return None
            except FloodWait as e:
                await bot.send_message(user_id, f"FloodWait: Please wait {e.value} seconds before trying again.")
                return None
            except Exception as e:
                await bot.send_message(user_id, f"<b>Error sending OTP:</b> `{e}`")
                return None

        if not code or not phone_number:
            return None

        # Step 2: OTP verification (up to 3 attempts)
        max_otp_attempts = 3
        signed_in = False
        needs_2fa = False

        for otp_attempt in range(1, max_otp_attempts + 1):
            otp_attempts_left = max_otp_attempts - otp_attempt
            if otp_attempt == 1:
                otp_prompt = (
                    "Please send the OTP that you've received from Telegram on your account.\n"
                    "➫ If OTP is 12345, you can send it as 1 2 3 4 5 or 12345.\n"
                    "/cancel - To cancel."
                )
            else:
                otp_prompt = (
                    f"Please enter the correct OTP received on your Telegram account.\n"
                    f"⚠️ Attempt {otp_attempt}/{max_otp_attempts} ({otp_attempts_left + 1} attempts left).\n"
                    f"/cancel - To cancel."
                )

            try:
                phone_code_msg = await bot.ask(
                    user_id,
                    otp_prompt,
                    filters=filters.text,
                    timeout=600
                )
            except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
                await bot.send_message(user_id, "Time limit reached of 10 minutes.\n\nPlease start generating your session again.")
                return None

            if not phone_code_msg or not phone_code_msg.text or phone_code_msg.text.startswith('/'):
                await bot.send_message(user_id, "<b>Process cancelled!</b>")
                return None

            phone_code = phone_code_msg.text.replace(" ", "").replace("-", "").strip()

            try:
                await client.sign_in(phone_number, code.phone_code_hash, phone_code)
                signed_in = True
                break
            except (PhoneCodeInvalid, PhoneCodeEmpty):
                if otp_attempts_left > 0:
                    await bot.send_message(
                        user_id, 
                        f"❌ The OTP you've sent is wrong.\n⚠️ You have {otp_attempts_left} attempt(s) left."
                    )
                    continue
                else:
                    await bot.send_message(
                        user_id, 
                        "❌ The OTP you've sent is wrong.\nMaximum 3 attempts reached. Please start again."
                    )
                    return None
            except PhoneCodeExpired:
                await bot.send_message(user_id, "The OTP you've sent is expired.\n\nPlease start generating your session again.")
                return None
            except PhoneNumberUnoccupied:
                await bot.send_message(user_id, "This phone number is not registered on Telegram. Please register it first.")
                return None
            except SessionPasswordNeeded:
                needs_2fa = True
                break
            except FloodWait as e:
                await bot.send_message(user_id, f"FloodWait: Please wait {e.value} seconds before trying again.")
                return None
            except Exception as e:
                await bot.send_message(user_id, f"<b>Sign in error:</b> `{e}`")
                return None

        if not signed_in and not needs_2fa:
            return None

        # Step 3: Two-Step Verification Password (up to 3 attempts)
        if needs_2fa:
            max_pwd_attempts = 3
            pwd_verified = False

            for pwd_attempt in range(1, max_pwd_attempts + 1):
                pwd_attempts_left = max_pwd_attempts - pwd_attempt
                if pwd_attempt == 1:
                    pwd_prompt = (
                        "Please enter your two-step verification password to continue.\n"
                        "/cancel - To cancel."
                    )
                else:
                    pwd_prompt = (
                        f"Please enter your two-step verification password.\n"
                        f"⚠️ Attempt {pwd_attempt}/{max_pwd_attempts} ({pwd_attempts_left + 1} attempts left).\n"
                        f"/cancel - To cancel."
                    )

                try:
                    two_step_msg = await bot.ask(
                        user_id,
                        pwd_prompt,
                        filters=filters.text,
                        timeout=300
                    )
                except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
                    await bot.send_message(user_id, "Time limit reached of 5 minutes.\n\nPlease start generating your session again.")
                    return None

                if not two_step_msg or not two_step_msg.text or two_step_msg.text.startswith('/'):
                    await bot.send_message(user_id, "<b>Process cancelled!</b>")
                    return None

                password = two_step_msg.text.strip()
                try:
                    await client.check_password(password=password)
                    pwd_verified = True
                    break
                except PasswordHashInvalid:
                    if pwd_attempts_left > 0:
                        await bot.send_message(
                            user_id, 
                            f"❌ The password you've sent is wrong.\n⚠️ You have {pwd_attempts_left} attempt(s) left."
                        )
                        continue
                    else:
                        await bot.send_message(
                            user_id, 
                            "❌ The password you've sent is wrong.\nMaximum 3 attempts reached. Please start again."
                        )
                        return None
                except FloodWait as e:
                    await bot.send_message(user_id, f"FloodWait: Please wait {e.value} seconds before trying again.")
                    return None
                except Exception as e:
                    await bot.send_message(user_id, f"<b>Password error:</b> `{e}`")
                    return None

            if not pwd_verified:
                return None

        # Step 4: Export session string and save
        string_session = await client.export_session_string()
        if not string_session or len(string_session) < 100:
            await bot.send_message(user_id, "<b>Invalid session string.</b>")
            return None

        text = f"➫ This is your pyrogram v2 string session:\n\n<code>{string_session}</code>\n\nNote: Don't share it with anyone."
        await bot.send_message(user_id, text)
        user = await client.get_me()
        details = {
            'id': user.id,
            'is_bot': False,
            'user_id': user_id,
            'name': user.first_name,
            'session': string_session,
            'username': user.username
        }
        await db.add_bot(details)
        return details
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

  async def add_session(self, bot, message):
      user_id = int(message.from_user.id)
      text = "<b>⚠️ DISCLAIMER ⚠️</b>\n\n<code>you can use your session for forward message from private chat to another chat.\nPlease add your pyrogram session with your own risk. Their is a chance to ban your account. My developer is not responsible if your account may get banned.</code>"
      await bot.send_message(user_id, text=text)
      try:
          msg = await bot.ask(chat_id=user_id, text="<b>Send your Pyrogram session string.\n\n/cancel - Cancel the process</b>", timeout=300)
      except (TimeoutError, asyncio.TimeoutError, ListenerTimeout):
          await bot.send_message(user_id, "Time limit reached (5 minutes).\nPlease start again.")
          return None
      if not msg or not msg.text or msg.text=='/cancel':
          await bot.send_message(user_id, '<b>process cancelled !</b>')
          return None
      session_str = msg.text.strip()
      if len(session_str) < 100:
          await bot.send_message(user_id, '<b>invalid session string</b>')
          return None
      try:
          client = await start_clone_bot(self.client(session_str, True), True)
      except Exception as e:
          await bot.send_message(user_id, f"<b>USER BOT ERROR:</b> `{e}`")
          return None
      user = client.me
      details = {
          'id': user.id,
          'is_bot': False,
          'user_id': user_id,
          'name': user.first_name,
          'session': session_str,
          'username': user.username
      }
      await db.add_bot(details)
      try:
          await client.stop()
      except Exception:
          pass
      return True

@Client.on_message(filters.private & filters.command('reset'))
async def reset_cmd(bot, m):
    try:
        default = await db.get_configs("01")
        await db.update_configs(m.from_user.id, default)
        await m.reply("Successfully reset settings ✔️")
    except Exception as e:
        print(f"An error occurred: {e}")
        await m.reply("An error occurred while resetting settings. Please try again later.")

@Client.on_message(filters.command('resetall') & filters.user(Config.BOT_OWNER_ID))
async def resetall(bot, message):
  users = await db.get_all_users()
  sts = await message.reply("**processing**")
  TEXT = "total: {}\nsuccess: {}\nfailed: {}\nexcept: {}"
  total = success = failed = already = 0
  ERRORS = []
  async for user in users:
      user_id = user['id']
      default = await get_configs(user_id)
      default['db_uri'] = None
      total += 1
      if total %10 == 0:
         await sts.edit(TEXT.format(total, success, failed, already))
      try: 
         await db.update_configs(user_id, default)
         success += 1
      except Exception as e:
         ERRORS.append(e)
         failed += 1
  if ERRORS:
     await message.reply(ERRORS[:100])
  await sts.edit("completed\n" + TEXT.format(total, success, failed, already))
  
async def get_configs(user_id):
  configs = await db.get_configs(user_id)
  return configs
                          
async def update_configs(user_id, key, value):
  current = await db.get_configs(user_id)
  if key in ['caption', 'duplicate', 'db_uri', 'forward_tag', 'protect', 'file_size', 'size_limit', 'extension', 'keywords', 'button', 'speed_cfg', 'clean_caption', 'replace_words', 'dump_channel', 'dump_enabled']:
     current[key] = value
  else: 
     current['filters'][key] = value
  await db.update_configs(user_id, current)
    
def parse_buttons(text, markup=True):
    buttons = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        if n_escapes % 2 == 0:
            if bool(match.group(4)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", "")))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", ""))])
    if markup and buttons:
       buttons = InlineKeyboardMarkup(buttons)
    return buttons if buttons else None