import os
import sys
import asyncio 
import datetime
try:
    import psutil
except ImportError:
    psutil = None
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from buttons import btn, btn_url, row, markup, colored_markup
from database import db, mongodb_version
from config import Config, temp
from platform import python_version
from translation import Translation
from pyrogram import Client, filters, enums, __version__ as pyrogram_version

def get_main_buttons(user_id=None):
    is_admin = bool(user_id and user_id in Config.BOT_OWNER_ID)
    rows = [
        row(
            btn('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', 'autosave#main', 'green'),
            btn('⚙️ sᴇᴛᴛɪɴɢs', 'settings#main', 'blue')
        ),
        row(
            btn('💎 ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ', 'prem_plans', 'green'),
            btn('🎁 ʀᴇғᴇʀ & ᴇᴀʀɴ', 'referral#main', 'blue')
        ),
        row(
            btn('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', 'tutorial#menu', 'blue'),
            btn('🛡️ ᴠᴇʀɪғʏ ᴘᴀss', 'verify_menu_btn', 'green')
        ),
        row(
            btn('📊 sᴛᴀᴛᴜs', 'status', 'blue'),
            btn('ℹ️ ᴀʙᴏᴜᴛ', 'about', 'blue')
        )
    ]
    if is_admin:
        rows.append(row(
            btn('📈 ᴜsᴇʀ ᴛʀᴀᴄᴋɪɴɢ', 'utr_overview', 'blue'),
            btn('⚙️ sʏsᴛᴇᴍ ᴄᴏɴғɪɢ', 'config#main', 'green')
        ))
    return markup(*rows)

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
    await message.reply_text(
        text=Translation.START_TXT.format(message.from_user.first_name) + extra_welcome,
        reply_markup=reply_markup,
        quote=True
    )

#==================Restart Function==================#

