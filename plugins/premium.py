"""
plugins/premium.py
──────────────────
Enterprise Premium & VIP Subscription System for Skinet Verse
Inspired by ZSRCBOT / Skinet-Src VIP architecture.

Features:
  1. Tiered VIP Plans (Starter, Pro Monthly, Ultra Lifetime)
  2. Direct UPI Intent & Dynamic 400x400 QR Code Generation
  3. Crypto & Direct Admin Fallback
  4. Manual UTR / Screenshot Proof Submission Workflow
  5. 1-Click Admin Approval & Rejection in LOG_CHANNEL / Owners
  6. Instant VIP Activation, Expiry Tracking & Verification Bypass
  7. /myplan, /plans, /addpremium, /delpremium Admin Management
"""

import os
import time
import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone, timedelta

from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from buttons import btn, btn_url, row, markup, colored_markup

from config import Config
from database import db

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# ── Plan Specifications ──────────────────────────────────────────────
PLANS = {
    "starter": {
        "id": "starter",
        "name": "🥉 Starter Pass",
        "tag": "Starter (7 Days)",
        "days": 7,
        "price": 49,
        "stars": 35,
        "speed": "1.0s (Fast)",
        "batch_limit": "500 msgs",
        "perks": [
            "⚡ 1.0s Fast Forwarding Speed",
            "🛡️ 0 Token Verification / Captcha Required",
            "📦 500 Messages Batch Forwarding",
            "🤖 1 UserBot / Bot Slot",
            "⏳ 7 Days Full VIP Access"
        ]
    },
    "pro": {
        "id": "pro",
        "name": "🥈 Pro Pass",
        "tag": "Pro Monthly (30 Days)",
        "days": 30,
        "price": 149,
        "stars": 110,
        "speed": "0.5s (Extreme Turbo)",
        "batch_limit": "Unlimited",
        "perks": [
            "⚡ 0.5s Extreme Turbo Speed",
            "🚀 Unlimited Batch Forwarding",
            "📡 Smart AutoSave 24/7 Channel Monitor",
            "🎓 Course Seller Mode & Auto Syllabus Index",
            "🛡️ 0 Verification Forever (Permanent Pass)",
            "🤖 Up to 3 Bot / UserBot Slots",
            "⏳ 30 Days Full VIP Access"
        ]
    },
    "ultra": {
        "id": "ultra",
        "name": "🥇 Ultra Lifetime Pass",
        "tag": "Ultra Lifetime (365 Days)",
        "days": 365,
        "price": 399,
        "stars": 290,
        "speed": "0.2s (Ultra Turbo)",
        "batch_limit": "Unlimited",
        "perks": [
            "⚡ 0.2s Ultra Turbo Speed",
            "🚀 Unlimited Everything & Dedicated Queue",
            "📦 Dedicated Stealth Dump Channel",
            "🎓 Full Course Seller Suite + Indexer",
            "🛡️ Permanent Verification Bypass",
            "🤖 10 UserBot Slots",
            "👑 Priority VIP Allocation & Direct Support",
            "⏳ 365 Days / Lifetime Validity"
        ]
    }
}

# In-memory conversational state: user_id -> {"order_id": str, "mode": "utr" | "screenshot"}
_SUBMIT_STATE = {}


def _get_admin_contact_link() -> str:
    contact = getattr(Config, "ADMIN_CONTACT", "").strip() or "@TheSkinet"
    if contact.startswith(("http://", "https://", "tg://")):
        return contact
    return f"https://t.me/{contact.lstrip('@')}"


def _format_time_ist(epoch: float) -> str:
    if not epoch:
        return "N/A"
    dt = datetime.fromtimestamp(epoch, tz=IST)
    return dt.strftime("%d-%b-%Y %I:%M %p")


def _build_qr_url(data_payload: str) -> str:
    encoded = urllib.parse.quote(data_payload)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=10&data={encoded}"


def _build_upi_intent(vpa: str, payee_name: str, amount: float, note: str, order_id: str) -> str:
    params = {
        "pa": vpa.strip(),
        "pn": payee_name.strip(),
        "am": f"{float(amount):.2f}",
        "cu": "INR",
        "tn": f"{note} #{order_id[-6:]}",
        "tr": order_id
    }
    return f"upi://pay?{urllib.parse.urlencode(params)}"


