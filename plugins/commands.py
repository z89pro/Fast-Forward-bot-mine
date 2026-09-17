import os
import sys
import asyncio 
import datetime
try:
    import psutil
except ImportError:
    psutil = None
from pyrogram.types import Message
from database import db, mongodb_version
from config import Config, temp
from platform import python_version
from translation import Translation
from pyrogram import Client, filters, enums, __version__ as pyrogram_version
def get_main_buttons(user_id=None):
    is_admin = bool(user_id and user_id in Config.BOT_OWNER_ID)
    buttons = [
        [
            InlineKeyboardButton('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', callback_data='autosave#main'),
            InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs', callback_data='settings#main')
        ],
        [
            InlineKeyboardButton('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', callback_data='tutorial#menu'),
            InlineKeyboardButton('🎁 ʀᴇғᴇʀ & ᴇᴀʀɴ', callback_data='referral#main')
        ],
        [
            InlineKeyboardButton('🛡️ ᴠᴇʀɪғʏ ᴘᴀss', callback_data='verify_menu_btn'),
            InlineKeyboardButton('📊 sᴛᴀᴛᴜs', callback_data='status')
        ],
        [
            InlineKeyboardButton('ℹ️ ᴀʙᴏᴜᴛ', callback_data='about')
        ]
    ]
    if is_admin:
        buttons.append([
            InlineKeyboardButton('📈 ᴜsᴇʀ ᴛʀᴀᴄᴋɪɴɢ', callback_data='utr_overview'),
            InlineKeyboardButton('⚙️ sʏsᴛᴇᴍ ᴄᴏɴғɪɢ', callback_data='config#main')
        ])
    return InlineKeyboardMarkup(buttons)

main_buttons = get_main_buttons()

#===================Start Function===================#

@Client.on_message(filters.private & filters.command(['start']))
async def start(client, message):
    user = message.from_user

    # Verification token deep-link: /start vrf_{token} or /start verify_{token}
    if len(message.command) > 1 and (message.command[1].startswith("verify_") or message.command[1].startswith("vrf_")):
        try:
            from plugins.verify import handle_verify_callback
            handled = await handle_verify_callback(client, message, message.command[1])
            if handled:
                return
        except Exception:
            pass

    if Config.FORCE_SUB_ON and Config.FORCE_SUB_CHANNEL:
        try:
            member = await client.get_chat_member(Config.FORCE_SUB_CHANNEL, user.id)
            if member.status in [enums.ChatMemberStatus.BANNED, "kicked"]:
                await client.send_message(
                    chat_id=message.chat.id,
                    text="You are banned from using this bot.",
                )
                return
        except Exception:
            channel_url = Config.FORCE_SUB_CHANNEL if Config.FORCE_SUB_CHANNEL.startswith("http") else f"https://t.me/{Config.FORCE_SUB_CHANNEL.lstrip('@')}"
            join_button = [
                [InlineKeyboardButton("ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=channel_url)],
                [InlineKeyboardButton("↻ ᴛʀʏ ᴀɢᴀɪɴ", url=f"https://t.me/{client.username}?start=start")]
            ]
            await client.send_message(
                chat_id=message.chat.id,
                text="ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.",
                reply_markup=InlineKeyboardMarkup(join_button)
            )
            return

    # Parse referral payload if present (/start ref_123456)
    ref_id = None
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        try:
            parsed_ref = int(message.command[1].replace("ref_", ""))
            if parsed_ref != user.id:
                ref_id = parsed_ref
        except Exception:
            ref_id = None

    is_new = not await db.is_user_exist(user.id)
    if is_new:
        await db.add_user(user.id, message.from_user.mention, referred_by=ref_id)
        if ref_id:
            credited, pts = await db.handle_referral_join(user.id, ref_id)
            if credited:
                try:
                    await client.send_message(
                        ref_id,
                        f"🎉 <b>New Referral Joined!</b>\n\n"
                        f"👤 <b>{user.mention}</b> joined Skinet Verse using your invite link!\n"
                        f"💎 You earned <b>+{pts} Referral Points</b>!\n\n"
                        f"Check your balance and redeem perks in /referral."
                    )
                except Exception:
                    pass
        if Config.LOG_CHANNEL:
            try:
                ref_txt = f"\n🔗 Rᴇғᴇʀʀᴇᴅ Bʏ: <code>{ref_id}</code>" if ref_id else ""
                await client.send_message(
                    chat_id=Config.LOG_CHANNEL,
                    text=f"#NewUser\n\nIᴅ - {user.id}\nNᴀᴍᴇ - {message.from_user.mention}{ref_txt}"
                )
            except Exception:
                pass
    else:
        await db.touch_user(user.id, message.from_user.mention)

    reply_markup = get_main_buttons(user.id)
    extra_welcome = "\n\n🎁 <i>You joined via an invite link! Claim your welcome bonus in /referral!</i>" if (is_new and ref_id) else ""
    await client.send_message(
        chat_id=message.chat.id,
        reply_markup=reply_markup,
        text=Translation.START_TXT.format(message.from_user.first_name) + extra_welcome)

#==================Restart Function==================#

@Client.on_message(filters.private & filters.command(['restart']) & filters.user(Config.BOT_OWNER_ID))
async def restart(client, message):
    msg = await message.reply_text(
        text="<i>ᴛʀʏɪɴɢ ᴛᴏ ʀᴇsᴛᴀʀᴛ...</i>"
    )
    await asyncio.sleep(5)
    await msg.edit("<i>sᴇʀᴠᴇʀ ʀᴇsᴛᴀʀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ✅</i>")
    os.execl(sys.executable, sys.executable, *sys.argv)
    
#==================Help Command==================#

@Client.on_message(filters.private & filters.command(['help']))
async def help_command(client, message):
    await client.send_message(
        chat_id=message.chat.id,
        text=Translation.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[
            InlineKeyboardButton('• ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='how_to_use'),
            InlineKeyboardButton('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', callback_data='tutorial#menu')
            ],[
            InlineKeyboardButton('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', callback_data='autosave#main'),
            InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ', callback_data='settings#main')
            ],[
            InlineKeyboardButton('• sᴛᴀᴛᴜs ', callback_data='status'),
            InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about')
            ],[
            InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='back')
            ]]
        )
    )

