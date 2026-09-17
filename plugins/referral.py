import logging
from config import Config, temp
from database import db
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, CallbackQuery, Message
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, btn_url, row, markup, colored_markup

logger = logging.getLogger("SkinetReferral")

REDEEM_PERKS = [
    {
        "id": "extreme_speed",
        "title": "⚡️ Extreme Speed Pass (0.5s Turbo)",
        "cost": 20,
        "desc": "Unlocks 0.5s ultra-fast burst message forwarding.",
        "key": "speed_cfg",
        "val": {"mode": "extreme", "delay": 0.5, "jitter": True, "batch_size": 100}
    },
    {
        "id": "course_seller",
        "title": "🎓 Course Seller Pro Pass",
        "cost": 30,
        "desc": "Auto lecture numbering, index table of contents & ad cleaner.",
        "key": "course_seller_mode",
        "val": True
    },
    {
        "id": "ad_remover",
        "title": "🛠 Skinet Clean Sanitizer Pass",
        "cost": 15,
        "desc": "Custom text & link replace rules with automated ad stripper.",
        "key": "clean_caption",
        "val": True
    },
    {
        "id": "verify_bypass",
        "title": "🛡️ 7-Day VIP Verification Pass",
        "cost": 50,
        "desc": "Bypasses all token verification steps freely for 7 full days.",
        "key": "vip_pass_7d",
        "val": 7 * 86400
    }
]

def is_owner(user_id: int) -> bool:
    return bool(user_id and user_id in Config.BOT_OWNER_ID)

async def get_bot_username(client: Client) -> str:
    me = getattr(client, "me", None)
    if not me:
        me = await client.get_me()
    return getattr(me, "username", None) or "bot"

async def build_referral_text(client: Client, user_id: int):
    uname = await get_bot_username(client)
    ref_link = f"https://t.me/{uname}?start=ref_{user_id}"
    data = await db.get_referral_data(user_id)
    
    count = data.get("referral_count", 0)
    points = data.get("referral_points", 0)
    earned = data.get("referral_earned_total", 0)
    redeemed = data.get("referral_redeemed_total", 0)
    per_join = getattr(Config, "REFERRAL_POINTS_PER_JOIN", 10)
    welcome_bonus = getattr(Config, "REFERRAL_WELCOME_BONUS", 5)

    text = (
        "<blockquote><b>🎁 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʀᴇғᴇʀ & ᴇᴀʀɴ</u></b></blockquote>\n\n"
        "Invite your friends or channel subscribers and earn rewards for every user who joins!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>Your Personal Invite Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "🌟 <b>Benefits for You (The Referrer):</b>\n"
        f"• Earn <b>+{per_join} Points</b> instantly for every friend who joins.\n"
        "• Redeem points directly for Turbo Speed, Course Seller Mode, and VIP perks!\n\n"
        "🎉 <b>Benefits for Your Friends:</b>\n"
        f"• Every new friend joining via your link claims a <b>+{welcome_bonus} Points</b> welcome bonus.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Your Referral Statistics:</b>\n"
        f"• Total Friends Referred: <code>{count}</code>\n"
        f"• Available Points: <code>{points} pts</code>\n"
        f"• Lifetime Earned: <code>{earned} pts</code> | Redeemed: <code>{redeemed} pts</code>"
    )
    return text, ref_link, data

async def build_referral_keyboard(client: Client, user_id: int):
    uname = await get_bot_username(client)
    ref_link = f"https://t.me/{uname}?start=ref_{user_id}"
    data = await db.get_referral_data(user_id)
    
    buttons = []
    
    # Welcome bonus button if referred and not claimed
    if data.get("referred_by") and not data.get("bonus_claimed"):
        buttons.append([
            InlineKeyboardButton("🎁 ᴄʟᴀɪᴍ ᴡᴇʟᴄᴏᴍᴇ ʙᴏɴᴜs (+5 ᴘᴛs)", callback_data="referral#claim_bonus")
        ])
    
    # Redeem & Leaderboard
    buttons.append([
        InlineKeyboardButton("💎 ʀᴇᴅᴇᴇᴍ ᴘᴏɪɴᴛs", callback_data="referral#redeem"),
        InlineKeyboardButton("🏆 ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ", callback_data="referral#leaderboard")
    ])
    
    # 1-Tap Share URL
    share_msg = f"Join Skinet Verse Forward Bot - The fastest channel cloning and course distribution suite! Click here: {ref_link}"
    import urllib.parse
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_msg)}"
    
    buttons.append([
        InlineKeyboardButton("🔗 sʜᴀʀᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ", url=share_url)
    ])
    
    if is_owner(user_id):
        buttons.append([
            InlineKeyboardButton("👑 ʀᴇғᴇʀʀᴀʟ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", callback_data="referral#admin")
        ])
        
    buttons.append([
        InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ", callback_data="back")
    ])
    return InlineKeyboardMarkup(buttons)