# ── UI Builders ───────────────────────────────────────────────────────

async def build_plans_view(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    prem_user = await db.get_premium_user(user_id)
    is_owner = await db.is_admin(user_id)

    if is_owner:
        user_badge = "👑 <b>Owner / Super Admin</b> (Permanent Unlimited VIP)"
    elif prem_user:
        exp_str = _format_time_ist(prem_user.get("expires_at", 0))
        plan_name = PLANS.get(prem_user.get("plan", "pro"), {}).get("name", "VIP Member")
        user_badge = f"💎 <b>Active:</b> {plan_name} (Expires: <code>{exp_str} IST</code>)"
    else:
        user_badge = "🥉 <b>Free Member</b> (Standard Speed, Verification Required)"

    text = (
        "<blockquote><b>💎 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs</u></b></blockquote>\n\n"
        f"<b>Your Status:</b> {user_badge}\n\n"
        "<i>Unlock unrestricted channel cloning, extreme 0.5s turbo speed, smart autosave listeners, and bypass all verifications!</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<b>🥉 STARTER PASS</b> — <code>₹49</code> (or 35 ⭐ Stars)\n"
        "  • <b>Validity:</b> 7 Days\n"
        "  • <b>Speed:</b> 1.0s Fast Forward\n"
        "  • <b>Batch:</b> 500 Messages\n"
        "  • <b>Perks:</b> 0 Verification Required · 1 Bot Slot\n\n"
        "<b>🥈 PRO MONTHLY PASS</b> — <code>₹149</code> (or 110 ⭐ Stars) 🔥 <b>POPULAR</b>\n"
        "  • <b>Validity:</b> 30 Days\n"
        "  • <b>Speed:</b> 0.5s Extreme Turbo\n"
        "  • <b>Batch:</b> Unlimited Forwarding\n"
        "  • <b>Perks:</b> AutoSave Monitor · Course Seller Mode · 3 Bot Slots · 0 Verification\n\n"
        "<b>🥇 ULTRA LIFETIME PASS</b> — <code>₹399</code> (or 290 ⭐ Stars) 👑 <b>BEST VALUE</b>\n"
        "  • <b>Validity:</b> 365 Days / Lifetime\n"
        "  • <b>Speed:</b> 0.2s Ultra Turbo\n"
        "  • <b>Batch:</b> Unlimited Everything\n"
        "  • <b>Perks:</b> Dedicated Dump Channel · 10 Bot Slots · Priority Allocation\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>Select a plan below to purchase via UPI / QR or contact Admin:</b>"
    )

    admin_link = _get_admin_contact_link()
    rows = [
        row(
            btn("🥉 Buy Starter (₹49)", "prem_buy_starter", "green"),
            btn("🥈 Buy Pro (₹149)", "prem_buy_pro", "green")
        ),
        row(
            btn("🥇 Buy Ultra Lifetime (₹399)", "prem_buy_ultra", "green")
        ),
        row(
            btn("💳 My Active Plan", "prem_myplan", "blue"),
            btn_url("💬 Contact Admin", admin_link, "blue")
        ),
        row(
            btn("🔙 Back to Home", "back", "red")
        )
    ]
    return text, markup(*rows)


# ── Commands ──────────────────────────────────────────────────────────

@Client.on_message(filters.private & filters.command(["plans", "premium", "buy", "vip"]))
async def plans_cmd(bot: Client, message: Message):
    text, reply_markup = await build_plans_view(message.from_user.id)
    await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)


