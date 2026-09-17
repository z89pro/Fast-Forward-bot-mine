import html
import logging
from datetime import datetime, timedelta
from config import Config
from database import db
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

logger = logging.getLogger("SkinetUserTrack")

PAGE_SIZE = 8

def is_owner(user_id: int) -> bool:
    return bool(user_id and user_id in Config.BOT_OWNER_ID)

def fmt_dt(dt):
    if not dt:
        return "—"
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        return "—"

async def build_userstats_overview():
    cursor = db.col.find({})
    users = [doc async for doc in cursor]
    now = datetime.now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    total = len(users)
    new_today = 0
    new_week = 0
    act_today = 0
    act_week = 0
    total_forwards = 0

    for doc in users:
        total_forwards += int(doc.get("forward_count", 0))
        fs = doc.get("first_seen")
        ls = doc.get("last_seen")
        if fs:
            try:
                if isinstance(fs, str): fs = datetime.fromisoformat(fs)
                if fs >= day_ago: new_today += 1
                if fs >= week_ago: new_week += 1
            except Exception: pass
        if ls:
            try:
                if isinstance(ls, str): ls = datetime.fromisoformat(ls)
                if ls >= day_ago: act_today += 1
                if ls >= week_ago: act_week += 1
            except Exception: pass

    growth_pct = (new_week / max(1, total)) * 100

    text = (
        "<blockquote><b>📊 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴜsᴇʀ ᴛʀᴀᴄᴋɪɴɢ ᴅᴀsʜʙᴏᴀʀᴅ</u></b></blockquote>\n\n"
        "<b>Comprehensive analytics & real-time telemetry over your bot's userbase:</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Registered Users:</b> <code>{total}</code>\n"
        f"🔁 <b>Total Messages Forwarded:</b> <code>{total_forwards}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆕 <b>New Users (24h):</b> <code>{new_today}</code>\n"
        f"📅 <b>New Users (7d):</b> <code>{new_week}</code>\n"
        f"🟢 <b>Active Users (24h):</b> <code>{act_today}</code>\n"
        f"⚡️ <b>Active Users (7d):</b> <code>{act_week}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>7-Day Growth Velocity:</b> <code>{growth_pct:.1f}%</code>\n\n"
        "<i>💡 Lookup any user profile:</i> <code>/userstats &lt;user_id&gt;</code>"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🕒 ɴᴇᴡ ᴜsᴇʀs", callback_data="utr_new_0"),
            InlineKeyboardButton("🟢 ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs", callback_data="utr_act_0")
        ],
        [
            InlineKeyboardButton("🎁 ʀᴇғᴇʀʀᴀʟ sᴛᴀᴛs", callback_data="referral#admin"),
            InlineKeyboardButton("⚙️ sʏsᴛᴇᴍ ᴄᴏɴғɪɢ", callback_data="config#main")
        ],
        [
            InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ", callback_data="back")
        ]
    ])
    return text, buttons

async def build_user_profile(user_id: int):
    user = await db.get_user(user_id)
    if not user:
        return f"<b>❌ User <code>{user_id}</code> not found in database.</b>", None

    name = html.escape(str(user.get("name", "User")))
    first_seen = fmt_dt(user.get("first_seen"))
    last_seen = fmt_dt(user.get("last_seen"))
    forwards = user.get("forward_count", 0)
    activity = user.get("activity_count", 1)
    
    ref = user.get("referral", {})
    referred_by = ref.get("referred_by") or "None (Direct)"
    ref_count = ref.get("referral_count", 0)
    ref_points = ref.get("referral_points", 0)
    
    channels = await db.get_user_channels(user_id)
    bot_info = await db.get_bot(user_id)
    bot_status = "✅ Connected" if bot_info else "❌ Not added"
    bot_type = "UserBot" if (bot_info and not bot_info.get("is_bot")) else ("Bot" if bot_info else "None")

    text = (
        f"<blockquote><b>👤 <u>ᴜsᴇʀ ᴘʀᴏғɪʟᴇ: {name}</u></b></blockquote>\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Name / Mention:</b> {name}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>First Seen:</b> <code>{first_seen}</code>\n"
        f"🕒 <b>Last Active:</b> <code>{last_seen}</code>\n"
        f"🔁 <b>Messages Forwarded:</b> <code>{forwards}</code>\n"
        f"⚡️ <b>Interaction Count:</b> <code>{activity}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot Engine:</b> <code>{bot_status} ({bot_type})</code>\n"
        f"🏷 <b>Configured Channels:</b> <code>{len(channels)}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Referred By:</b> <code>{referred_by}</code>\n"
        f"👥 <b>Invited Friends:</b> <code>{ref_count}</code>\n"
        f"💎 <b>Referral Points:</b> <code>{ref_points} pts</code>"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴘᴏɪɴᴛs", callback_data=f"utr_addpts_{user_id}"),
            InlineKeyboardButton("🔙 ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="utr_overview")
        ]
    ])
    return text, buttons