# ================= COMMANDS =================

@Client.on_message(filters.private & filters.command(["referral", "refer", "earn"]))
async def referral_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    text, _, _ = await build_referral_text(client, user_id)
    reply_markup = await build_referral_keyboard(client, user_id)
    await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command(["topref", "leaderboard"]))
async def topref_cmd(client: Client, message: Message):
    leaders = await db.get_top_referrers(limit=10)
    lines = ["<b>🏆 <u>ᴛᴏᴘ 10 ʀᴇғᴇʀʀᴀʟ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ</u></b>\n"]
    if not leaders:
        lines.append("<i>No referrals recorded yet. Be the first to invite!</i>")
    else:
        medals = ["🥇", "🥈", "🥉"] + [f"<b>#{i+1}</b>" for i in range(3, 10)]
        for i, doc in enumerate(leaders):
            ref = doc.get("referral", {})
            name = doc.get("name", str(doc.get("id")))
            count = ref.get("referral_count", 0)
            pts = ref.get("referral_points", 0)
            lines.append(f"{medals[i]} <b>{name}</b> — <code>{count} invites</code> ({pts} pts)")
    
    lines.append("\n<i>💡 Invite friends using /referral to climb the ranks!</i>")
    await message.reply_text("\n".join(lines), disable_web_page_preview=True)

@Client.on_message(filters.private & filters.command(["refadmin"]) & filters.user(Config.BOT_OWNER_ID))
async def refadmin_cmd(client: Client, message: Message):
    ledger = await db.get_referral_ledger(limit=10)
    leaders = await db.get_top_referrers(limit=5)
    
    text = (
        "👑 <b><u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʀᴇғᴇʀʀᴀʟ ᴀᴅᴍɪɴ ᴅᴀsʜʙᴏᴀʀᴅ</u></b>\n\n"
        f"⚙️ <b>Points per Join:</b> <code>{getattr(Config, 'REFERRAL_POINTS_PER_JOIN', 10)} pts</code>\n"
        f"🎁 <b>Welcome Bonus:</b> <code>{getattr(Config, 'REFERRAL_WELCOME_BONUS', 5)} pts</code>\n\n"
        "<b>🏆 Top 5 Referrers:</b>\n"
    )
    for i, doc in enumerate(leaders):
        ref = doc.get("referral", {})
        text += f"• <code>{doc.get('id')}</code> ({doc.get('name', 'User')}): <b>{ref.get('referral_count', 0)}</b> invites ({ref.get('referral_points', 0)} pts)\n"
    
    text += "\n<b>📜 Recent Ledger Events:</b>\n"
    if not ledger:
        text += "<i>No recent events.</i>\n"
    else:
        for ev in ledger:
            text += f"• <code>[{ev.get('time', '')}]</code> {ev.get('type', '').upper()} | User: <code>{ev.get('user_id')}</code> | {ev.get('points', 0)} pts ({ev.get('detail', '')})\n"
            
    text += "\n👇 <i>Choose an action below:</i>"
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ᴀᴅᴅ ᴘᴏɪɴᴛs ᴛᴏ ᴜsᴇʀ", callback_data="referral#admin_add")],
        [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ʀᴇғᴇʀʀᴀʟ", callback_data="referral#main")]
    ])
    await message.reply_text(text, reply_markup=buttons, disable_web_page_preview=True)


# ================= CALLBACK QUERIES =================