@Client.on_message(filters.private & filters.command(['restart', 'reboot']))
async def restart(client, message):
    user_id = message.from_user.id
    if not await db.is_admin(user_id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> This command is restricted to Bot Administrators.", quote=True)

    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    stamp = datetime.now(ist).strftime("%d-%b-%Y %I:%M:%S %p")
    user_name = message.from_user.first_name or "Admin"

    msg = await message.reply_text(
        text=Translation.RESTART_TXT.format(user_name, stamp),
        quote=True
    )
    try:
        await db.set_restart_status(message.chat.id, msg.id)
    except Exception:
        pass
    try:
        import json
        with open('.restart_status.json', 'w') as f:
            json.dump({'chat_id': message.chat.id, 'message_id': msg.id}, f)
    except Exception:
        pass
    await asyncio.sleep(1.5)
    os.execl(sys.executable, sys.executable, *sys.argv)
    
def get_help_buttons():
    return markup(
        row(
            btn('📖 ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ', 'how_to_use', 'blue'),
            btn('📚 ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', 'tutorial#menu', 'blue')
        ),
        row(
            btn('🚀 sᴍᴀʀᴛ ᴀᴜᴛᴏsᴀᴠᴇ', 'autosave#main', 'green'),
            btn('⚙️ sᴇᴛᴛɪɴɢs', 'settings#main', 'blue')
        ),
        row(
            btn('📊 sᴛᴀᴛᴜs', 'status', 'blue'),
            btn('ℹ️ ᴀʙᴏᴜᴛ', 'about', 'blue')
        ),
        row(
            btn('📜 ᴛᴇʀᴍs', 'terms_btn', 'blue'),
            btn('🔒 ᴘʀɪᴠᴀᴄʏ', 'privacy_btn', 'blue')
        ),
        row(
            btn('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', 'back', 'red')
        )
    )

#==================Help Command==================#

@Client.on_message(filters.private & filters.command(['help']))
async def help_command(client, message):
    await message.reply_text(
        text=Translation.HELP_TXT,
        reply_markup=get_help_buttons(),
        quote=True
    )

#==================Terms & Privacy Commands==================#

@Client.on_message(filters.private & filters.command(['terms', 'tos']))
async def terms_command(client, message):
    await message.reply_text(
        text=Translation.TERMS_TXT,
        reply_markup=markup(
            row(btn('🔒 ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ', 'privacy_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', 'back', 'red'))
        ),
        disable_web_page_preview=True,
        quote=True
    )

@Client.on_message(filters.private & filters.command(['privacy']))
async def privacy_command(client, message):
    await message.reply_text(
        text=Translation.PRIVACY_TXT,
        reply_markup=markup(
            row(btn('📜 ᴛᴇʀᴍs ᴏғ sᴇʀᴠɪᴄᴇ', 'terms_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ', 'back', 'red'))
        ),
        disable_web_page_preview=True,
        quote=True
    )

#==================Callback Functions==================#

@Client.on_callback_query(filters.regex(r'^help'))
async def helpcb(bot, query):
    await query.message.edit_text(
        text=Translation.HELP_TXT,
        reply_markup=get_help_buttons()
    )

@Client.on_callback_query(filters.regex(r'^how_to_use'))
async def how_to_use(bot, query):
    await query.message.edit_text(
        text=Translation.HOW_USE_TXT,
        reply_markup=markup(
            row(btn('📚 ᴏᴘᴇɴ ꜰᴜʟʟ ᴛᴜᴛᴏʀɪᴀʟ ʜᴜʙ', 'tutorial#menu', 'green')),
            row(btn('🔙 ʙᴀᴄᴋ', 'help', 'red'))
        ),
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
        reply_markup=markup(
            row(
                btn('📜 ᴛᴇʀᴍs', 'terms_btn', 'blue'),
                btn('🔒 ᴘʀɪᴠᴀᴄʏ', 'privacy_btn', 'blue')
            ),
            row(btn('🔙 ʙᴀᴄᴋ', 'back', 'red'))
        ),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
    )

@Client.on_callback_query(filters.regex(r'^terms_btn'))
async def terms_cb(bot, query):
    await query.message.edit_text(
        text=Translation.TERMS_TXT,
        reply_markup=markup(
            row(btn('🔒 ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ', 'privacy_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ', 'about', 'red'))
        ),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r'^privacy_btn'))
async def privacy_cb(bot, query):
    await query.message.edit_text(
        text=Translation.PRIVACY_TXT,
        reply_markup=markup(
            row(btn('📜 ᴛᴇʀᴍs ᴏғ sᴇʀᴠɪᴄᴇ', 'terms_btn', 'blue')),
            row(btn('🔙 ʙᴀᴄᴋ', 'about', 'red'))
        ),
        disable_web_page_preview=True
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
        reply_markup=markup(
            row(
                btn('• ʙᴀᴄᴋ', 'help', 'red'),
                btn('• sᴇʀᴠᴇʀ sᴛᴀᴛs', 'server_status', 'blue')
            )
        ),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )

@Client.on_callback_query(filters.regex(r'^server_status'))
async def server_status(bot, query):
    ram = psutil.virtual_memory().percent if psutil else "N/A"
    cpu = psutil.cpu_percent() if psutil else "N/A"

    await query.message.edit_text(
        text=Translation.SERVER_TXT.format(cpu, ram),
        reply_markup=markup(row(btn('• ʙᴀᴄᴋ', 'status', 'red'))),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )

#===================Donate Function===================#

@Client.on_message(filters.private & filters.command(['donate']))
async def donate_cmd(client, message):
    await message.reply_text(
        text=Translation.DONATE_TXT,
        quote=True
    )

#===================Clone Command===================#