# ================= COMMANDS =================

@Client.on_message(filters.private & filters.command(["userstats", "track", "admintrack"]))
async def userstats_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return await message.reply_text(
            "⚠️ <b>Access Denied:</b> This analytics dashboard is strictly restricted to Bot Owners.",
            quote=True
        )

    # If specific user ID provided: /userstats <user_id>
    if len(message.command) > 1:
        raw_target = message.command[1].strip()
        if raw_target.isdigit():
            target_id = int(raw_target)
            text, buttons = await build_user_profile(target_id)
            return await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=True, quote=True)

    text, buttons = await build_userstats_overview()
    await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=True, quote=True)


# ================= CALLBACKS =================

@Client.on_callback_query(filters.regex(r"^utr_"))
async def utr_callbacks(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not is_owner(user_id):
        return await query.answer("Admins only!", show_alert=True)

    data = query.data

    if data == "utr_overview":
        text, buttons = await build_userstats_overview()
        await query.message.edit_text(text, reply_markup=buttons, disable_web_page_preview=True)

    elif data.startswith("utr_new_") or data.startswith("utr_act_"):
        is_new = data.startswith("utr_new_")
        page = int(data.split("_")[-1])
        cursor = db.col.find({})
        users = [doc async for doc in cursor]

        sort_key = "first_seen" if is_new else "last_seen"
        title = "🕒 <b><u>ɴᴇᴡ ᴜsᴇʀs ʟɪsᴛ</u></b>" if is_new else "🟢 <b><u>ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs ʟɪsᴛ</u></b>"
        prefix = "utr_new" if is_new else "utr_act"

        # Sort descending by date
        def sort_fn(x):
            val = x.get(sort_key)
            if not val: return datetime.min
            if isinstance(val, str):
                try: return datetime.fromisoformat(val)
                except Exception: return datetime.min
            return val

        users.sort(key=sort_fn, reverse=True)

        total_pages = max(1, (len(users) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        chunk = users[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

        lines = [
            f"<blockquote>{title}</blockquote>\n",
            f"<b>Total Users:</b> <code>{len(users)}</code> | Page <b>{page+1}/{total_pages}</b>\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        item_buttons = []
        for u in chunk:
            uid = u.get("id")
            name = html.escape(str(u.get("name", "User"))[:18])
            date_val = fmt_dt(u.get(sort_key))
            lines.append(f"• <b>{name}</b> (<code>{uid}</code>)\n  └ <i>{date_val}</i> | Forwards: <code>{u.get('forward_count', 0)}</code>")
            item_buttons.append([InlineKeyboardButton(f"👤 View {name}", callback_data=f"utr_user_{uid}")])

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Pager row
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"{prefix}_{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1} / {total_pages}", callback_data="utr_noop"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"{prefix}_{page + 1}"))

        markup_rows = item_buttons + [nav_row, [InlineKeyboardButton("🔙 ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="utr_overview")]]
        await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(markup_rows), disable_web_page_preview=True)

    elif data.startswith("utr_user_"):
        target_id = int(data.replace("utr_user_", ""))
        text, buttons = await build_user_profile(target_id)
        await query.message.edit_text(text, reply_markup=buttons, disable_web_page_preview=True)

    elif data.startswith("utr_addpts_"):
        target_id = int(data.replace("utr_addpts_", ""))
        await query.message.delete()
        ask = await client.ask(
            user_id,
            text=f"<b>👑 Send points to add to User <code>{target_id}</code>:</b>\n(e.g. <code>25</code>)\n/cancel - Abort",
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel") or not ask.text.strip().isdigit():
            return await client.send_message(user_id, "Process cancelled or invalid number.")
        
        pts = int(ask.text.strip())
        ref_data = await db.get_referral_data(target_id)
        ref_data['referral_points'] = ref_data.get('referral_points', 0) + pts
        ref_data['referral_earned_total'] = ref_data.get('referral_earned_total', 0) + pts
        await db.update_referral_data(target_id, ref_data)
        await db.log_referral_event('admin_grant', target_id, pts, f"Owner {user_id} grant via userstats")

        try:
            await client.send_message(
                target_id,
                f"🎁 <b>Admin Bonus:</b> You have been granted <b>+{pts} Referral Points</b> by the administrator!\nCheck /referral."
            )
        except Exception:
            pass

        await client.send_message(
            user_id,
            f"✅ Granted <b>+{pts} points</b> to User <code>{target_id}</code>!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 View Profile", callback_data=f"utr_user_{target_id}")]])
        )

    elif data == "utr_noop":
        await query.answer()