@Client.on_message(filters.private & filters.command(["myplan", "plan"]))
async def myplan_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    prem_user = await db.get_premium_user(user_id)
    is_owner = await db.is_admin(user_id)

    if is_owner:
        txt = (
            "<blockquote><b>👑 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — sᴜᴘᴇʀ ᴀᴅᴍɪɴ</u></b></blockquote>\n\n"
            "• <b>Tier:</b> <code>Lifetime Super Admin</code>\n"
            "• <b>Expires:</b> <code>Never (Permanent)</code>\n"
            "• <b>Speed:</b> <code>0.2s Ultra Turbo</code>\n"
            "• <b>Batch Limit:</b> <code>Unlimited</code>\n"
            "• <b>AutoSave:</b> <code>Full Multi-Channel</code>\n"
            "• <b>Verification:</b> <code>Permanent Bypass</code>"
        )
    elif prem_user:
        plan_info = PLANS.get(prem_user.get("plan", "pro"), PLANS["pro"])
        exp_str = _format_time_ist(prem_user.get("expires_at", 0))
        rem_secs = max(0, int(prem_user.get("expires_at", 0) - time.time()))
        rem_days = rem_secs // 86400
        rem_hrs = (rem_secs % 86400) // 3600

        perks_formatted = "\n".join([f"  • {p}" for p in plan_info["perks"]])

        txt = (
            f"<blockquote><b>💎 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — {plan_info['name'].upper()}</u></b></blockquote>\n\n"
            f"• <b>Plan:</b> {plan_info['name']}\n"
            f"• <b>Expiry Date:</b> <code>{exp_str} IST</code>\n"
            f"• <b>Remaining:</b> <code>{rem_days} Days, {rem_hrs} Hours</code>\n"
            f"• <b>Speed:</b> <code>{plan_info['speed']}</code>\n"
            f"• <b>Batch Limit:</b> <code>{plan_info['batch_limit']}</code>\n\n"
            f"<b>Active Perks:</b>\n{perks_formatted}"
        )
    else:
        txt = (
            "<blockquote><b>🥉 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — ғʀᴇᴇ ᴍᴇᴍʙᴇʀ</u></b></blockquote>\n\n"
            "• <b>Current Plan:</b> <code>Free Tier</code>\n"
            "• <b>Forward Speed:</b> <code>Normal / Fast (1.0s - 3.0s)</code>\n"
            "• <b>Verification:</b> <code>Required via Shortener / Referral</code>\n"
            "• <b>AutoSave:</b> <code>Basic</code>\n\n"
            "👉 <i>Upgrade to VIP Premium for extreme 0.5s turbo speed, 0 captcha, and unlimited channels!</i>"
        )

    btn_list = [
        row(btn("💎 View VIP Plans", "prem_plans", "green")),
        row(btn("🔙 Back to Home", "back", "red"))
    ]
    await message.reply_text(txt, reply_markup=markup(*btn_list))


# ── Admin Manual Premium Commands ─────────────────────────────────────

@Client.on_message(filters.private & filters.command(["addpremium", "addvip"]))
async def admin_add_premium(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Admin only command.")

    args = message.command[1:]
    if len(args) < 2:
        return await message.reply_text(
            "<b>Usage:</b> <code>/addpremium &lt;user_id&gt; &lt;days&gt; [plan: starter/pro/ultra]</code>\n\n"
            "Example: <code>/addpremium 123456789 30 pro</code>"
        )

    try:
        target_uid = int(args[0])
        days = int(args[1])
        plan_key = args[2].lower() if len(args) >= 3 else "pro"
        if plan_key not in PLANS:
            plan_key = "pro"
    except ValueError:
        return await message.reply_text("❌ Invalid User ID or Days. Must be integers.")

    new_expires = await db.set_premium_user(target_uid, days, plan_key, activated_by=message.from_user.id)
    exp_str = _format_time_ist(new_expires)
    plan_name = PLANS[plan_key]["name"]

    await message.reply_text(
        f"✅ <b>Successfully granted Premium VIP!</b>\n\n"
        f"👤 <b>User:</b> <code>{target_uid}</code>\n"
        f"💎 <b>Plan:</b> {plan_name}\n"
        f"⏳ <b>Validity:</b> <code>{days} Days</code>\n"
        f"📅 <b>Expires:</b> <code>{exp_str} IST</code>"
    )

    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>🎉 <u>ʏᴏᴜʀ ᴠɪᴘ ᴘʀᴇᴍɪᴜᴍ ʜᴀs ʙᴇᴇɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</u></b></blockquote>\n\n"
                f"An administrator has activated your VIP subscription!\n\n"
                f"💎 <b>Plan:</b> {plan_name}\n"
                f"⏳ <b>Duration:</b> <code>{days} Days</code>\n"
                f"📅 <b>Valid Until:</b> <code>{exp_str} IST</code>\n\n"
                "⚡ <i>All premium features are now unlocked! Enjoy zero verification and extreme speed.</i>"
            ),
            reply_markup=markup(row(btn("💎 View Plan Perks", "prem_myplan", "green")))
        )
    except Exception as e:
        logger.debug(f"Could not notify user {target_uid} of VIP grant: {e}")


