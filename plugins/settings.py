import asyncio 
from database import db
from config import Config
from translation import Translation
from pyrogram import Client, filters
from .test import get_configs, update_configs, CLIENT, parse_buttons
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CLIENT = CLIENT()


@Client.on_message(filters.command('settings'))
async def settings(client, message):
   await message.delete()
   await message.reply_text(
     "<b>cʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ʏᴏᴜʀ ᴡɪsʜ.</b>",
     reply_markup=main_buttons(message.from_user.id)
     )
    
@Client.on_callback_query(filters.regex(r'^settings'))
async def settings_query(bot, query):
  user_id = query.from_user.id
  i, type = query.data.split("#")
  buttons = [[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data="settings#main")]]
  
  if type=="main":
     await query.message.edit_text(
       "<b>cʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ʏᴏᴜʀ ᴡɪsʜ.</b>",
       reply_markup=main_buttons(user_id))

  elif type=="speed":
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))

  elif type.startswith("speed_mode_"):
     mode = type.replace("speed_mode_", "")
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     speed_cfg['mode'] = mode
     if mode == 'extreme':
        speed_cfg['delay'] = 0.5
        speed_cfg['batch_size'] = 100
     elif mode == 'fast':
        speed_cfg['delay'] = 1.0
        speed_cfg['batch_size'] = 100
     elif mode == 'normal':
        speed_cfg['delay'] = 3.0
        speed_cfg['batch_size'] = 50
     elif mode == 'safe':
        speed_cfg['delay'] = 5.0
        speed_cfg['batch_size'] = 20
     await update_configs(user_id, 'speed_cfg', speed_cfg)
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))

  elif type.startswith("speed_adj_"):
     adj = float(type.replace("speed_adj_", ""))
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     new_delay = round(max(0.2, min(30.0, float(speed_cfg.get('delay', 1.0)) + adj)), 1)
     speed_cfg['delay'] = new_delay
     speed_cfg['mode'] = 'custom'
     await update_configs(user_id, 'speed_cfg', speed_cfg)
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))

  elif type == "speed_toggle_jitter":
     configs = await get_configs(user_id)
     speed_cfg = configs.get('speed_cfg') or {'mode': 'fast', 'delay': 1.0, 'jitter': True, 'batch_size': 100}
     speed_cfg['jitter'] = not speed_cfg.get('jitter', True)
     await update_configs(user_id, 'speed_cfg', speed_cfg)
     await query.message.edit_text(
        speed_text(speed_cfg),
        reply_markup=speed_buttons(speed_cfg))
       
  elif type=="bots":
     buttons = [] 
     _bot = await db.get_bot(user_id)
     if _bot is not None:
        buttons.append([InlineKeyboardButton(_bot['name'],
                         callback_data=f"settings#editbot")])
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴜsᴇʀ ʙᴏᴛ ✚', 
                         callback_data="settings#adduserbot")])
        buttons.append([InlineKeyboardButton('✚ ʟᴏɢɪɴ ᴜsᴇʀ ʙᴏᴛ ✚', 
                         callback_data="settings#addlogin")])


     else:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ʙᴏᴛ ✚', 
                         callback_data="settings#addbot")])
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴜsᴇʀ ʙᴏᴛ ✚', 
                         callback_data="settings#adduserbot")])
        buttons.append([InlineKeyboardButton('✚ ʟᴏɢɪɴ ᴜsᴇʀ ʙᴏᴛ ✚', 
                         callback_data="settings#addlogin")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
       "<b><u>ᴍʏ ʙᴏᴛs</b></u>\n\n<b>ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴀʟʟ ʙᴏᴛ ғʀᴏᴍ ʜᴇʀᴇ</b>",
       reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbot":
     try:
        await query.message.delete()
     except Exception:
        pass
     res = await CLIENT.add_bot(bot, query)
     if res != True: return
     await bot.send_message(
        user_id,
        "<b>ʙᴏᴛ ᴛᴏᴋᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ ᴀᴅᴅᴇᴅ ᴛᴏ ᴅʙ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type == "addlogin":
     try:
        await query.message.delete()
     except Exception:
        pass
     user = await CLIENT.add_login(bot, query)
     if user is None: return    
     await bot.send_message(
        user_id,
        "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ʟᴏɢɪɴ ᴛᴏ ᴅʙ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
        

  elif type=="adduserbot":
     try:
        await query.message.delete()
     except Exception:
        pass
     res = await CLIENT.add_session(bot, query)
     if res != True: return
     await bot.send_message(
        user_id,
        "<b>sᴇssɪᴏɴ sᴜᴄᴄᴇss ғᴜʟʟʏ ᴀᴅᴅᴇᴅ ᴛᴏ ᴅʙ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type=="channels":
     buttons = []
     channels = await db.get_user_channels(user_id)
     for channel in channels:
        buttons.append([InlineKeyboardButton(f"{channel['title']}",
                         callback_data=f"settings#editchannels_{channel['chat_id']}")])
     buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ✚', 
                      callback_data="settings#addchannel")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text( 
       "<b><u>ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟs</b></u>\n\n<b>ʏᴏᴜ ᴄᴀɴ ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ ʜᴇʀᴇ ‼️</b>",
       reply_markup=InlineKeyboardMarkup(buttons))
   
  elif type=="addchannel":  
     await query.message.delete()
     try:
         text = await bot.send_message(user_id, "<b>sᴇᴛ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ\n\nғᴏʀᴡᴀʀᴅ ᴀ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴛᴀʀɢᴇᴛ ᴄʜᴀɴɴᴇʟ.\n/cancel - ᴛᴏ ᴄᴀɴᴄᴇʟ ᴛʜɪs ᴘʀᴏᴄᴇss</b>")
         chat_ids = await bot.listen(chat_id=user_id, timeout=300)
         if chat_ids.text=="/cancel":
            await chat_ids.delete()
            return await text.edit_text(
                  "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
         elif not chat_ids.forward_date:
            await chat_ids.delete()
            return await text.edit_text("**ᴛʜɪs ɪs ɴᴏᴛ ᴀ ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇ**")
         else:
            chat_id = chat_ids.forward_from_chat.id
            title = chat_ids.forward_from_chat.title
            username = chat_ids.forward_from_chat.username
            username = "@" + username if username else "private"
         chat = await db.add_channel(user_id, chat_id, title, username)
         await chat_ids.delete()
         await text.edit_text(
            "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ✅</b>" if chat else "<b>ᴛʜɪs ᴄʜᴀɴɴᴇʟ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴅᴅᴇᴅ</b>",
            reply_markup=InlineKeyboardMarkup(buttons))
     except asyncio.exceptions.TimeoutError:
         await text.edit_text('ᴘʀᴏᴄᴇss ʜᴀs ʙᴇᴇɴ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴄᴀɴᴄᴇʟʟᴇᴅ.', reply_markup=InlineKeyboardMarkup(buttons))

  
  elif type=="editbot": 
     bot = await db.get_bot(user_id)
     TEXT = Translation.BOT_DETAILS if bot['is_bot'] else Translation.USER_DETAILS
     buttons = [[InlineKeyboardButton('❌ ʀᴇᴍᴏᴠᴇ ❌', callback_data=f"settings#removebot")
               ],
               [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data="settings#bots")]]
     await query.message.edit_text(
        TEXT.format(bot['name'], bot['id'], bot['username']),
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type=="removebot":
     await db.remove_bot(user_id)
     await query.message.edit_text(
        "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type.startswith("editchannels"): 
     chat_id = type.split('_')[1]
     chat = await db.get_channel_details(user_id, chat_id)
     buttons = [[InlineKeyboardButton('❌ ʀᴇᴍᴏᴠᴇ ❌', callback_data=f"settings#removechannel_{chat_id}")
               ],
               [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data="settings#channels")]]
     await query.message.edit_text(
        f"<b><u>📄 ᴄʜᴀɴɴᴇʟ ᴅᴇᴛᴀɪʟs</b></u>\n\n<b>- ᴛɪᴛʟᴇ:</b> <code>{chat['title']}</code>\n<b>- ᴄʜᴀɴɴᴇʟ ɪᴅ: </b> <code>{chat['chat_id']}</code>\n<b>- ᴜsᴇʀɴᴀᴍᴇ:</b> {chat['username']}",
        reply_markup=InlineKeyboardMarkup(buttons))
        
  elif type.startswith("removechannel"):
     chat_id = type.split('_')[1]
     await db.remove_channel(user_id, chat_id)
     await query.message.edit_text(
        "<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇᴅ ✅</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                               
  elif type=="caption":
     buttons = []
     data = await get_configs(user_id)
     caption = data['caption']
     clean_caption = data.get('clean_caption', False)
     clean_mark = "✅ ᴏɴ" if clean_caption else "❌ ᴏғғ"
     if caption is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴄᴀᴘᴛɪᴏɴ ✚', 
                      callback_data="settings#addcaption")])
     else:
        buttons.append([InlineKeyboardButton('sᴇᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#seecaption")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ᴅᴇʟᴇᴛᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#deletecaption"))
     buttons.append([InlineKeyboardButton(f"🧹 ᴀᴜᴛᴏ-ᴄʟᴇᴀɴ ᴄᴀᴘᴛɪᴏɴ: {clean_mark}", 
                   callback_data="settings#toggle_cleancaption")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM CAPTION & CLEANER</b></u>\n\n"
        "<b>Configure custom captions or enable auto-cleaning to automatically strip foreign links, usernames & promotional ads from captions!</b>\n\n"
        "<b><u>AVAILABLE FILLINGS:</b></u>\n- <code>{filename}</code> : Filename\n- <code>{size}</code> : File size\n- <code>{caption}</code> : default caption",
        reply_markup=InlineKeyboardMarkup(buttons))
                                
  elif type=="toggle_cleancaption":
     data = await get_configs(user_id)
     curr = data.get('clean_caption', False)
     await update_configs(user_id, 'clean_caption', not curr)
     await query.answer(f"Auto-Clean: {'Enabled' if not curr else 'Disabled'}")
     data = await get_configs(user_id)
     caption = data['caption']
     clean_caption = data.get('clean_caption', False)
     clean_mark = "✅ ᴏɴ" if clean_caption else "❌ ᴏғғ"
     buttons = []
     if caption is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴄᴀᴘᴛɪᴏɴ ✚', 
                      callback_data="settings#addcaption")])
     else:
        buttons.append([InlineKeyboardButton('sᴇᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#seecaption")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ᴅᴇʟᴇᴛᴇ ᴄᴀᴘᴛɪᴏɴ', 
                      callback_data="settings#deletecaption"))
     buttons.append([InlineKeyboardButton(f"🧹 ᴀᴜᴛᴏ-ᴄʟᴇᴀɴ ᴄᴀᴘᴛɪᴏɴ: {clean_mark}", 
                   callback_data="settings#toggle_cleancaption")])
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM CAPTION & CLEANER</b></u>\n\n"
        "<b>Configure custom captions or enable auto-cleaning to automatically strip foreign links, usernames & promotional ads from captions!</b>\n\n"
        "<b><u>AVAILABLE FILLINGS:</b></u>\n- <code>{filename}</code> : Filename\n- <code>{size}</code> : File size\n- <code>{caption}</code> : default caption",
        reply_markup=InlineKeyboardMarkup(buttons))
                                
  elif type=="seecaption":   
     data = await get_configs(user_id)
     buttons = [[InlineKeyboardButton('🖋️ ᴇᴅɪᴛ ᴄᴀᴘᴛɪᴏɴ', 
                  callback_data="settings#addcaption")
               ],[
               InlineKeyboardButton('• ʙᴀᴄᴋ', 
                 callback_data="settings#caption")]]
     await query.message.edit_text(
        f"<b><u>YOUR CUSTOM CAPTION</b></u>\n\n<code>{data['caption']}</code>",
        reply_markup=InlineKeyboardMarkup(buttons))
    
  elif type=="deletecaption":
     await update_configs(user_id, 'caption', None)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                              
  elif type=="addcaption":
     await query.message.delete()
     try:
         text = await bot.send_message(query.message.chat.id, "Send your custom caption\n/cancel - <code>cancel this process</code>")
         caption = await bot.listen(chat_id=user_id, timeout=300)
         if caption.text=="/cancel":
            await caption.delete()
            return await text.edit_text(
                  "<b>process canceled !</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
         try:
            caption.text.format(filename='', size='', caption='')
         except KeyError as e:
            await caption.delete()
            return await text.edit_text(
               f"<b>wrong filling {e} used in your caption. change it</b>",
               reply_markup=InlineKeyboardMarkup(buttons))
         await update_configs(user_id, 'caption', caption.text)
         await caption.delete()
         await text.edit_text(
            "<b>Successfully Updated</b>",
            reply_markup=InlineKeyboardMarkup(buttons))
     except asyncio.exceptions.TimeoutError:
         await text.edit_text('Process has been automatically cancelled', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="button":
     buttons = []
     button = (await get_configs(user_id))['button']
     if button is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ʙᴜᴛᴛᴏɴ ✚', 
                      callback_data="settings#addbutton")])
     else:
        buttons.append([InlineKeyboardButton('👀 sᴇᴇ ʙᴜᴛᴛᴏɴ', 
                      callback_data="settings#seebutton")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ʀᴇᴍᴏᴠᴇ ʙᴜᴛᴛᴏɴ ', 
                      callback_data="settings#deletebutton"))
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM BUTTON</b></u>\n\n<b>You can set an inline button for messages.</b>\n\n<b><u>FORMAT:</b></u>\n`[Button Name][buttonurl:https://t.me/your_link]`\n",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbutton":
     await query.message.delete()
     try:
         txt = await bot.send_message(user_id, text="**Send your custom button.\n\nFORMAT:**\n`[Button Name][buttonurl:https://t.me/your_link]`\n\n/cancel - `cancel this process`")
         ask = await bot.listen(chat_id=user_id, timeout=300)
         if not ask or not ask.text or ask.text == '/cancel':
            return await txt.edit_text("<b>Process cancelled !</b>", reply_markup=InlineKeyboardMarkup(buttons))
         button = parse_buttons(ask.text)
         if not button:
            try: await ask.delete()
            except Exception: pass
            return await txt.edit_text("**INVALID BUTTON FORMAT**", reply_markup=InlineKeyboardMarkup(buttons))
         await update_configs(user_id, 'button', ask.text)
         try: await ask.delete()
         except Exception: pass
         await txt.edit_text("**Successfully button added**",
            reply_markup=InlineKeyboardMarkup(buttons))
     except Exception as e:
         await txt.edit_text(f'Process cancelled or timed out ({e})', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seebutton":
      button = (await get_configs(user_id))['button']
      button = parse_buttons(button, markup=False)
      button.append([InlineKeyboardButton("↩ Back", "settings#button")])
      await query.message.edit_text(
         "**YOUR CUSTOM BUTTON**",
         reply_markup=InlineKeyboardMarkup(button))
      
  elif type=="deletebutton":
     await update_configs(user_id, 'button', None)
     await query.message.edit_text(
        "**Successfully button deleted**",
        reply_markup=InlineKeyboardMarkup(buttons))
   
  elif type=="database":
     buttons = []
     db_uri = (await get_configs(user_id))['db_uri']
     if db_uri is None:
        buttons.append([InlineKeyboardButton('✚ ᴀᴅᴅ ᴜʀʟ ✚', 
                      callback_data="settings#addurl")])
     else:
        buttons.append([InlineKeyboardButton('👀 sᴇᴇ ᴜʀʟ', 
                      callback_data="settings#seeurl")])
        buttons[-1].append(InlineKeyboardButton('🗑️ ʀᴇᴍᴏᴠᴇ ᴜʀʟ ', 
                      callback_data="settings#deleteurl"))
     buttons.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>DATABASE</u>\n\nDatabase is required for store your duplicate messages permenant. other wise stored duplicate media may be disappeared when after bot restart.</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
  elif type=="addurl":
     await query.message.delete()
     uri = await bot.ask(user_id, "<b>please send your mongodb url.</b>\n\n<i>get your Mongodb url from [here](https://mongodb.com)</i>", disable_web_page_preview=True)
     if uri.text=="/cancel":
        return await uri.reply_text(
                  "<b>process canceled !</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
     if not uri.text.startswith("mongodb+srv://") and not uri.text.endswith("majority"):
        return await uri.reply("<b>Invalid Mongodb Url</b>",
                   reply_markup=InlineKeyboardMarkup(buttons))
     await update_configs(user_id, 'db_uri', uri.text)
     await uri.reply("**Successfully database url added**",
             reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seeurl":
     db_uri = (await get_configs(user_id))['db_uri']
     await query.answer(f"DATABASE URL: {db_uri}", show_alert=True)
  
  elif type=="deleteurl":
     await update_configs(user_id, 'db_uri', None)
     await query.message.edit_text(
        "**Successfully your database url deleted**",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type=="dump":
     if user_id not in Config.BOT_OWNER_ID:
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     dump_chan, dump_enabled = await db.get_admin_dump()
     state_mark = "✅ ᴏɴ" if dump_enabled else "❌ ᴏғғ"
     current_info = f"<code>{dump_chan}</code>" if dump_chan else "Not Set"
     
     btn = [
        [InlineKeyboardButton(f"📦 ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ: {state_mark}", callback_data="settings#toggledump")],
        [InlineKeyboardButton("➕ sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="settings#setdump")]
     ]
     if dump_chan:
        btn[1].append(InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ", callback_data="settings#deletedump"))
     btn.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")])
     
     await query.message.edit_text(
        "<b><u>📦 MEDIA DUMP / BACKUP CHANNEL (ADMIN ONLY)</u></b>\n\n"
        "A separate dedicated channel where all forwarded media/files from all users are permanently backed up.\n\n"
        f"<b>• Current Dump Target:</b> {current_info}\n"
        f"<b>• Media Dump Status:</b> {state_mark}\n\n"
        "<i>👑 Only bot admins can configure this channel. Normal users cannot access this setting.</i>",
        reply_markup=InlineKeyboardMarkup(btn)
     )

  elif type=="toggledump":
     if user_id not in Config.BOT_OWNER_ID:
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     dump_chan, dump_enabled = await db.get_admin_dump()
     await db.update_admin_dump(dump_chan, not dump_enabled)
     await query.answer(f"Media Dump: {'Enabled' if not dump_enabled else 'Disabled'}")
     dump_chan, dump_enabled = await db.get_admin_dump()
     state_mark = "✅ ᴏɴ" if dump_enabled else "❌ ᴏғғ"
     current_info = f"<code>{dump_chan}</code>" if dump_chan else "Not Set"
     btn = [
        [InlineKeyboardButton(f"📦 ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ: {state_mark}", callback_data="settings#toggledump")],
        [InlineKeyboardButton("➕ sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="settings#setdump")]
     ]
     if dump_chan:
        btn[1].append(InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ", callback_data="settings#deletedump"))
     btn.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>📦 MEDIA DUMP / BACKUP CHANNEL (ADMIN ONLY)</u></b>\n\n"
        "A separate dedicated channel where all forwarded media/files from all users are permanently backed up.\n\n"
        f"<b>• Current Dump Target:</b> {current_info}\n"
        f"<b>• Media Dump Status:</b> {state_mark}\n\n"
        "<i>👑 Only bot admins can configure this channel. Normal users cannot access this setting.</i>",
        reply_markup=InlineKeyboardMarkup(btn)
     )

  elif type=="setdump":
     if user_id not in Config.BOT_OWNER_ID:
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     await query.message.delete()
     try:
         txt = await bot.send_message(user_id, "<b>Please send your Dump Channel ID or username</b>\n(Example: <code>-1001234567890</code> or <code>@my_dump_channel</code>)\n/cancel - <code>cancel</code>")
         ask = await bot.listen(chat_id=user_id, timeout=300)
         if not ask or not ask.text or ask.text == '/cancel':
             return await txt.edit_text("<b>Process cancelled !</b>", reply_markup=InlineKeyboardMarkup(buttons))
         raw = ask.text.strip()
         if raw.lstrip('-').isdigit():
             c_id = int(raw)
         elif raw.startswith('@'):
             c_id = raw
         else:
             c_id = raw
         await db.update_admin_dump(c_id, True)
         await txt.edit_text(f"<b>✅ Global Dump Channel set to:</b> <code>{c_id}</code>\nMedia Dump is now <b>Enabled</b> for all forwardings!", reply_markup=InlineKeyboardMarkup(buttons))
     except Exception as e:
         await bot.send_message(user_id, f"Process cancelled: {e}", reply_markup=InlineKeyboardMarkup(buttons))

  elif type=="deletedump":
     if user_id not in Config.BOT_OWNER_ID:
        return await query.answer("⚠️ Dump Channel settings are restricted to Bot Admins only!", show_alert=True)
     await db.update_admin_dump(None, False)
     await query.answer("Dump Channel removed!", show_alert=True)
     btn = [
        [InlineKeyboardButton("📦 ᴍᴇᴅɪᴀ ᴅᴜᴍᴘ: ❌ ᴏғғ", callback_data="settings#toggledump")],
        [InlineKeyboardButton("➕ sᴇᴛ ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="settings#setdump")],
        [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")]
     ]
     await query.message.edit_text(
        "<b><u>📦 MEDIA DUMP / BACKUP CHANNEL (ADMIN ONLY)</u></b>\n\n"
        "A separate dedicated channel where all forwarded media/files from all users are permanently backed up.\n\n"
        "<b>• Current Dump Target:</b> Not Set\n"
        "<b>• Status:</b> ❌ ᴏғғ\n\n"
        "<i>👑 Only bot admins can configure this channel. Normal users cannot access this setting.</i>",
        reply_markup=InlineKeyboardMarkup(btn)
     )
      
  elif type=="filters":
     await query.message.edit_text(
        "<b><u>💠 CUSTOM FILTERS 💠</b></u>\n\n**configure the type of messages which you want forward**",
        reply_markup=await filters_buttons(user_id))
  elif type=="nextfilters":
     await query.edit_message_reply_markup( 
        reply_markup=await next_filters_buttons(user_id))
   
  elif type.startswith("updatefilter"):
     i, key, value = type.split('-')
     if value=="True":
        await update_configs(user_id, key, False)
     else:
        await update_configs(user_id, key, True)
     if key in ['poll', 'protect']:
        return await query.edit_message_reply_markup(
           reply_markup=await next_filters_buttons(user_id)) 
     await query.edit_message_reply_markup(
        reply_markup=await filters_buttons(user_id))
   
  elif type.startswith("file_size"):
    settings = await get_configs(user_id)
    size = settings.get('file_size', 0)
    i, limit = size_limit(settings['size_limit'])
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {limit} `{size} MB` will forward</b>',
       reply_markup=size_button(size))
  elif type.startswith("update_size"):
    size = int(query.data.split('-')[1])
    if 0 < size > 2000:
      return await query.answer("size limit exceeded", show_alert=True)
    await update_configs(user_id, 'file_size', size)
    i, limit = size_limit((await get_configs(user_id))['size_limit'])
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {limit} `{size} MB` will forward</b>',
       reply_markup=size_button(size))
  
  elif type.startswith('update_limit'):
    i, limit, size = type.split('-')
    limit, sts = size_limit(limit)
    await update_configs(user_id, 'size_limit', limit) 
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {sts} `{size} MB` will forward</b>',
       reply_markup=size_button(int(size)))
  elif type == "add_extension":
    await query.message.delete() 
    ext = await bot.ask(user_id, text="**please send your extensions (seperete by space)**")
    if ext.text == '/cancel':
       return await ext.reply_text(
                  "<b>process canceled</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
    extensions = ext.text.split(" ")
    extension = (await get_configs(user_id))['extension']
    if extension:
        for extn in extensions:
            extension.append(extn)
    else:
        extension = extensions
    await update_configs(user_id, 'extension', extension)
    await ext.reply_text(
        f"**successfully updated**",
        reply_markup=InlineKeyboardMarkup(buttons))
  elif type == "get_extension":
    extensions = (await get_configs(user_id))['extension']
    btn = extract_btn(extensions)
    btn.append([InlineKeyboardButton('✚ ᴀᴅᴅ ✚', 'settings#add_extension')])
    btn.append([InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ᴀʟʟ', 'settings#rmve_all_extension')])
    btn.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 'settings#main')])
    await query.message.edit_text(
        text='<b><u>EXTENSIONS</u></b>\n\n**Files with these extiontions will not forward**',
        reply_markup=InlineKeyboardMarkup(btn))
  
  elif type == "rmve_all_extension":
    await update_configs(user_id, 'extension', None)
    await query.message.edit_text(text="**sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ**",
                                   reply_markup=InlineKeyboardMarkup(buttons))
  elif type == "add_keyword":
    await query.message.delete()
    ask = await bot.ask(user_id, text="**ᴘʟᴇᴀsᴇ sᴇɴᴛ ᴋᴇʏᴡᴏʀᴅ (sᴇᴘʀᴀᴛᴇᴅ ʙʏ sᴘᴀᴄᴇ)**")
    if ask.text == '/cancel':
       return await ask.reply_text(
                  "<b>ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ ✅</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
    keywords = ask.text.split(" ")
    keyword = (await get_configs(user_id))['keywords']
    if keyword:
        for word in keywords:
            keyword.append(word)
    else:
        keyword = keywords
    await update_configs(user_id, 'keywords', keyword)
    await ask.reply_text(
        f"**successfully updated**",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type == "get_keyword":
    keywords = (await get_configs(user_id))['keywords']
    btn = extract_btn(keywords)
    btn.append([InlineKeyboardButton('✚ ᴀᴅᴅ ✚', 'settings#add_keyword')])
    btn.append([InlineKeyboardButton('ʀᴇᴍᴏᴠᴇ ᴀʟʟ', 'settings#rmve_all_keyword')])
    btn.append([InlineKeyboardButton('• ʙᴀᴄᴋ', 'settings#main')])
    await query.message.edit_text(
        text='<b><u>KEYWORDS</u></b>\n\n**File with these keywords in file name will forwad**',
        reply_markup=InlineKeyboardMarkup(btn))
      
  elif type == "rmve_all_keyword":
    await update_configs(user_id, 'keywords', None)
    await query.message.edit_text(text="**sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ**",
                                   reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "courseseller":
     configs = await get_configs(user_id)
     await query.message.edit_text(
        course_seller_text(configs),
        reply_markup=course_seller_buttons(configs)
     )

  elif type == "cs_toggle_mode":
     configs = await get_configs(user_id)
     curr = bool(configs.get('course_seller_mode', False))
     new_val = not curr
     configs['course_seller_mode'] = new_val
     if new_val:
        configs['auto_course_list'] = True
        configs['auto_numbering'] = True
        configs['username_remover'] = True
        configs['link_remover'] = True
        configs['hidden_link_remover'] = True
        configs['forward_tag'] = False
     await db.update_configs(user_id, configs)
     await query.answer(f"Course Seller Mode: {'Activated ⚡️' if new_val else 'Disabled'}")
     await query.message.edit_text(
        course_seller_text(configs),
        reply_markup=course_seller_buttons(configs)
     )

  elif type == "cs_toggle_list":
     configs = await get_configs(user_id)
     curr = bool(configs.get('auto_course_list', False))
     configs['auto_course_list'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Course List Maker: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_num":
     configs = await get_configs(user_id)
     curr = bool(configs.get('auto_numbering', False))
     configs['auto_numbering'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Lecture Numbering: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_user":
     configs = await get_configs(user_id)
     curr = bool(configs.get('username_remover', False))
     configs['username_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Username Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_link":
     configs = await get_configs(user_id)
     curr = bool(configs.get('link_remover', False))
     configs['link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Link Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "cs_toggle_hidden":
     configs = await get_configs(user_id)
     curr = bool(configs.get('hidden_link_remover', False))
     configs['hidden_link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Hidden Link Sanitizer: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(course_seller_text(configs), reply_markup=course_seller_buttons(configs))

  elif type == "ftm":
     configs = await get_configs(user_id)
     await query.message.edit_text(
        ftm_text(configs),
        reply_markup=ftm_buttons(configs)
     )

  elif type == "ftm_toggle_user":
     configs = await get_configs(user_id)
     curr = bool(configs.get('username_remover', False))
     configs['username_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Username Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_toggle_link":
     configs = await get_configs(user_id)
     curr = bool(configs.get('link_remover', False))
     configs['link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Link Remover: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_toggle_hidden":
     configs = await get_configs(user_id)
     curr = bool(configs.get('hidden_link_remover', False))
     configs['hidden_link_remover'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Hidden Link Sanitizer: {'ON' if not curr else 'OFF'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_toggle_tag":
     configs = await get_configs(user_id)
     curr = bool(configs.get('forward_tag', False))
     configs['forward_tag'] = not curr
     await db.update_configs(user_id, configs)
     await query.answer(f"Forward Tag: {'Preserved' if not curr else 'Removed (Clean)'}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_cycle_upload":
     configs = await get_configs(user_id)
     modes = ['media', 'video', 'document']
     curr_mode = configs.get('upload_type', 'media')
     next_mode = modes[(modes.index(curr_mode) + 1) % len(modes)] if curr_mode in modes else 'media'
     configs['upload_type'] = next_mode
     await db.update_configs(user_id, configs)
     await query.answer(f"Upload Type: {next_mode.upper()}")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type == "ftm_set_user_rep":
     await query.message.delete()
     ask = await bot.ask(user_id, text="<b>👤 Send your replacement username (e.g. <code>@MyBrandCourses</code>):</b>\n\nSend <code>none</code> to clear\n/cancel - Cancel", timeout=120)
     if ask.text and not ask.text.startswith('/'):
        val = None if ask.text.strip().lower() == 'none' else ask.text.strip()
        configs = await get_configs(user_id)
        configs['username_replacer'] = val
        await db.update_configs(user_id, configs)
        await bot.send_message(user_id, f"✅ Username replacer set to: <code>{val}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#ftm')]]))

  elif type == "ftm_set_link_rep":
     await query.message.delete()
     ask = await bot.ask(user_id, text="<b>🔗 Send your replacement link (e.g. <code>https://t.me/MyChannel</code>):</b>\n\nSend <code>none</code> to clear\n/cancel - Cancel", timeout=120)
     if ask.text and not ask.text.startswith('/'):
        val = None if ask.text.strip().lower() == 'none' else ask.text.strip()
        configs = await get_configs(user_id)
        configs['link_replacer'] = val
        await db.update_configs(user_id, configs)
        await bot.send_message(user_id, f"✅ Link replacer set to: <code>{val}</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#ftm')]]))

  elif type == "ftm_add_word":
     await query.message.delete()
     ask = await bot.ask(user_id, text="<b>🔤 Send word replacement rule as <code>old_word:new_word</code>:</b>\n(Example: <code>@competitor:@mychannel</code> or <code>badword:</code> to delete word)\n/cancel - Cancel", timeout=120)
     if ask.text and ":" in ask.text and not ask.text.startswith('/'):
        parts = ask.text.split(":", 1)
        old, new = parts[0].strip(), parts[1].strip()
        configs = await get_configs(user_id)
        words = configs.get('replace_words', {})
        words[old] = new
        configs['replace_words'] = words
        await db.update_configs(user_id, configs)
        await bot.send_message(user_id, f"✅ Rule added: <code>'{old}' ➔ '{new}'</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='settings#ftm')]]))

  elif type == "ftm_clear_words":
     configs = await get_configs(user_id)
     configs['replace_words'] = {}
     await db.update_configs(user_id, configs)
     await query.answer("All word replacement rules cleared!")
     await query.message.edit_text(ftm_text(configs), reply_markup=ftm_buttons(configs))

  elif type.startswith("alert"):
    alert = type.split('_')[1]
    await query.answer(alert, show_alert=True)

def course_seller_text(cfg):
    mode_status = "🟢 ᴀᴄᴛɪᴠᴇ" if cfg.get('course_seller_mode') else "🔴 ᴅɪsᴀʙʟᴇᴅ"
    list_status = "✅ ᴏɴ" if cfg.get('auto_course_list') else "❌ ᴏғғ"
    num_status = "✅ ᴏɴ" if cfg.get('auto_numbering') else "❌ ᴏғғ"
    user_rem = "✅ ᴏɴ" if cfg.get('username_remover') else "❌ ᴏғғ"
    link_rem = "✅ ᴏɴ" if cfg.get('link_remover') else "❌ ᴏғғ"
    hid_rem = "✅ ᴏɴ" if cfg.get('hidden_link_remover') else "❌ ᴏғғ"
    
    return (
        "<b><u>🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ ⚡️</u></b>\n\n"
        "<b>Power tools engineered specifically for Course Sellers & Content Distributors:</b>\n\n"
        f"⚡️ <b>Master Seller Mode:</b> {mode_status}\n"
        f"📚 <b>Auto Course List Maker:</b> {list_status}\n"
        f"🔢 <b>Auto Lecture Numbering:</b> {num_status}\n"
        f"👤 <b>Other Seller Username Remover:</b> {user_rem}\n"
        f"🔗 <b>Link Remover & Replacer:</b> {link_rem}\n"
        f"🔍 <b>Hidden Link Sanitizer:</b> {hid_rem}\n\n"
        "<i>💡 When enabled, the bot automatically removes competitor ads, numbers your lectures, and creates a clean clickable syllabus table of contents!</i>"
    )

def course_seller_buttons(cfg):
    mode_btn = "🛑 ᴅɪsᴀʙʟᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ" if cfg.get('course_seller_mode') else "⚡ ᴇɴᴀʙʟᴇ sᴇʟʟᴇʀ ᴍᴏᴅᴇ"
    list_mark = "✅" if cfg.get('auto_course_list') else "❌"
    num_mark = "✅" if cfg.get('auto_numbering') else "❌"
    user_mark = "✅" if cfg.get('username_remover') else "❌"
    link_mark = "✅" if cfg.get('link_remover') else "❌"
    hid_mark = "✅" if cfg.get('hidden_link_remover') else "❌"
    
    buttons = [
        [InlineKeyboardButton(mode_btn, callback_data="settings#cs_toggle_mode")],
        [
            InlineKeyboardButton(f"📚 ᴄᴏᴜʀsᴇ ʟɪsᴛ ᴍᴀᴋᴇʀ {list_mark}", callback_data="settings#cs_toggle_list"),
            InlineKeyboardButton(f"🔢 ᴀᴜᴛᴏ ɴᴜᴍʙᴇʀɪɴɢ {num_mark}", callback_data="settings#cs_toggle_num")
        ],
        [
            InlineKeyboardButton(f"👤 ᴜsᴇʀɴᴀᴍᴇ ʀᴇᴍᴏᴠᴇʀ {user_mark}", callback_data="settings#cs_toggle_user"),
            InlineKeyboardButton(f"🔗 ʟɪɴᴋ ʀᴇᴍᴏᴠᴇʀ {link_mark}", callback_data="settings#cs_toggle_link")
        ],
        [
            InlineKeyboardButton(f"🔍 ʜɪᴅᴅᴇɴ ʟɪɴᴋs {hid_mark}", callback_data="settings#cs_toggle_hidden"),
            InlineKeyboardButton("🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ", callback_data="settings#ftm")
        ],
        [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")]
    ]
    return InlineKeyboardMarkup(buttons)

def ftm_text(cfg):
    user_rem = "✅ ᴏɴ" if cfg.get('username_remover') else "❌ ᴏғғ"
    user_rep = cfg.get('username_replacer') or "None (Clean only)"
    link_rem = "✅ ᴏɴ" if cfg.get('link_remover') else "❌ ᴏғғ"
    link_rep = cfg.get('link_replacer') or "None (Clean only)"
    hid_rem = "✅ ᴏɴ" if cfg.get('hidden_link_remover') else "❌ ᴏғғ"
    replacements = cfg.get('replace_words', {})
    up_type = str(cfg.get('upload_type', 'media')).upper()
    tag_status = "❌ ʀᴇᴍᴏᴠᴇᴅ (ᴄʟᴇᴀɴ)" if not cfg.get('forward_tag') else "✅ ᴘʀᴇsᴇʀᴠᴇᴅ"
    
    return (
        "<b><u>🛠 sᴋɪɴᴇᴛ ᴛᴇxᴛ & ᴍᴇᴅɪᴀ ᴍᴏᴅɪғɪᴇʀ ⚡️</u></b>\n\n"
        "<b>Skinet Verse Content Sanitization & Re-Branding Suite:</b>\n\n"
        f"👤 <b>Username Remover:</b> {user_rem}\n"
        f"👤 <b>Username Replacer:</b> <code>{user_rep}</code>\n"
        f"🔗 <b>Link Remover:</b> {link_rem}\n"
        f"🔗 <b>Link Replacer:</b> <code>{link_rep}</code>\n"
        f"🔍 <b>Hidden Link Sanitizer:</b> {hid_rem}\n"
        f"🔤 <b>Active Word Replacements:</b> <code>{len(replacements)} rules</code>\n"
        f"📦 <b>Upload Stream Mode:</b> <code>{up_type}</code>\n"
        f"🏷 <b>Forward Tag:</b> <code>{tag_status}</code>\n"
    )

def ftm_buttons(cfg):
    user_mark = "✅ ᴏɴ" if cfg.get('username_remover') else "❌ ᴏғғ"
    link_mark = "✅ ᴏɴ" if cfg.get('link_remover') else "❌ ᴏғғ"
    hid_mark = "✅ ᴏɴ" if cfg.get('hidden_link_remover') else "❌ ᴏғғ"
    tag_mark = "✅ ᴄʟᴇᴀɴ" if not cfg.get('forward_tag') else "⚠️ ᴛᴀɢɢᴇᴅ"
    up_type = str(cfg.get('upload_type', 'media')).capitalize()
    
    buttons = [
        [
            InlineKeyboardButton(f"👤 ᴜsᴇʀɴᴀᴍᴇ: {user_mark}", callback_data="settings#ftm_toggle_user"),
            InlineKeyboardButton("✏️ sᴇᴛ ᴜsᴇʀɴᴀᴍᴇ ʀᴇᴘʟᴀᴄᴇʀ", callback_data="settings#ftm_set_user_rep")
        ],
        [
            InlineKeyboardButton(f"🔗 ʟɪɴᴋs: {link_mark}", callback_data="settings#ftm_toggle_link"),
            InlineKeyboardButton("✏️ sᴇᴛ ʟɪɴᴋ ʀᴇᴘʟᴀᴄᴇʀ", callback_data="settings#ftm_set_link_rep")
        ],
        [
            InlineKeyboardButton(f"🔍 ʜɪᴅᴅᴇɴ ʟɪɴᴋs: {hid_mark}", callback_data="settings#ftm_toggle_hidden"),
            InlineKeyboardButton(f"🏷 ᴛᴀɢ: {tag_mark}", callback_data="settings#ftm_toggle_tag")
        ],
        [
            InlineKeyboardButton("🔤 ᴀᴅᴅ ᴡᴏʀᴅ ʀᴇᴘʟᴀᴄᴇᴍᴇɴᴛ", callback_data="settings#ftm_add_word"),
            InlineKeyboardButton("🗑 ʀᴇsᴇᴛ ᴡᴏʀᴅs", callback_data="settings#ftm_clear_words")
        ],
        [
            InlineKeyboardButton(f"📦 ᴜᴘʟᴏᴀᴅ ᴛʏᴘᴇ: {up_type}", callback_data="settings#ftm_cycle_upload")
        ],
        [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")]
    ]
    return InlineKeyboardMarkup(buttons)

def main_buttons(user_id=None):
  is_admin = bool(user_id and user_id in Config.BOT_OWNER_ID)
  buttons = [[
       InlineKeyboardButton('🤖 ʙᴏᴛs',
                    callback_data=f'settings#bots'),
       InlineKeyboardButton('🏷 ᴄʜᴀɴɴᴇʟs',
                    callback_data=f'settings#channels')
       ],[
       InlineKeyboardButton('🖋️ ᴄᴀᴘᴛɪᴏɴ',
                    callback_data=f'settings#caption'),
       InlineKeyboardButton('🗃 ᴍᴏɴɢᴏ ᴅʙ',
                    callback_data=f'settings#database')
       ],[
       InlineKeyboardButton('🕵‍♀ ғɪʟᴛᴇʀs 🕵‍♀',
                    callback_data=f'settings#filters'),
       InlineKeyboardButton('⏹ ʙᴜᴛᴛᴏɴ',
                    callback_data=f'settings#button')
       ],[
       InlineKeyboardButton('⚡ sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ ⚡',
                    callback_data='settings#speed'),
       InlineKeyboardButton('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ 🚀',
                    callback_data='autosave#main')
       ],[
       InlineKeyboardButton('🎓 ᴄᴏᴜʀsᴇ sᴇʟʟᴇʀ ⚡️',
                    callback_data='settings#courseseller'),
       InlineKeyboardButton('🛠 sᴋɪɴᴇᴛ ᴍᴏᴅɪғɪᴇʀ 🛠',
                    callback_data='settings#ftm')
       ]]
  if is_admin:
      buttons.append([
          InlineKeyboardButton('📦 ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ (ᴀᴅᴍɪɴ)', callback_data='settings#dump'),
          InlineKeyboardButton('ᴇxᴛʀᴀ sᴇᴛᴛɪɴɢs 🧪', callback_data='settings#nextfilters')
      ])
  else:
      buttons.append([
          InlineKeyboardButton('ᴇxᴛʀᴀ sᴇᴛᴛɪɴɢs 🧪', callback_data='settings#nextfilters')
      ])
  buttons.append([
      InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='help')
  ])
  return InlineKeyboardMarkup(buttons)

def speed_buttons(cfg):
  mode = cfg.get('mode', 'fast')
  delay = float(cfg.get('delay', 1.0))
  jitter = cfg.get('jitter', True)

  extreme_mark = " ✅" if mode == "extreme" else ""
  fast_mark = " ✅" if mode == "fast" else ""
  normal_mark = " ✅" if mode == "normal" else ""
  safe_mark = " ✅" if mode == "safe" else ""
  jitter_mark = "✅ ᴏɴ" if jitter else "❌ ᴏғғ"

  buttons = [
    [
      InlineKeyboardButton(f"🚀 ᴇxᴛʀᴇᴍᴇ (0.5s){extreme_mark}", callback_data="settings#speed_mode_extreme"),
      InlineKeyboardButton(f"⚡ ғᴀsᴛ (1.0s){fast_mark}", callback_data="settings#speed_mode_fast"),
    ],
    [
      InlineKeyboardButton(f"🏃 ɴᴏʀᴍᴀʟ (3.0s){normal_mark}", callback_data="settings#speed_mode_normal"),
      InlineKeyboardButton(f"🐢 sᴀғᴇ (5.0s){safe_mark}", callback_data="settings#speed_mode_safe"),
    ],
    [
      InlineKeyboardButton("➖ 0.5s", callback_data="settings#speed_adj_-0.5"),
      InlineKeyboardButton(f"⏱️ ᴅᴇʟᴀʏ: {delay:.1f}s", callback_data=f"settings#alert_Current delay is {delay:.1f}s"),
      InlineKeyboardButton("➕ 0.5s", callback_data="settings#speed_adj_0.5"),
    ],
    [
      InlineKeyboardButton("➖ 1.0s", callback_data="settings#speed_adj_-1.0"),
      InlineKeyboardButton("➕ 1.0s", callback_data="settings#speed_adj_1.0"),
    ],
    [
      InlineKeyboardButton(f"🎲 ᴀɴᴛɪ-ʙᴀɴ ᴊɪᴛᴛᴇʀ: {jitter_mark}", callback_data="settings#speed_toggle_jitter"),
    ],
    [
      InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="settings#main")
    ]
  ]
  return InlineKeyboardMarkup(buttons)

def speed_text(cfg):
  mode = cfg.get('mode', 'fast')
  delay = float(cfg.get('delay', 1.0))
  jitter = cfg.get('jitter', True)
  batch_size = cfg.get('batch_size', 100)

  mode_names = {
    'extreme': '🚀 ᴇxᴛʀᴇᴍᴇ (0.5s)',
    'fast': '⚡ ғᴀsᴛ (1.0s)',
    'normal': '🏃 ɴᴏʀᴍᴀʟ (3.0s)',
    'safe': '🐢 sᴀғᴇ (5.0s - Anti-Ban)',
    'custom': '⚙️ ᴄᴜsᴛᴏᴍ'
  }
  mode_str = mode_names.get(mode, mode.title())
  jitter_str = "✅ ᴇɴᴀʙʟᴇᴅ (±30% random jitter)" if jitter else "❌ ᴅɪsᴀʙʟᴇᴅ"

  return (
    "<b><u>⚡ sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ & ᴀɴᴛɪ-ʙᴀɴ sᴇᴛᴛɪɴɢs ⚡</u></b>\n\n"
    "Configure message forwarding speed, delay intervals, and anti-ban protections.\n\n"
    f"<b>• ᴄᴜʀʀᴇɴᴛ ᴍᴏᴅᴇ:</b> <code>{mode_str}</code>\n"
    f"<b>• ʙᴀsᴇ ᴅᴇʟᴀʏ:</b> <code>{delay:.1f} sec</code>\n"
    f"<b>• ʜᴜᴍᴀɴ ᴊɪᴛᴛᴇʀ:</b> <code>{jitter_str}</code>\n"
    f"<b>• ʙᴀᴛᴄʜ sɪᴢᴇ:</b> <code>{batch_size} msgs</code>\n\n"
    "<i>💡 <b>Modes Reference:</b>\n"
    "• <b>⚡ Fast:</b> 1.0s delay (recommended for normal forwarding)\n"
    "• <b>🏃 Normal:</b> 3.0s delay (balanced speed & safety)\n"
    "• <b>🐢 Safe:</b> 5.0s delay (best for userbots to avoid bans)\n"
    "• <b>🚀 Extreme:</b> 0.5s delay (fastest transfer, recommended for bot tokens)\n"
    "• <b>🎲 Anti-Ban Jitter:</b> Randomizes delays like a human to evade Telegram automated pattern bans</i>"
  )

def size_limit(limit):
   if str(limit) == "None":
      return None, ""
   elif str(limit) == "True":
      return True, "more than"
   else:
      return False, "less than"
def extract_btn(datas):
    i = 0
    btn = []
    if datas:
       for data in datas:
         if i >= 5:
            i = 0
         if i == 0:
            btn.append([InlineKeyboardButton(data, f'settings#alert_{data}')])
            i += 1
            continue
         elif i > 0:
            btn[-1].append(InlineKeyboardButton(data, f'settings#alert_{data}'))
            i += 1
    return btn 

def size_button(size):
  buttons = [[
       InlineKeyboardButton('+',
                    callback_data=f'settings#update_limit-True-{size}'),
       InlineKeyboardButton('=',
                    callback_data=f'settings#update_limit-None-{size}'),
       InlineKeyboardButton('-',
                    callback_data=f'settings#update_limit-False-{size}')
       ],[
       InlineKeyboardButton('+1',
                    callback_data=f'settings#update_size-{size + 1}'),
       InlineKeyboardButton('-1',
                    callback_data=f'settings#update_size_-{size - 1}')
       ],[
       InlineKeyboardButton('+5',
                    callback_data=f'settings#update_size-{size + 5}'),
       InlineKeyboardButton('-5',
                    callback_data=f'settings#update_size_-{size - 5}')
       ],[
       InlineKeyboardButton('+10',
                    callback_data=f'settings#update_size-{size + 10}'),
       InlineKeyboardButton('-10',
                    callback_data=f'settings#update_size_-{size - 10}')
       ],[
       InlineKeyboardButton('+50',
                    callback_data=f'settings#update_size-{size + 50}'),
       InlineKeyboardButton('-50',
                    callback_data=f'settings#update_size_-{size - 50}')
       ],[
       InlineKeyboardButton('+100',
                    callback_data=f'settings#update_size-{size + 100}'),
       InlineKeyboardButton('-100',
                    callback_data=f'settings#update_size_-{size - 100}')
       ],[
       InlineKeyboardButton('↩ Back',
                    callback_data="settings#main")
     ]]
  return InlineKeyboardMarkup(buttons)
async def filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('🏷️ ғᴏʀᴡᴀʀᴅ ᴛᴀɢ',
                    callback_data=f'settings_#updatefilter-forward_tag-{filter["forward_tag"]}'),
       InlineKeyboardButton('✅' if filter['forward_tag'] else '❌',
                    callback_data=f'settings#updatefilter-forward_tag-{filter["forward_tag"]}')
       ],[
       InlineKeyboardButton('🖍️ ᴛᴇxᴛ',
                    callback_data=f'settings_#updatefilter-text-{filters["text"]}'),
       InlineKeyboardButton('✅' if filters['text'] else '❌',
                    callback_data=f'settings#updatefilter-text-{filters["text"]}')
       ],[
       InlineKeyboardButton('📁 ᴅᴏᴄᴜᴍᴇɴᴛs',
                    callback_data=f'settings_#updatefilter-document-{filters["document"]}'),
       InlineKeyboardButton('✅' if filters['document'] else '❌',
                    callback_data=f'settings#updatefilter-document-{filters["document"]}')
       ],[
       InlineKeyboardButton('🎞️ ᴠɪᴅᴇᴏs',
                    callback_data=f'settings_#updatefilter-video-{filters["video"]}'),
       InlineKeyboardButton('✅' if filters['video'] else '❌',
                    callback_data=f'settings#updatefilter-video-{filters["video"]}')
       ],[
       InlineKeyboardButton('📷 ᴘʜᴏᴛᴏs',
                    callback_data=f'settings_#updatefilter-photo-{filters["photo"]}'),
       InlineKeyboardButton('✅' if filters['photo'] else '❌',
                    callback_data=f'settings#updatefilter-photo-{filters["photo"]}')
       ],[
       InlineKeyboardButton('🎧 ᴀᴜᴅɪᴏs',
                    callback_data=f'settings_#updatefilter-audio-{filters["audio"]}'),
       InlineKeyboardButton('✅' if filters['audio'] else '❌',
                    callback_data=f'settings#updatefilter-audio-{filters["audio"]}')
       ],[
       InlineKeyboardButton('🎤 ᴠᴏɪᴄᴇs',
                    callback_data=f'settings_#updatefilter-voice-{filters["voice"]}'),
       InlineKeyboardButton('✅' if filters['voice'] else '❌',
                    callback_data=f'settings#updatefilter-voice-{filters["voice"]}')
       ],[
       InlineKeyboardButton('🎭 ᴀɴɪᴍᴀᴛɪᴏɴs',
                    callback_data=f'settings_#updatefilter-animation-{filters["animation"]}'),
       InlineKeyboardButton('✅' if filters['animation'] else '❌',
                    callback_data=f'settings#updatefilter-animation-{filters["animation"]}')
       ],[
       InlineKeyboardButton('🃏 sᴛɪᴄᴋᴇʀs',
                    callback_data=f'settings_#updatefilter-sticker-{filters["sticker"]}'),
       InlineKeyboardButton('✅' if filters['sticker'] else '❌',
                    callback_data=f'settings#updatefilter-sticker-{filters["sticker"]}')
       ],[
       InlineKeyboardButton('▶️ sᴋɪᴘ ᴅᴜᴘʟɪᴄᴀᴛᴇ',
                    callback_data=f'settings_#updatefilter-duplicate-{filter["duplicate"]}'),
       InlineKeyboardButton('✅' if filter['duplicate'] else '❌',
                    callback_data=f'settings#updatefilter-duplicate-{filter["duplicate"]}')
       ],[
       InlineKeyboardButton('• ʙᴀᴄᴋ',
                    callback_data="settings#main")
       ]]
  return InlineKeyboardMarkup(buttons) 
async def next_filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('📊 ᴘᴏʟʟ',
                    callback_data=f'settings_#updatefilter-poll-{filters["poll"]}'),
       InlineKeyboardButton('✅' if filters['poll'] else '❌',
                    callback_data=f'settings#updatefilter-poll-{filters["poll"]}')
       ],[
       InlineKeyboardButton('🔒 sᴇᴄᴜʀᴇ ᴍᴇssᴀɢᴇs',
                    callback_data=f'settings_#updatefilter-protect-{filter["protect"]}'),
       InlineKeyboardButton('✅' if filter['protect'] else '❌',
                    callback_data=f'settings#updatefilter-protect-{filter["protect"]}')
       ],[
       InlineKeyboardButton('🛑 sɪᴢᴇ ʟɪᴍɪᴛ',
                    callback_data='settings#file_size')
       ],[
       InlineKeyboardButton('💾 ᴇxᴛᴇɴsɪᴏɴ',
                    callback_data='settings#get_extension')
       ],[
       InlineKeyboardButton('♦️ ᴋᴇʏᴡᴏʀᴅ',
                    callback_data='settings#get_keyword')
       ],[
       InlineKeyboardButton('• ʙᴀᴄᴋ', 
                    callback_data="settings#main")
       ]]
  return InlineKeyboardMarkup(buttons) 
   
