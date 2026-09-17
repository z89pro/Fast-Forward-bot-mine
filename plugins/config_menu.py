import os
import sys
import asyncio
import logging
from config import Config, temp
from database import db
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, CallbackQuery, Message
from buttons import StyledMarkup as InlineKeyboardMarkup, btn, btn_url, row, markup, colored_markup

logger = logging.getLogger("SkinetConfig")

async def is_admin(user_id: int) -> bool:
    return await db.is_admin(user_id)

def mask_secret(s: str) -> str:
    if not s or not isinstance(s, str):
        return "N/A"
    s = s.strip()
    if len(s) <= 8:
        return "•" * len(s)
    return s[:4] + "•" * 8 + s[-4:]

async def build_config_view() -> str:
    fsub_status = "🟢 <b>Enabled</b>" if Config.FORCE_SUB_ON else "🔴 <b>Disabled</b>"
    fsub_chan = f"<code>{Config.FORCE_SUB_CHANNEL}</code>" if Config.FORCE_SUB_CHANNEL else "<i>None (Not set)</i>"
    log_chan = f"<code>{Config.LOG_CHANNEL}</code>" if Config.LOG_CHANNEL else "<i>None (Not set)</i>"
    dump_chan = f"<code>{Config.DUMP_CHANNEL}</code>" if Config.DUMP_CHANNEL else "<i>None (Not set)</i>"
    all_admins = await db.get_all_admins()
    admins_str = " ".join([f"<code>{x}</code>" for x in all_admins]) if all_admins else "<i>None</i>"
    masked_token = mask_secret(Config.BOT_TOKEN)
    masked_hash = mask_secret(Config.API_HASH)
    fast_delay = getattr(Config, 'FAST_DELAY', 1.0)
    vcfg = await db.get_verify_config()
    v_status = "🟢 <b>Enabled</b>" if vcfg.get('enabled') else "🔴 <b>Disabled</b>"
    v_info = f"{vcfg.get('duration', 24)}h ({vcfg.get('steps', 1)} Step)"
    upi_val = getattr(Config, 'UPI_ID', '') or "<i>Not Set</i>"
    
    text = (
        "<blockquote><b>⚙️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ ᴄᴏɴғɪɢᴜʀᴀᴛɪᴏɴ</u></b></blockquote>\n\n"
        "<i>Modify global bot environment values dynamically from Telegram. Changes persist in MongoDB across server restarts!</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>Authorized Admins ({len(all_admins)}):</b> {admins_str}\n"
        f"📡 <b>Log Channel ID:</b> {log_chan}\n"
        f"📦 <b>Dump Channel ID:</b> {dump_chan}\n"
        f"📢 <b>Force Sub Channel:</b> {fsub_chan}\n"
        f"🔒 <b>Force Sub Enforced:</b> {fsub_status}\n"
        f"🛡️ <b>Token Verification:</b> {v_status} (<code>{v_info}</code>)\n"
        f"💳 <b>UPI Payment ID:</b> <code>{upi_val}</code>\n"
        f"🤖 <b>Bot Token:</b> <code>{masked_token}</code>\n"
        f"🔑 <b>API ID / Hash:</b> <code>{Config.API_ID}</code> / <code>{masked_hash}</code>\n"
        f"⚡️ <b>Default Speed Delay:</b> <code>{fast_delay}s</code>\n"
        f"🗄 <b>Database Name:</b> <code>{Config.DATABASE_NAME}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <b>Select any parameter below to update its value:</b>"
    )
    return text