#==================Callback Functions==================#

@Client.on_callback_query(filters.regex(r'^help'))
async def helpcb(bot, query):
    await query.message.edit_text(
        text=Translation.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[
            InlineKeyboardButton('• ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='how_to_use'),
            InlineKeyboardButton('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', callback_data='tutorial#menu')
            ],[
            InlineKeyboardButton('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', callback_data='autosave#main'),
            InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ', callback_data='settings#main')
            ],[
            InlineKeyboardButton('• sᴛᴀᴛᴜs ', callback_data='status'),
            InlineKeyboardButton('• ᴀʙᴏᴜᴛ', callback_data='about')
            ],[
            InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='back')
            ]]
        ))

@Client.on_callback_query(filters.regex(r'^how_to_use'))
async def how_to_use(bot, query):
    await query.message.edit_text(
        text=Translation.HOW_USE_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('📚 ᴏᴘᴇɴ ꜰᴜʟʟ ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', callback_data='tutorial#menu')],
            [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='help')]
        ]),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r'^back'))
async def back(bot, query):
    reply_markup = get_main_buttons(query.from_user.id)
    await query.message.edit_text(
       reply_markup=reply_markup,
       text=Translation.START_TXT.format(
                query.from_user.first_name))

@Client.on_callback_query(filters.regex(r'^about'))
async def about(bot, query):
    await query.message.edit_text(
        text=Translation.ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='back')]]),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
    )

@Client.on_callback_query(filters.regex(r'^donate'))
async def donate(bot, query):
    await query.message.edit_text(
        text=Translation.DONATE_TXT,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='back')]]),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
    )

START_TIME = datetime.datetime.now()

# Function to calculate and format bot uptime
def format_uptime():
    uptime = datetime.datetime.now() - START_TIME
    total_seconds = uptime.total_seconds()

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    uptime_components = []
    if int(days) > 0:
        uptime_components.append(f"{int(days)} D")
    if int(hours) > 0:
        uptime_components.append(f"{int(hours)} H")
    if int(minutes) > 0:
        uptime_components.append(f"{int(minutes)} M")
    if int(seconds) > 0:
        uptime_components.append(f"{int(seconds)} Sec")

    uptime_str = ', '.join(uptime_components) if uptime_components else "0 Sec"
    return uptime_str

@Client.on_callback_query(filters.regex(r'^status'))
async def status(bot, query):
    users_count, bots_count = await db.total_users_bots_count()
    total_channels = await db.total_channels()

    # Calculate bot uptime
    uptime_str = format_uptime()

    await query.message.edit_text(
        text=Translation.STATUS_TXT.format(users_count, bots_count, temp.forwardings, total_channels),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='help'),
             InlineKeyboardButton('• sᴇʀᴠᴇʀ sᴛᴀᴛs', callback_data='server_status')
]]),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )

@Client.on_callback_query(filters.regex(r'^server_status'))
async def server_status(bot, query):
    ram = psutil.virtual_memory().percent if psutil else "N/A"
    cpu = psutil.cpu_percent() if psutil else "N/A"

    await query.message.edit_text(
        text=Translation.SERVER_TXT.format(cpu, ram),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='status')]]),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )

#===================Donate Function===================#

@Client.on_message(filters.private & filters.command(['donate']))
async def donate_cmd(client, message):
    await message.reply_text(
        text=Translation.DONATE_TXT
    )

#===================Clone Command===================#

@Client.on_message(filters.private & filters.command(['clone']))
async def clone_cmd(client, message):
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if not _bot:
        return await message.reply_text("<b>❌ Please add a bot or login a UserBot in /settings first!</b>")
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("<b>❌ Please set a target channel in /settings first!</b>")
    await message.reply_text(
        "<b>⚡ <u>Channel Cloning Guide:</u></b>\n\n"
        "To forward or clone messages from a source channel to your target:\n"
        "• Use <code>/forward</code> for interactive wizard\n"
        "• Use <code>/fwd &lt;start_link&gt; &lt;end_link&gt;</code> for direct range forward\n"
        "• Use <code>/autosave</code> to automatically monitor channels in real-time.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings#main"),
             InlineKeyboardButton("🚀 AutoSave", callback_data="autosave#main")]
        ])
    )

#===================Verify Menu Callback===================#

@Client.on_callback_query(filters.regex(r'^verify_menu_btn'))
async def verify_menu_callback(bot, query):
    user_id = query.from_user.id
    from plugins.verify import is_user_verified, send_verify_prompt, get_remaining_verify_time
    verified = await is_user_verified(user_id)
    if verified:
        rem_sec = get_remaining_verify_time(user_id)
        if rem_sec > 0:
            hrs = rem_sec // 3600
            mins = (rem_sec % 3600) // 60
            exp_text = f"{hrs}h {mins}m remaining"
        else:
            exp_text = "Permanent VIP / Admin Access"
        await query.answer(f"✅ Verified! ({exp_text})", show_alert=True)
    else:
        await query.answer()
        await send_verify_prompt(bot, query.message, user_id)