@Client.on_message(filters.private & filters.command(["delpremium", "delvip"]))
async def admin_del_premium(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Admin only command.")

    args = message.command[1:]
    if not args:
        return await message.reply_text("<b>Usage:</b> <code>/delpremium &lt;user_id&gt;</code>")

    try:
        target_uid = int(args[0])
    except ValueError:
        return await message.reply_text("❌ Invalid User ID.")

    await db.remove_premium_user(target_uid)
    await message.reply_text(f"✅ Premium access revoked for user <code>{target_uid}</code>.")


# ── Callback Handlers ─────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^prem_plans$"))
async def cb_prem_plans(bot: Client, query: CallbackQuery):
    text, reply_markup = await build_plans_view(query.from_user.id)
    await query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^prem_myplan$"))
async def cb_prem_myplan(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    prem_user = await db.get_premium_user(user_id)
    is_owner = await db.is_admin(user_id)

    if is_owner:
        txt = (
            "<blockquote><b>👑 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — sᴜᴘᴇʀ ᴀᴅᴍɪɴ</u></b></blockquote>\n\n"
            "• <b>Tier:</b> <code>Lifetime Super Admin</code>\n"
            "• <b>Expires:</b> <code>Never (Permanent)</code>\n"
            "• <b>Speed:</b> <code>0.2s Ultra Turbo</code>\n"
            "• <b>Batch Limit:</b> <code>Unlimited</code>\n"
            "• <b>Verification:</b> <code>Permanent Bypass</code>"
        )
    elif prem_user:
        plan_info = PLANS.get(prem_user.get("plan", "pro"), PLANS["pro"])
        exp_str = _format_time_ist(prem_user.get("expires_at", 0))
        rem_secs = max(0, int(prem_user.get("expires_at", 0) - time.time()))
        rem_days = rem_secs // 86400
        rem_hrs = (rem_secs % 86400) // 3600

        perks_formatted = "\n".join([f"  • {p}" for p in plan_info["perks"]])

        txt = (
            f"<blockquote><b>💎 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — {plan_info['name'].upper()}</u></b></blockquote>\n\n"
            f"• <b>Plan:</b> {plan_info['name']}\n"
            f"• <b>Expiry Date:</b> <code>{exp_str} IST</code>\n"
            f"• <b>Remaining:</b> <code>{rem_days} Days, {rem_hrs} Hours</code>\n"
            f"• <b>Speed:</b> <code>{plan_info['speed']}</code>\n"
            f"• <b>Batch Limit:</b> <code>{plan_info['batch_limit']}</code>\n\n"
            f"<b>Active Perks:</b>\n{perks_formatted}"
        )
    else:
        txt = (
            "<blockquote><b>🥉 <u>ʏᴏᴜʀ ᴠɪᴘ sᴛᴀᴛᴜs — ғʀᴇᴇ ᴍᴇᴍʙᴇʀ</u></b></blockquote>\n\n"
            "• <b>Current Plan:</b> <code>Free Tier</code>\n"
            "• <b>Forward Speed:</b> <code>Normal / Fast (1.0s - 3.0s)</code>\n"
            "• <b>Verification:</b> <code>Required via Shortener / Referral</code>\n"
            "• <b>AutoSave:</b> <code>Basic</code>\n\n"
            "👉 <i>Upgrade to VIP Premium for extreme 0.5s turbo speed, 0 captcha, and unlimited channels!</i>"
        )

    btn_list = [
        row(btn("💎 Upgrade Plan", "prem_plans", "green")),
        row(btn("🔙 Back to Home", "back", "red"))
    ]
    await query.message.edit_text(txt, reply_markup=markup(*btn_list))


@Client.on_callback_query(filters.regex(r"^prem_buy_(starter|pro|ultra)$"))
async def cb_prem_buy(bot: Client, query: CallbackQuery):
    plan_key = query.data.split("_")[2]
    plan = PLANS.get(plan_key)
    if not plan:
        return await query.answer("Invalid plan selected.", show_alert=True)

    user_id = query.from_user.id
    order_id = f"ORD_{user_id}_{int(time.time())}"
    vpa = getattr(Config, "UPI_ID", "").strip() or "Available on request / Contact Admin"
    payee_name = getattr(Config, "UPI_NAME", "Skinet Verse").strip()
    amount = float(plan["price"])

    upi_intent = _build_upi_intent(vpa, payee_name, amount, plan["tag"], order_id) if "@" in vpa else ""
    qr_code_url = _build_qr_url(upi_intent if upi_intent else f"PAY_SKINET_{order_id}_{amount}")

    order_doc = {
        "order_id": order_id,
        "user_id": user_id,
        "user_mention": query.from_user.mention,
        "plan": plan_key,
        "amount": amount,
        "days": plan["days"],
        "status": "pending",
        "utr": None,
        "screenshot": None,
        "created_at": time.time(),
        "expires_at": time.time() + 1800
    }
    await db.create_premium_order(order_doc)

    admin_link = _get_admin_contact_link()
    crypto_addr = getattr(Config, "CRYPTO_ADDRESS", "").strip()
    crypto_line = f"\n🪙 <b>USDT (TRC20):</b> <code>{crypto_addr}</code>" if crypto_addr else ""

    text = (
        f"<blockquote><b>💳 <u>ᴄʜᴇᴄᴋᴏᴜᴛ — {plan['name'].upper()}</u></b></blockquote>\n\n"
        f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
        f"📦 <b>Plan:</b> {plan['name']} (<code>{plan['days']} Days</code>)\n"
        f"💰 <b>Amount Payable:</b> <code>₹{amount:.2f}</code> (or <code>{plan['stars']} ⭐</code>)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 <b>UPI ID:</b> <code>{vpa}</code>\n"
        f"👤 <b>Payee:</b> <code>{payee_name}</code>{crypto_line}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>📌 Payment Instructions:</b>\n"
        "1️⃣ Open GPay / PhonePe / Paytm / BHIM / Cred.\n"
        "2️⃣ Pay the exact amount to the UPI ID above.\n"
        "3️⃣ Tap <b>📤 Submit UTR / Ref</b> or <b>📸 Send Screenshot</b> below.\n"
        "4️⃣ Once verified by our automated engine or admin, your VIP activates instantly!"
    )

    action_buttons = [
        row(
            btn("📤 Submit UTR / Ref No", f"prem_utr_{order_id}", "green"),
            btn("📸 Submit Screenshot", f"prem_ss_{order_id}", "green")
        ),
        row(
            btn_url("💬 Contact Admin / Direct Buy", admin_link, "blue")
        ),
        row(
            btn("❌ Cancel Order", f"prem_cancel_{order_id}", "red"),
            btn("🔙 All Plans", "prem_plans", "blue")
        )
    ]

    await query.message.edit_text(text, reply_markup=markup(*action_buttons), disable_web_page_preview=False)


@Client.on_callback_query(filters.regex(r"^prem_utr_"))
async def cb_prem_submit_utr(bot: Client, query: CallbackQuery):
    order_id = query.data.replace("prem_utr_", "")
    user_id = query.from_user.id
    _SUBMIT_STATE[user_id] = {"order_id": order_id, "mode": "utr"}

    await query.answer()
    await query.message.reply_text(
        "<blockquote><b>⌨️ <u>sᴜʙᴍɪᴛ ᴜᴛʀ / ᴛʀᴀɴsᴀᴄᴛɪᴏɴ ɪᴅ</u></b></blockquote>\n\n"
        f"Please enter the 12-digit UTR / Reference number for Order <code>{order_id}</code>:\n\n"
        "<i>Send <code>/cancel</code> to abort.</i>"
    )


@Client.on_callback_query(filters.regex(r"^prem_ss_"))
async def cb_prem_submit_ss(bot: Client, query: CallbackQuery):
    order_id = query.data.replace("prem_ss_", "")
    user_id = query.from_user.id
    _SUBMIT_STATE[user_id] = {"order_id": order_id, "mode": "screenshot"}

    await query.answer()
    await query.message.reply_text(
        "<blockquote><b>📸 <u>sᴜʙᴍɪᴛ ᴘᴀʏᴍᴇɴᴛ sᴄʀᴇᴇɴsʜᴏᴛ</u></b></blockquote>\n\n"
        f"Please send the payment screenshot for Order <code>{order_id}</code>:\n\n"
        "<i>Send <code>/cancel</code> to abort.</i>"
    )


@Client.on_callback_query(filters.regex(r"^prem_cancel_"))
async def cb_prem_cancel(bot: Client, query: CallbackQuery):
    order_id = query.data.replace("prem_cancel_", "")
    user_id = query.from_user.id
    _SUBMIT_STATE.pop(user_id, None)
    await db.update_premium_order(order_id, {"status": "cancelled"})
    await query.answer("Order cancelled.", show_alert=True)
    text, reply_markup = await build_plans_view(user_id)
    await query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)


# ── Proof Submission Listener (Text & Photo) ──────────────────────────

@Client.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start", "help", "plans", "premium", "settings", "cancel"]))
async def proof_submission_listener(bot: Client, message: Message):
    user_id = message.from_user.id
    st = _SUBMIT_STATE.get(user_id)
    if not st:
        return

    order_id = st["order_id"]
    mode = st["mode"]
    _SUBMIT_STATE.pop(user_id, None)

    order = await db.get_premium_order(order_id)
    if not order or order.get("status") != "pending":
        return await message.reply_text("❌ This order is invalid or expired. Please create a new order in /plans.")

    plan_info = PLANS.get(order["plan"], PLANS["pro"])
    now_ist = datetime.now(tz=IST).strftime("%d-%b-%Y %I:%M:%S %p")

    utr_val = None
    photo_file_id = None

    if mode == "utr" and message.text:
        utr_val = message.text.strip()
        await db.update_premium_order(order_id, {"utr": utr_val, "submitted_at": time.time(), "status": "verifying"})
    elif mode == "screenshot" and message.photo:
        photo_file_id = message.photo.file_id
        await db.update_premium_order(order_id, {"screenshot": photo_file_id, "submitted_at": time.time(), "status": "verifying"})
    elif message.text:
        utr_val = message.text.strip()
        await db.update_premium_order(order_id, {"utr": utr_val, "submitted_at": time.time(), "status": "verifying"})

    await message.reply_text(
        "<blockquote><b>⏳ <u>ᴘᴀʏᴍᴇɴᴛ ᴘʀᴏᴏғ sᴜʙᴍɪᴛᴛᴇᴅ!</u></b></blockquote>\n\n"
        f"Thank you, {message.from_user.first_name}!\n"
        f"Your proof for Order <code>{order_id}</code> has been dispatched to administrators.\n\n"
        f"💎 <b>Plan:</b> {plan_info['name']} (<code>₹{order['amount']:.2f}</code>)\n"
        f"🧾 <b>Ref/UTR:</b> <code>{utr_val or 'Screenshot Attached'}</code>\n\n"
        "⚡ <i>Your VIP pass will be activated as soon as an admin approves. You will be notified automatically!</i>",
        reply_markup=markup(row(btn("💎 Back to Plans", "prem_plans", "blue")))
    )

    # Dispatch to LOG_CHANNEL & Bot Owners for 1-click verification
    admin_alert_text = (
        "<blockquote><b>💎 <u>#NewPremiumOrderPending</u></b></blockquote>\n\n"
        f"👤 <b>User:</b> {message.from_user.mention} (<code>{user_id}</code>)\n"
        f"📦 <b>Plan:</b> {plan_info['name']} (<code>{order['days']} Days</code>)\n"
        f"💰 <b>Amount:</b> <code>₹{order['amount']:.2f}</code>\n"
        f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
        f"🧾 <b>UTR / Ref:</b> <code>{utr_val or 'See Screenshot'}</code>\n"
        f"⏰ <b>Time:</b> <code>{now_ist} IST</code>\n\n"
        "👇 <b>Approve or Reject this payment:</b>"
    )

    admin_actions = markup(
        row(
            btn("✅ Approve VIP", f"prem_appr_{user_id}_{order['plan']}_{order_id}", "green"),
            btn("❌ Reject", f"prem_rej_{user_id}_{order_id}", "red")
        )
    )

    targets = set()
    if Config.LOG_CHANNEL:
        targets.add(Config.LOG_CHANNEL)
    for oid in Config.BOT_OWNER_ID:
        targets.add(oid)

    for target in targets:
        try:
            if photo_file_id:
                await bot.send_photo(target, photo=photo_file_id, caption=admin_alert_text, reply_markup=admin_actions)
            else:
                await bot.send_message(target, text=admin_alert_text, reply_markup=admin_actions)
        except Exception as e:
            logger.warning(f"Could not notify admin {target} of premium proof: {e}")


# ── Admin Approval & Rejection Callbacks ──────────────────────────────

@Client.on_callback_query(filters.regex(r"^prem_appr_"))
async def cb_prem_approve(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only action!", show_alert=True)

    parts = query.data.split("_")
    # prem_appr_{user_id}_{plan}_{order_id}
    target_uid = int(parts[2])
    plan_key = parts[3]
    order_id = "_".join(parts[4:])

    plan_info = PLANS.get(plan_key, PLANS["pro"])
    new_expires = await db.set_premium_user(target_uid, plan_info["days"], plan_key, activated_by=query.from_user.id)
    await db.update_premium_order(order_id, {"status": "approved", "approved_by": query.from_user.id, "approved_at": time.time()})

    exp_str = _format_time_ist(new_expires)
    admin_name = query.from_user.first_name

    await query.answer(f"✅ Approved! VIP granted to {target_uid}", show_alert=True)

    try:
        if query.message.caption:
            await query.message.edit_caption(
                f"{query.message.caption}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>APPROVED BY {admin_name} ({query.from_user.id})</b>\n📅 <b>Valid Until:</b> <code>{exp_str} IST</code>"
            )
        else:
            await query.message.edit_text(
                f"{query.message.text}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>APPROVED BY {admin_name} ({query.from_user.id})</b>\n📅 <b>Valid Until:</b> <code>{exp_str} IST</code>"
            )
    except Exception:
        pass

    # Notify user with celebration card
    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>🎉 <u>ᴘʀᴇᴍɪᴜᴍ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</u></b></blockquote>\n\n"
                f"Your payment has been verified and your VIP pass is active!\n\n"
                f"💎 <b>Plan:</b> {plan_info['name']}\n"
                f"⏳ <b>Validity:</b> <code>{plan_info['days']} Days</code>\n"
                f"📅 <b>Expires:</b> <code>{exp_str} IST</code>\n\n"
                "<b>✨ All Premium Features Unlocked:</b>\n"
                "• ⚡ Extreme 0.5s Turbo Forwarding\n"
                "• 🛡️ 0 Token Verification / Captcha Forever\n"
                "• 🚀 Unlimited Batch Forwarding\n"
                "• 📡 Smart AutoSave Real-Time Monitoring\n"
                "• 🎓 Course Seller Syllabus Indexer\n\n"
                "<i>Thank you for supporting Skinet Verse!</i>"
            ),
            reply_markup=markup(row(btn("💎 View My Plan", "prem_myplan", "green")))
        )
    except Exception as e:
        logger.warning(f"Failed to send VIP celebration to {target_uid}: {e}")