def build_config_buttons(vcfg=None) -> InlineKeyboardMarkup:
    fsub_mark = "✅ ᴏɴ" if Config.FORCE_SUB_ON else "❌ ᴏғғ"
    v_enabled = vcfg.get("enabled", True) if vcfg else Config.VERIFY_ENABLED
    v_mark = "✅ ᴏɴ" if v_enabled else "❌ ᴏғғ"
    buttons = [
        [
            InlineKeyboardButton("📡 ʟᴏɢ ᴄʜᴀɴɴᴇʟ", callback_data="config#set_log"),
            InlineKeyboardButton("📦 ᴅᴜᴍᴘ ᴄʜᴀɴɴᴇʟ", callback_data="config#set_dump")
        ],
        [
            InlineKeyboardButton("📢 ғᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ", callback_data="config#set_fsub"),
            InlineKeyboardButton(f"🔒 ғ-sᴜʙ: {fsub_mark}", callback_data="config#toggle_fsub")
        ],
        [
            InlineKeyboardButton(f"🛡️ ᴠᴇʀɪғʏ: {v_mark}", callback_data="config#toggle_verify"),
            InlineKeyboardButton("⚙️ ᴠᴇʀɪғʏ sᴇᴛᴛɪɴɢs", callback_data="config#verify_settings")
        ],
        [
            InlineKeyboardButton("👑 ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", callback_data="config#manage_admins"),
            InlineKeyboardButton("💳 ᴜᴘɪ ᴘᴀʏᴍᴇɴᴛ ɪᴅ", callback_data="config#set_upi")
        ],
        [
            InlineKeyboardButton("⚡️ sᴘᴇᴇᴅ ᴅᴇʟᴀʏ", callback_data="config#set_speed"),
            InlineKeyboardButton("🤖 ʙᴏᴛ ᴛᴏᴋᴇɴ", callback_data="config#set_token")
        ],
        [
            InlineKeyboardButton("🔑 ᴀᴘɪ ɪᴅ / ʜᴀsʜ", callback_data="config#set_api"),
            InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ ʙᴏᴛ ɴᴏᴡ", callback_data="config#restart")
        ],
        [
            InlineKeyboardButton("⚙️ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs", callback_data="settings#main"),
            InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="back")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


# ================= COMMAND /config & /env =================

@Client.on_message(filters.private & filters.command(["config", "env", "vars"]))
async def config_cmd(bot: Client, message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return await message.reply_text(
            "⚠️ <b>Access Denied:</b> This configuration dashboard is strictly restricted to Bot Admins & Owners.",
            quote=True
        )
    text = await build_config_view()
    vcfg = await db.get_verify_config()
    await message.reply_text(text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)


# ================= CALLBACK QUERY ROUTER =================

@Client.on_callback_query(filters.regex(r"^config"))
async def config_callback(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if not await is_admin(user_id):
        return await query.answer("⚠️ Access Denied! Restricted to Bot Admins & Owners only.", show_alert=True)

    data = query.data.split("#")[1] if "#" in query.data else "main"

    if data == "main":
        text = await build_config_view()
        vcfg = await db.get_verify_config()
        await query.message.edit_text(text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)

    elif data == "toggle_fsub":
        Config.FORCE_SUB_ON = not Config.FORCE_SUB_ON
        await db.update_system_config("FORCE_SUB_ON", Config.FORCE_SUB_ON)
        status_txt = "Enabled" if Config.FORCE_SUB_ON else "Disabled"
        await query.answer(f"Force Sub is now {status_txt}!")
        text = await build_config_view()
        vcfg = await db.get_verify_config()
        await query.message.edit_text(text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)

    elif data == "toggle_verify":
        vcfg = await db.get_verify_config()
        new_val = not vcfg.get("enabled", True)
        await db.update_verify_config("enabled", new_val)
        Config.VERIFY_ENABLED = new_val
        status_txt = "Enabled" if new_val else "Disabled"
        await query.answer(f"Token verification is now {status_txt}!")
        text = await build_config_view()
        vcfg["enabled"] = new_val
        await query.message.edit_text(text, reply_markup=build_config_buttons(vcfg), disable_web_page_preview=True)

    elif data == "verify_settings":
        await query.answer()
        vcfg = await db.get_verify_config()
        status_txt = "🟢 ᴇɴᴀʙʟᴇᴅ" if vcfg.get("enabled") else "🔴 ᴅɪsᴀʙʟᴇᴅ"
        s1 = f"{vcfg.get('shortener_url', 'None')} (API: {'Set' if vcfg.get('shortener_api') else 'None'})"
        s2 = f"{vcfg.get('shortener_url2', 'None')} (API: {'Set' if vcfg.get('shortener_api2') else 'None'})"
        s3 = f"{vcfg.get('shortener_url3', 'None')} (API: {'Set' if vcfg.get('shortener_api3') else 'None'})"
        txt = (
            "<blockquote><b>🛡️ <u>ᴛᴏᴋᴇɴ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴇᴛᴛɪɴɢs</u></b></blockquote>\n\n"
            f"• <b>sᴛᴀᴛᴜs:</b> <code>{status_txt}</code>\n"
            f"• <b>ᴘᴀss ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{vcfg.get('duration', 24)} Hours</code>\n"
            f"• <b>ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ sᴛᴇᴘs:</b> <code>{vcfg.get('steps', 1)} Step(s)</code>\n"
            f"• <b>ʟɪɴᴋ ᴛɪᴍᴇᴏᴜᴛ:</b> <code>{vcfg.get('timeout', 30)} Minutes</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Shortener 1:</b> <code>{s1}</code>\n"
            f"<b>Shortener 2:</b> <code>{s2}</code>\n"
            f"<b>Shortener 3:</b> <code>{s3}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>💡 Use <code>/setverify</code> in chat to change steps, duration, and add shortener API keys.</i>"
        )
        await query.message.edit_text(
            txt,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#main")]
            ]),
            disable_web_page_preview=True
        )

    elif data == "set_log":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            text=(
                "<b>📡 Send new Log Channel ID:</b>\n\n"
                "Example: <code>-1003584084546</code>\n"
                "Send <code>0</code> to disable logging\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw = ask.text.strip()
        if not (raw.lstrip("-").isdigit()):
            return await bot.send_message(
                user_id,
                "<b>❌ Invalid Channel ID! Must be numbers (e.g. -1001234567890).</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )
        
        new_val = int(raw)
        Config.LOG_CHANNEL = new_val
        await db.update_system_config("LOG_CHANNEL", new_val)
        
        # Test notification dispatch
        if new_val != 0:
            try:
                await bot.send_message(new_val, "📡 <b>Log Channel Connected Successfully!</b>\n<i>⚡️ Powered by Skinet Verse</i>")
            except Exception as e:
                logger.warning(f"Could not dispatch test ping to new log channel {new_val}: {e}")

        await bot.send_message(
            user_id,
            f"✅ <b>Log Channel updated to:</b> <code>{new_val}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_dump":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            text=(
                "<b>📦 Send new Dump Channel ID:</b>\n\n"
                "Example: <code>-1001234567890</code>\n"
                "Send <code>0</code> to disable media dump\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw = ask.text.strip()
        if not (raw.lstrip("-").isdigit()):
            return await bot.send_message(
                user_id,
                "<b>❌ Invalid Channel ID! Must be numbers.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )
        
        new_val = int(raw)
        Config.DUMP_CHANNEL = new_val
        await db.update_system_config("DUMP_CHANNEL", new_val)
        await db.update_admin_dump(new_val, enabled=bool(new_val != 0))

        await bot.send_message(
            user_id,
            f"✅ <b>Dump Channel updated to:</b> <code>{new_val}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_fsub":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            text=(
                "<b>📢 Send new Force Sub Channel:</b>\n\n"
                "Examples:\n"
                "• <code>@MyChannel</code>\n"
                "• <code>https://t.me/MyChannel</code>\n"
                "• <code>-1001234567890</code>\n"
                "Send <code>none</code> to clear\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw = ask.text.strip()
        val = "" if raw.lower() in ("none", "0", "off") else raw
        Config.FORCE_SUB_CHANNEL = val
        await db.update_system_config("FORCE_SUB_CHANNEL", val)

        await bot.send_message(
            user_id,
            f"✅ <b>Force Sub Channel set to:</b> <code>{val or 'None'}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "manage_admins":
        admins = await db.get_all_admins()
        primary_owner = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
        admin_lines = []
        for a in admins:
            tag = " 👑 (Primary Owner)" if a == primary_owner else " 🛡️ (Admin)"
            admin_lines.append(f"• <code>{a}</code>{tag}")
        admins_body = "\n".join(admin_lines) if admin_lines else "<i>None</i>"

        text = (
            "<blockquote><b>👑 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴍᴜʟᴛɪ-ᴀᴅᴍɪɴ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ</u></b></blockquote>\n\n"
            f"<b>Total Authorized Admins:</b> <code>{len(admins)}</code>\n\n"
            f"{admins_body}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Authorized administrators have full access to system configuration, premium VIP approvals, shortener management, and live logs.</i>\n\n"
            "👇 <b>Select an action below:</b>"
        )
        btns = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ ᴀᴅᴅ ᴀᴅᴍɪɴ", callback_data="config#add_admin_prompt"),
                InlineKeyboardButton("➖ ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ", callback_data="config#del_admin_prompt")
            ],
            [
                InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")
            ]
        ])
        await query.message.edit_text(text, reply_markup=btns)

    elif data == "add_admin_prompt":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            text=(
                "<b>👑 Send the Telegram User ID to promote as Admin:</b>\n\n"
                "Example: <code>987654321</code>\n"
                "<i>User ID can be found via @userinfobot or /status.</i>\n\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        val = ask.text.strip()
        if not val.isdigit():
            return await bot.send_message(
                user_id,
                "<b>❌ Invalid ID! User ID must be numbers only.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#manage_admins")]])
            )
        new_admin = int(val)
        await db.add_admin(new_admin)
        await bot.send_message(
            user_id,
            f"✅ <b>Successfully added user <code>{new_admin}</code> to authorized administrators!</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴs", callback_data="config#manage_admins")]])
        )

    elif data == "del_admin_prompt":
        await query.message.delete()
        admins = await db.get_all_admins()
        primary_owner = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
        ask = await bot.ask(
            user_id,
            text=(
                f"👑 <b>Current Admins:</b> <code>{' '.join(str(x) for x in admins)}</code>\n\n"
                "<b>Send the Telegram User ID to remove from Admins:</b>\n"
                "<i>Note: Primary owner cannot be removed.</i>\n\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        val = ask.text.strip()
        if not val.isdigit():
            return await bot.send_message(
                user_id,
                "<b>❌ Invalid ID! Must be digits only.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#manage_admins")]])
            )
        del_admin = int(val)
        if primary_owner and del_admin == primary_owner:
            return await bot.send_message(
                user_id,
                "<b>⚠️ Primary bot owner cannot be removed!</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#manage_admins")]])
            )
        await db.remove_admin(del_admin)
        await bot.send_message(
            user_id,
            f"✅ <b>Successfully removed <code>{del_admin}</code> from administrators!</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴs", callback_data="config#manage_admins")]])
        )

    elif data == "set_upi":
        await query.message.delete()
        curr_upi = getattr(Config, 'UPI_ID', '') or 'None'
        ask = await bot.ask(
            user_id,
            text=(
                f"💳 <b>Current UPI ID:</b> <code>{curr_upi}</code>\n\n"
                "<b>Send new UPI ID for receiving premium payments:</b>\n"
                "Example: <code>yourname@upi</code> or <code>merchant@okhdfcbank</code>\n"
                "Send <code>none</code> to remove.\n\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        new_upi = ask.text.strip()
        if new_upi.lower() in ("none", "0", "off"):
            new_upi = ""
        Config.UPI_ID = new_upi
        await db.update_system_config("UPI_ID", new_upi)
        await bot.send_message(
            user_id,
            f"✅ <b>UPI Payment ID updated to:</b> <code>{new_upi or 'None'}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_admins":
        await query.message.delete()
        admins = await db.get_all_admins()
        curr = " ".join([str(x) for x in admins])
        ask = await bot.ask(
            user_id,
            text=(
                f"👑 <b>Current Admin IDs:</b> <code>{curr}</code>\n\n"
                "<b>Send space-separated Telegram user IDs to set as authorized admins:</b>\n"
                "Example: <code>8349955493 987654321</code>\n\n"
                "<i>Note: Your ID will always be preserved so you cannot lock yourself out.</i>\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        raw_ids = ask.text.strip().replace(",", " ").split()
        parsed = [int(x) for x in raw_ids if x.lstrip("-").isdigit()]
        if user_id not in parsed:
            parsed.append(user_id)
        
        for aid in parsed:
            await db.add_admin(aid)

        await bot.send_message(
            user_id,
            f"✅ <b>Admin list updated to:</b> <code>{parsed}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_speed":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            text=(
                "<b>⚡️ Send new Default Forward Delay (in seconds):</b>\n\n"
                "Presets:\n"
                "• <code>0.2</code> or <code>0.5</code> (Extreme Fast)\n"
                "• <code>1.0</code> (Fast Default)\n"
                "• <code>3.0</code> (Normal Safe)\n"
                "• <code>5.0</code> (Anti-Flood Strict)\n\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=120
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        try:
            val = float(ask.text.strip())
            if val < 0.1 or val > 60.0:
                raise ValueError()
        except ValueError:
            return await bot.send_message(
                user_id,
                "<b>❌ Invalid delay! Enter a decimal number between 0.1 and 60.0</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        Config.FAST_DELAY = val
        await db.update_system_config("FAST_DELAY", val)

        await bot.send_message(
            user_id,
            f"✅ <b>Default Delay set to:</b> <code>{val}s</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "set_token":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            text=(
                "<b>🤖 Send new Telegram Bot Token:</b>\n\n"
                "Format: <code>1234567890:AAHxxxx...</code>\n\n"
                "⚠️ <b>Important:</b> <i>After saving a new bot token, you MUST restart the bot for the change to take effect!</i>\n"
                "<i>/cancel - Abort</i>"
            ),
            timeout=180
        )
        if not ask.text or ask.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        token = ask.text.strip()
        if not (":" in token and token.split(":", 1)[0].isdigit()):
            return await bot.send_message(
                user_id,
                "<b>❌ Invalid Bot Token format! Must be numeric_id:string from @BotFather.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
            )

        Config.BOT_TOKEN = token
        await db.update_system_config("BOT_TOKEN", token)

        await bot.send_message(
            user_id,
            f"✅ <b>Bot Token saved to database!</b>\n\nToken: <code>{mask_secret(token)}</code>\n\nClick below to restart the bot client with this new token:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 ʀᴇsᴛᴀʀᴛ ʙᴏᴛ ɴᴏᴡ", callback_data="config#restart")],
                [InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]
            ])
        )

    elif data == "set_api":
        await query.message.delete()
        ask_id = await bot.ask(
            user_id,
            text="<b>🔑 Send your Telegram API ID (numbers):</b>\n\n<i>/cancel - Abort</i>",
            timeout=120
        )
        if not ask_id.text or ask_id.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        if not ask_id.text.strip().isdigit():
            return await bot.send_message(user_id, "<b>❌ API ID must be digits only!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ", callback_data="config#main")]]))
        
        api_id = int(ask_id.text.strip())

        ask_hash = await bot.ask(
            user_id,
            text="<b>🔑 Send your Telegram API HASH (hex string):</b>\n\n<i>/cancel - Abort</i>",
            timeout=120
        )
        if not ask_hash.text or ask_hash.text.startswith("/cancel"):
            text = await build_config_view()
            return await bot.send_message(user_id, text, reply_markup=build_config_buttons(), disable_web_page_preview=True)

        api_hash = ask_hash.text.strip()
        Config.API_ID = api_id
        Config.API_HASH = api_hash
        await db.update_system_config("API_ID", api_id)
        await db.update_system_config("API_HASH", api_hash)

        await bot.send_message(
            user_id,
            f"✅ <b>API Credentials updated!</b>\nAPI ID: <code>{api_id}</code>\nAPI Hash: <code>{mask_secret(api_hash)}</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• ʙᴀᴄᴋ ᴛᴏ ᴄᴏɴғɪɢ", callback_data="config#main")]])
        )

    elif data == "restart":
        msg = await query.message.edit_text(
            "<blockquote><b>🔄 Restarting Skinet Verse Bot Engine...</b>\n\n<i>All services will reload with latest database configs in 5 seconds.</i></blockquote>"
        )
        try:
            await db.set_restart_status(query.message.chat.id, msg.id)
        except Exception:
            pass
        try:
            import json
            with open('.restart_status.json', 'w') as f:
                json.dump({'chat_id': query.message.chat.id, 'message_id': msg.id}, f)
        except Exception:
            pass
        await asyncio.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)