@Client.on_callback_query(filters.regex(r"^referral"))
async def referral_callbacks(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data.split("#")[1] if "#" in query.data else "main"

    if data == "main":
        text, _, _ = await build_referral_text(client, user_id)
        reply_markup = await build_referral_keyboard(client, user_id)
        await query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)

    elif data == "claim_bonus":
        success, res = await db.claim_welcome_bonus(user_id)
        if success:
            await query.answer(f"🎉 Welcome bonus claimed! You received +{res} points!", show_alert=True)
        else:
            await query.answer(f"⚠️ {res}", show_alert=True)
        text, _, _ = await build_referral_text(client, user_id)
        reply_markup = await build_referral_keyboard(client, user_id)
        await query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)

    elif data == "leaderboard":
        leaders = await db.get_top_referrers(limit=10)
        lines = ["<b>🏆 <u>ᴛᴏᴘ 10 ʀᴇғᴇʀʀᴀʟ ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ</u></b>\n"]
        if not leaders:
            lines.append("<i>No referrals recorded yet. Be the first to invite!</i>")
        else:
            medals = ["🥇", "🥈", "🥉"] + [f"<b>#{i+1}</b>" for i in range(3, 10)]
            for i, doc in enumerate(leaders):
                ref = doc.get("referral", {})
                name = doc.get("name", str(doc.get("id")))
                count = ref.get("referral_count", 0)
                pts = ref.get("referral_points", 0)
                lines.append(f"{medals[i]} <b>{name}</b> — <code>{count} invites</code> ({pts} pts)")
        
        lines.append("\n<i>💡 Invite friends using /referral to climb the ranks!</i>")
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="referral#main")]])
        await query.message.edit_text("\n".join(lines), reply_markup=buttons, disable_web_page_preview=True)

    elif data == "redeem":
        ref_data = await db.get_referral_data(user_id)
        points = ref_data.get("referral_points", 0)
        
        lines = [
            "💎 <b><u>ʀᴇᴅᴇᴇᴍ ʏᴏᴜʀ ʀᴇғᴇʀʀᴀʟ ᴘᴏɪɴᴛs</u></b> 💎\n",
            f"Your Balance: <b>{points} Points</b>\n",
            "Select any plan or pass below to unlock immediately:\n"
        ]
        
        buttons = []
        for perk in REDEEM_PERKS:
            afford = "✅" if points >= perk["cost"] else "🔒"
            lines.append(f"{afford} <b>{perk['title']}</b> — <code>{perk['cost']} pts</code>\n  └ <i>{perk['desc']}</i>\n")
            buttons.append([
                InlineKeyboardButton(
                    f"{afford} {perk['title']} ({perk['cost']} pts)",
                    callback_data=f"referral#buy_{perk['id']}"
                )
            ])
            
        buttons.append([InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="referral#main")])
        await query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif data.startswith("buy_"):
        perk_id = data.replace("buy_", "")
        perk = next((p for p in REDEEM_PERKS if p["id"] == perk_id), None)
        if not perk:
            return await query.answer("Perk not found!", show_alert=True)
            
        ref_data = await db.get_referral_data(user_id)
        points = ref_data.get("referral_points", 0)
        
        if points < perk["cost"]:
            return await query.answer(
                f"❌ Not enough points! You need {perk['cost']} pts but have {points} pts.\nInvite friends with /referral to earn more!",
                show_alert=True
            )
            
        confirm_text = (
            "💎 <b><u>ᴄᴏɴғɪʀᴍ ʀᴇᴅᴇᴍᴘᴛɪᴏɴ</u></b>\n\n"
            f"Perk: <b>{perk['title']}</b>\n"
            f"Description: <i>{perk['desc']}</i>\n"
            f"Cost: <b>{perk['cost']} Points</b>\n"
            f"Your Balance: <b>{points} pts</b> ➔ <b>{points - perk['cost']} pts</b> after redemption\n\n"
            "Do you want to confirm this unlock?"
        )
        buttons = [
            [InlineKeyboardButton("✅ ᴄᴏɴғɪʀᴍ & ᴜɴʟᴏᴄᴋ", callback_data=f"referral#conf_{perk_id}")],
            [InlineKeyboardButton("• ᴄᴀɴᴄᴇʟ", callback_data="referral#redeem")]
        ]
        await query.message.edit_text(confirm_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif data.startswith("conf_"):
        perk_id = data.replace("conf_", "")
        perk = next((p for p in REDEEM_PERKS if p["id"] == perk_id), None)
        if not perk:
            return await query.answer("Perk not found!", show_alert=True)
            
        success, res = await db.redeem_referral_points(user_id, perk["cost"], perk["title"])
        if not success:
            return await query.answer(f"⚠️ {res}", show_alert=True)
            
        # Apply the perk to user configurations in database
        configs = await db.get_configs(user_id)
        if perk["key"] == "all_vip":
            configs['speed_cfg'] = {"mode": "extreme", "delay": 0.5, "jitter": True, "batch_size": 100}
            configs['course_seller_mode'] = True
            configs['auto_course_list'] = True
            configs['auto_numbering'] = True
            configs['username_remover'] = True
            configs['link_remover'] = True
            configs['clean_caption'] = True
            configs['autosave_unlocked'] = True
        elif perk["key"] == "speed_cfg":
            configs['speed_cfg'] = perk["val"]
        elif perk["key"] == "course_seller_mode":
            configs['course_seller_mode'] = True
            configs['auto_course_list'] = True
            configs['auto_numbering'] = True
        elif perk["key"] == "autosave_unlocked":
            configs['autosave_unlocked'] = True
            
        await db.update_configs(user_id, configs)
        await query.answer("🎉 Perk unlocked successfully!", show_alert=True)
        
        success_text = (
            "✅ <b><u>ʀᴇᴅᴇᴍᴘᴛɪᴏɴ sᴜᴄᴄᴇssғᴜʟ!</u></b> 🎉\n\n"
            f"Unlocked: <b>{perk['title']}</b>\n"
            f"Deducted: <b>{perk['cost']} Points</b>\n"
            f"Remaining Balance: <b>{res} Points</b>\n\n"
            "<i>Your new privileges are active immediately! Check /settings to view your updated parameters.</i>"
        )
        buttons = [
            [InlineKeyboardButton("⚙️ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs", callback_data="settings#main")],
            [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ʀᴇғᴇʀʀᴀʟ", callback_data="referral#main")]
        ]
        await query.message.edit_text(success_text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif data == "admin":
        if not is_owner(user_id):
            return await query.answer("Admins only!", show_alert=True)
        leaders = await db.get_top_referrers(limit=5)
        ledger = await db.get_referral_ledger(limit=5)
        text = (
            "👑 <b><u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ʀᴇғᴇʀʀᴀʟ ᴀᴅᴍɪɴ</u></b>\n\n"
            "<b>Top 5 Referrers:</b>\n"
        )
        for doc in leaders:
            ref = doc.get("referral", {})
            text += f"• <code>{doc.get('id')}</code>: <b>{ref.get('referral_count', 0)}</b> invites ({ref.get('referral_points', 0)} pts)\n"
        text += "\n<b>Recent Events:</b>\n"
        for ev in ledger:
            text += f"• <code>{ev.get('user_id')}</code>: {ev.get('points', 0)} pts ({ev.get('detail', '')})\n"
            
        buttons = [
            [InlineKeyboardButton("➕ ᴀᴅᴅ ᴘᴏɪɴᴛs ᴛᴏ ᴜsᴇʀ", callback_data="referral#admin_add")],
            [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="referral#main")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

    elif data == "admin_add":
        if not is_owner(user_id):
            return await query.answer("Admins only!", show_alert=True)
        await query.message.delete()
        ask = await client.ask(
            user_id,
            text="<b>👑 Send User ID and points to add:</b>\nFormat: <code>user_id:points</code> (e.g. <code>123456789:50</code>)\n/cancel - Abort",
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel") or ":" not in ask.text:
            return await client.send_message(user_id, "Process cancelled or invalid format.")
            
        parts = ask.text.strip().split(":", 1)
        try:
            target_id = int(parts[0].strip())
            grant_pts = int(parts[1].strip())
        except ValueError:
            return await client.send_message(user_id, "❌ Invalid numbers!")
            
        ref_data = await db.get_referral_data(target_id)
        ref_data['referral_points'] = ref_data.get('referral_points', 0) + grant_pts
        ref_data['referral_earned_total'] = ref_data.get('referral_earned_total', 0) + max(0, grant_pts)
        await db.update_referral_data(target_id, ref_data)
        await db.log_referral_event('admin_grant', target_id, grant_pts, f"Admin {user_id} manual grant")
        
        try:
            await client.send_message(
                target_id,
                f"🎁 <b>Admin Grant:</b> You received <b>+{grant_pts} Referral Points</b> from the bot owner!\nCheck /referral."
            )
        except Exception:
            pass
            
        await client.send_message(
            user_id,
            f"✅ Successfully granted <b>+{grant_pts} points</b> to User <code>{target_id}</code>!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="referral#admin")]])
        )
