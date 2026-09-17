import os
from config import Config

class Translation(object):
  START_TXT = """<b>ʜɪ {}

ɪ'ᴍ <b>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ꜰᴏʀᴡᴀʀᴅ ʙᴏᴛ</b> ⚡️
ɪ ᴄᴀɴ ꜰᴏʀᴡᴀʀᴅ, ᴄʟᴏɴᴇ, ᴀɴᴅ ᴍᴏɴɪᴛᴏʀ ᴄʜᴀɴɴᴇʟs ᴀᴛ ᴜʟᴛʀᴀ-ꜰᴀsᴛ sᴘᴇᴇᴅ.

ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ!</b>"""

  DONATE_TXT = """<b><i>Thanks for using Skinet Verse Forward Bot! ❤️</i></b>"""

  HELP_TXT = """<b><u>🔆 sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ʜᴇʟᴘ</u></b>

<u>**📚 Available Commands:**</u>

<b>⏣ __/start - Check I'm alive__ 
⏣ __/forward - Forward messages__
⏣ __/fwd <start> <end> - Direct range forward__
⏣ __/autosave - Smart AutoSave & Channel Monitoring__
⏣ __/tutorial - 12-Module Master Tutorial Hub__
⏣ __/skinet - Skinet Text & Media Modifier Guide__
⏣ __/pause - Pause ongoing forwarding__
⏣ __/resume - Resume paused forwarding__
⏣ __/stop - Cancel your ongoing forwarding__
⏣ __/unequify - Delete duplicate messages in channels__
⏣ __/settings - Configure your settings__
⏣ __/reset - Reset your settings__</b>

<b><u>💢 Features:</u></b>
<b>► __🎓 Course Seller Mode: Auto lecture numbering & table of contents__
► __🛠 Skinet Modifier: Competitor username & link replacers__
► __🚀 Smart AutoSave: Real-time automatic channel monitoring__
► __Smart Media Filters: Filter Videos, Photos, Documents, Audio__
► __Custom Upload Destinations: Per-channel or global targets__
► __Direct Range Forward: Forward ranges via message links__
► __Pause & Resume: Interactive pause/resume for forward tasks__
► __Auto-Clean Captions: Strip foreign links, ads, usernames__
► __Custom Speed Control: Extreme, Fast, Normal, Safe & Anti-Ban Jitter__
► __Skip duplicate messages, filter extensions & file sizes__</b>"""

  HOW_USE_TXT = """<b><u>⚠️ Before Forwarding:</u></b>
<b>► __Add a bot token or login with userbot in /settings__
► __Add at least one target channel in /settings__ `(your bot/userbot must be admin there)`
► __If the source channel is private, your userbot must be a member there__
► __Then use /forward to start forwarding messages__</b>"""

  ABOUT_TXT = """<b>
╔════❰ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ❱═❍⊱❁
║╭━━━━━━━━━━━━━━━➣
║┣⪼📃 ʙᴏᴛ : sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ
║┣⪼🗣️ ʟᴀɴɢᴜᴀɢᴇ : ᴘʏᴛʜᴏɴ3
║┣⪼📚 ʟɪʙʀᴀʀʏ : ᴘʏʀᴏɢʀᴀᴍ / ᴘʏʀᴏғᴏʀᴋ
║┣⪼⚡ ғᴇᴀᴛᴜʀᴇs : sᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ & ᴀɴᴛɪ-ʙᴀɴ
║┣⪼💎 ᴇᴅɪᴛɪᴏɴ : sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ᴜʟᴛʀᴀ
║┣⪼🗒️ ᴠᴇʀsɪᴏɴ : 2.5.0
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁</b>"""

  STATUS_TXT = """<b>
╔════❰ ʙᴏᴛ sᴛᴀᴛᴜs  ❱═❍⊱❁
║╭━━━━━━━━━━━━━━━➣
║┣⪼👱 ᴛᴏᴛᴀʟ  ᴜsᴇʀs : <code>{}</code>
║┃
║┣⪼🤖 ᴛᴏᴛᴀʟ ʙᴏᴛs : <code>{}</code>
║┃
║┣⪼🔃 ғᴏʀᴡᴀʀᴅɪɴɢs : <code>{}</code>
║┃
║┣⪼🏷️ ᴄʜᴀɴɴᴇʟs : <code>{}</code>
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁</b>""" 

  SERVER_TXT = """<b>
╔════❰ sᴇʀᴠᴇʀ sᴛᴀᴛs  ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼ ᴄᴘᴜ: <code>{}%</code>
║┣⪼ ʀᴀᴍ: <code>{}%</code>
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪</b>"""
  
  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or send message link of source chat.\n/cancel - Cancel this process</b>"

  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose your target chat from the buttons below.\n/cancel - Cancel this process</b>"

  SKIP_MSG = "<b><u>sᴇᴛ ɴᴏ. ᴏғ ᴍᴇssᴀɢᴇs ᴛᴏ sᴋɪᴘ 📃</u></b>\n\n<b>You can skip a certain number of messages and forward the rest.\n\nDefault Skip Number = 0</b>\n\n<b><i>Example: If you enter 0, no messages will be skipped.\nIf you enter 5, the first 5 messages will be skipped.</i></b>\n/cancel <b>- Cancel this process</b>"

  CANCEL = "<b>Process Cancelled Successfully!</b>"

  BOT_DETAILS = "<b><u>📄 BOT DETAILS</u></b>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ BOT ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"

  USER_DETAILS = "<b><u>📄 USERBOT DETAILS</u></b>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ USER ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"  
         
  TEXT = """<b>╔════❰ ғᴏʀᴡᴀʀᴅ sᴛᴀᴛᴜs  ❱═❍⊱❁
║╭━━━━━━━━━━━━━━━➣
║┣⪼<b>𖨠 ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ғᴇᴛᴄʜᴇᴅ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ᴅᴇʟᴇᴛᴇᴅ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 sᴋɪᴘᴘᴇᴅ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ғɪʟᴛᴇʀᴇᴅ ᴍᴇssᴀɢᴇs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ᴄᴜʀʀᴇɴᴛ sᴛᴀᴛᴜs: </b> <code>{}</code>
║┃
║┣⪼<b>𖨠 ᴘᴇʀᴄᴇɴᴛᴀɢᴇ: </b> <code>{}</code>%
║╰━━━━━━━━━━━━━━━➣ 
╚════❰ <b>{}</b> ❱══❍⊱❁"""

  DUPLICATE_TEXT = """
╔════❰ ᴜɴᴇǫᴜɪғʏ sᴛᴀᴛᴜs ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼ <b>ғᴇᴛᴄʜᴇᴅ ғɪʟᴇs:</b> <code>{}</code>
║┃
║┣⪼ <b>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴅᴇʟᴇᴛᴇᴅ:</b> <code>{}</code> 
║╰━━━━━━━━━━━━━━━➣
╚════❰ {} ❱══❍⊱❁۪۪
"""

  DOUBLE_CHECK = """<b><u>ᴅᴏᴜʙʟᴇ ᴄʜᴇᴄᴋɪɴɢ 📋</u></b>

<b>ʙᴇꜰᴏʀᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ ᴛʜᴇ ᴍᴇssᴀɢᴇs ᴄʟɪᴄᴋ ᴛʜᴇ ʏᴇs ʙᴜᴛᴛᴏɴ ᴏɴʟʏ ᴀꜰᴛᴇʀ ᴄʜᴇᴄᴋɪɴɢ ᴛʜᴇ ꜰᴏʟʟᴏᴡɪɴɢ</b>

<b>★ ʏᴏᴜʀ ʙᴏᴛ: {botname}</b>
<b>★ sᴏᴜʀᴄᴇ ᴄʜᴀᴛ: {from_chat}</b>
<b>★ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ: {to_chat}</b>
<b>★ sᴋɪᴘ ᴍᴇssᴀɢᴇs: {skip}</b>

<i><b>° {botname} ᴍᴜsᴛ ʙᴇ ᴀᴅᴍɪɴ ɪɴ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ</b> ({to_chat})</i>
<i><b>° ɪꜰ ᴛʜᴇ sᴏᴜʀᴄᴇ ᴄʜᴀᴛ ɪs ᴘʀɪᴠᴀᴛᴇ ʏᴏᴜʀ ᴜsᴇʀʙᴏᴛ ᴍᴜsᴛ ʙᴇ ᴍᴇᴍʙᴇʀ ᴏʀ ʏᴏᴜʀ ʙᴏᴛ ᴍᴜsᴛ ʙᴇ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇʀᴇ ᴀʟsᴏ</b></i>

<b>ɪꜰ ᴛʜᴇ ᴀʙᴏᴠᴇ ɪs ᴄʜᴇᴄᴋᴇᴅ ᴛʜᴇɴ ᴛʜᴇ ʏᴇs ʙᴜᴛᴛᴏɴ ᴄᴀɴ ʙᴇ ᴄʟɪᴄᴋᴇᴅ</b>""" 