# ================= MULTI-ADMIN COMMANDS =================

@Client.on_message(filters.private & filters.command(["addadmin"]))
async def cmd_add_admin(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Restricted to Bot Admins & Owners.")
    args = message.command[1:]
    if not args or not args[0].isdigit():
        return await message.reply_text("<b>Usage:</b> <code>/addadmin &lt;user_id&gt;</code>\n\nExample: <code>/addadmin 987654321</code>")
    new_uid = int(args[0])
    await db.add_admin(new_uid)
    await message.reply_text(f"✅ User <code>{new_uid}</code> has been granted Administrator privileges.")


@Client.on_message(filters.private & filters.command(["deladmin"]))
async def cmd_del_admin(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Restricted to Bot Admins & Owners.")
    args = message.command[1:]
    if not args or not args[0].isdigit():
        return await message.reply_text("<b>Usage:</b> <code>/deladmin &lt;user_id&gt;</code>\n\nExample: <code>/deladmin 987654321</code>")
    del_uid = int(args[0])
    primary_owner = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
    if primary_owner and del_uid == primary_owner:
        return await message.reply_text("⚠️ <b>Cannot remove primary Bot Owner.</b>")
    await db.remove_admin(del_uid)
    await message.reply_text(f"✅ User <code>{del_uid}</code> removed from Administrator privileges.")


@Client.on_message(filters.private & filters.command(["admins"]))
async def cmd_admins(bot: Client, message: Message):
    if not await db.is_admin(message.from_user.id):
        return await message.reply_text("⚠️ <b>Access Denied:</b> Restricted to Bot Admins & Owners.")
    admins = await db.get_all_admins()
    primary = Config.BOT_OWNER_ID[0] if Config.BOT_OWNER_ID else None
    lines = []
    for a in admins:
        tag = " 👑 (Primary Owner)" if a == primary else " 🛡️ (Admin)"
        lines.append(f"• <code>{a}</code>{tag}")
    admin_text = (
        "<blockquote><b>👑 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs</u></b></blockquote>\n\n"
        f"<b>Total Count:</b> <code>{len(admins)}</code>\n\n" + "\n".join(lines)
    )
    await message.reply_text(admin_text)