@Client.on_callback_query(filters.regex(r"^prem_rej_"))
async def cb_prem_reject(bot: Client, query: CallbackQuery):
    if not await db.is_admin(query.from_user.id):
        return await query.answer("⚠️ Admin only action!", show_alert=True)

    parts = query.data.split("_")
    target_uid = int(parts[2])
    order_id = "_".join(parts[3:])

    await db.update_premium_order(order_id, {"status": "rejected", "rejected_by": query.from_user.id, "rejected_at": time.time()})
    admin_name = query.from_user.first_name

    await query.answer("❌ Order rejected.", show_alert=True)

    try:
        if query.message.caption:
            await query.message.edit_caption(
                f"{query.message.caption}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n❌ <b>REJECTED BY {admin_name}</b>"
            )
        else:
            await query.message.edit_text(
                f"{query.message.text}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n❌ <b>REJECTED BY {admin_name}</b>"
            )
    except Exception:
        pass

    admin_link = _get_admin_contact_link()
    try:
        await bot.send_message(
            target_uid,
            (
                "<blockquote><b>⚠️ <u>ᴘᴀʏᴍᴇɴᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ ᴜɴsᴜᴄᴄᴇssғᴜʟ</u></b></blockquote>\n\n"
                f"Your payment proof for Order <code>{order_id}</code> could not be verified by our team.\n\n"
                "<i>If you believe this is a mistake, please contact our administrator directly with your bank transaction statement.</i>"
            ),
            reply_markup=markup(row(btn_url("💬 Contact Admin", admin_link, "blue")))
        )
    except Exception as e:
        logger.warning(f"Could not notify user of rejection: {e}")