@Client.on_message(filters.private & filters.command(['clone']))
async def clone_cmd(client, message):
    user_id = message.from_user.id
    _bot = await db.get_bot(user_id)
    if not _bot:
        return await message.reply_text("<b>❌ Please add a bot or login a UserBot in /settings first!</b>", quote=True)
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("<b>❌ Please set a target channel in /settings first!</b>", quote=True)
    await message.reply_text(
        "<b>⚡ <u>ᴄʜᴀɴɴᴇʟ ᴄʟᴏɴɪɴɢ ɢᴜɪᴅᴇ:</u></b>\n\n"
        "ᴛᴏ ғᴏʀᴡᴀʀᴅ ᴏʀ ᴄʟᴏɴᴇ ᴍᴇssᴀɢᴇs ғʀᴏᴍ ᴀ sᴏᴜʀᴄᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ʏᴏᴜʀ ᴛᴀʀɢᴇᴛ:\n"
        "• ᴜsᴇ <code>/forward</code> ғᴏʀ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ ᴡɪᴢᴀʀᴅ\n"
        "• ᴜsᴇ <code>/fwd &lt;start_link&gt; &lt;end_link&gt;</code> ғᴏʀ ᴅɪʀᴇᴄᴛ ʀᴀɴɢᴇ ғᴏʀᴡᴀʀᴅ\n"
        "• ᴜsᴇ <code>/autosave</code> ᴛᴏ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴍᴏɴɪᴛᴏʀ ᴄʜᴀɴɴᴇʟs ɪɴ ʀᴇᴀʟ-ᴛɪᴍᴇ.",
        reply_markup=markup(
            row(
                btn("⚙️ sᴇᴛᴛɪɴɢs", "settings#main", "blue"),
                btn("📚 ᴛᴜᴛᴏʀɪᴀʟ", "tutorial#menu", "blue")
            )
        ),
        quote=True
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


#===================Non-Command & Unknown Message Handler===================#

KNOWN_COMMANDS = {
    "start", "help", "settings", "forward", "fwd", "autosave", "live", "monitor",
    "broadcast", "bcast", "cancelbroadcast", "bcastcancel", "broadcastrestart", "bcastrestart",
    "restart", "reboot", "terms", "tos", "privacy", "donate", "clone", "plans",
    "premium", "buy", "vip", "myplan", "plan", "addpremium", "addvip", "delpremium",
    "delvip", "referral", "refer", "earn", "topref", "leaderboard", "refadmin",
    "stop", "pause", "resume", "reset", "resetall", "tutorial", "guide", "skinet",
    "modifier", "ftm", "courseseller", "seller", "unequify", "userstats", "track",
    "admintrack", "verify", "setverify", "config", "env", "vars", "addadmin",
    "deladmin", "admins", "cancel", "yes", "no"
}

@Client.on_message(filters.private & ~filters.service, group=100)
async def non_command_handler(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id

    # 1. Skip if there is an active listener (like bot.ask) for this chat/user
    try:
        from pyrogram import enums
        if hasattr(client, "listeners") and isinstance(client.listeners, dict):
            msg_listeners = client.listeners.get(enums.ListenerTypes.MESSAGE, [])
            for l in msg_listeners:
                ident = getattr(l, "identifier", None)
                if ident:
                    c_id = getattr(ident, "chat_id", None)
                    u_id = getattr(ident, "from_user_id", None)
                    if (c_id and c_id == message.chat.id) or (u_id and u_id == user_id):
                        return
    except Exception:
        pass

    # 2. Skip if user is submitting payment proof
    try:
        from plugins.premium import _SUBMIT_STATE
        if user_id in _SUBMIT_STATE:
            return
    except Exception:
        pass

    raw_text = (message.text or message.caption or "").strip()

    # 3. Check if it's a known command -> let registered handlers execute
    if raw_text.startswith("/"):
        cmd_word = raw_text.split()[0].lstrip("/").split("@")[0].lower()
        if cmd_word in KNOWN_COMMANDS:
            return

        # Unknown command response
        return await message.reply_text(
            f"<blockquote><b>❓ <u>ᴜɴᴋɴᴏᴡɴ ᴄᴏᴍᴍᴀɴᴅ: /{cmd_word}</u></b></blockquote>\n\n"
            f"ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ <code>/{cmd_word}</code> ɪs ɴᴏᴛ ʀᴇᴄᴏɢɴɪᴢᴇᴅ ʙʏ sᴋɪɴᴇᴛ ᴠᴇʀsᴇ.\n\n"
            f"👉 ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ <code>/help</code> ᴛᴏ ᴠɪᴇᴡ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs!",
            quote=True,
            reply_markup=markup(
                row(btn("📖 ᴠɪᴇᴡ ᴄᴏᴍᴍᴀɴᴅs", "help", "blue"), btn("🔙 ʜᴏᴍᴇ", "back", "red"))
            )
        )

    # 4. Check if it's a link forward attempt
    if raw_text.startswith("https://t.me/") or raw_text.startswith("http://t.me/") or raw_text.startswith("t.me/"):
        return await message.reply_text(
            "<blockquote><b>🔗 <u>ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴅᴇᴛᴇᴄᴛᴇᴅ</u></b></blockquote>\n\n"
            "ᴛᴏ ғᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇs ᴜsɪɴɢ ʟɪɴᴋs, ᴜsᴇ ᴛʜᴇ <code>/fwd</code> ʀᴀɴɢᴇ ᴄᴏᴍᴍᴀɴᴅ:\n"
            "• <code>/fwd &lt;start_link&gt; &lt;end_link&gt;</code>\n\n"
            "ᴏʀ ʟᴀᴜɴᴄʜ ᴛʜᴇ ɪɴᴛᴇʀᴀᴄᴛɪᴠᴇ ғᴏʀᴡᴀʀᴅɪɴɢ ᴡɪᴢᴀʀᴅ ᴡɪᴛʜ <code>/forward</code>!",
            quote=True,
            reply_markup=markup(
                row(
                    btn("🚀 ʜᴏᴡ ᴛᴏ ғᴏʀᴡᴀʀᴅ", "how_to_use", "blue"),
                    btn("⚙️ sᴇᴛᴛɪɴɢs", "settings#main", "blue")
                )
            )
        )

    # 5. Friendly non-command response
    user_name = message.from_user.first_name if message.from_user else "Friend"
    reply_markup = get_main_buttons(user_id)

    await message.reply_text(
        text=(
            f"<blockquote><b>👋 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴀssɪsᴛᴀɴᴛ</u></b></blockquote>\n\n"
            f"👋 <b>ʜᴇʟʟᴏ, {user_name}!</b>\n\n"
            f"ɪ ᴀᴍ <b>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ</b>, ʏᴏᴜʀ ᴀᴜᴛᴏᴍᴀᴛᴇᴅ ᴍᴇᴅɪᴀ ᴍɪɢʀᴀᴛɪᴏɴ ᴀɴᴅ ᴄʜᴀɴɴᴇʟ ᴄʟᴏɴɪɴɢ ᴇɴɢɪɴᴇ.\n\n"
            f"💡 <b>ǫᴜɪᴄᴋ sᴛᴀʀᴛ:</b>\n"
            f"• <code>/start</code> — ᴏᴘᴇɴ ᴍᴀɪɴ ᴅᴀsʜʙᴏᴀʀᴅ\n"
            f"• <code>/forward</code> — ʟᴀᴜɴᴄʜ ғᴏʀᴡᴀʀᴅɪɴɢ ᴡɪᴢᴀʀᴅ\n"
            f"• <code>/autosave</code> — 24/7 ᴄʜᴀɴɴᴇʟ ᴍᴏɴɪᴛᴏʀ\n"
            f"• <code>/help</code> — ᴠɪᴇᴡ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs\n"
            f"• <code>/settings</code> — ᴄᴏɴғɪɢᴜʀᴇ ʙᴏᴛs & ᴄʜᴀɴɴᴇʟs\n\n"
            f"👇 <i>ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ:</i>"
        ),
        reply_markup=reply_markup,
        quote=True
    )

