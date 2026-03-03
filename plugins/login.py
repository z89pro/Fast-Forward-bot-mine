"""
plugins/login.py
Handles /login and /logout commands.
OTP + 2FA both have 5-retry mechanism.
"""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired,
    SessionPasswordNeeded, BadRequest
)
from utils.session_manager import create_temp_client, stop_user_client
import database as db

MAX_RETRIES = 5

# Track ongoing login sessions: {user_id: state_dict}
_login_state: dict = {}


def register(bot: Client):

    @bot.on_message(filters.command("login") & filters.private)
    async def login_cmd(client: Client, msg: Message):
        user_id = msg.from_user.id

        if await db.get_session(user_id):
            await msg.reply("✅ Already logged in!\nUse /logout to log out first.")
            return

        if user_id in _login_state:
            await msg.reply("⏳ Login already in progress. Send your OTP or wait for timeout.")
            return

        await msg.reply(
            "📱 **Login to your Telegram Account**\n\n"
            "Send your phone number with country code.\n"
            "Example: `+919876543210`\n\n"
            "_Send /cancel to abort._"
        )

        # ── Step 1: Phone number ──────────────────────────────
        try:
            phone_msg: Message = await client.listen(
                filters.text & filters.private & filters.user(user_id),
                timeout=300
            )
        except asyncio.TimeoutError:
            await msg.reply("⌛ Timed out. Send /login to try again.")
            return

        if phone_msg.text.strip().lower() == "/cancel":
            await msg.reply("❌ Login cancelled.")
            return

        phone = phone_msg.text.strip()
        temp_client = await create_temp_client(user_id)
        await temp_client.connect()

        try:
            sent = await temp_client.send_code(phone)
        except PhoneNumberInvalid:
            await msg.reply("❌ Invalid phone number. Try /login again.")
            await temp_client.disconnect()
            return
        except Exception as e:
            await msg.reply(f"❌ Error: `{e}`\nTry /login again.")
            await temp_client.disconnect()
            return

        _login_state[user_id] = {
            "client": temp_client,
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash,
        }

        # ── Step 2: OTP — 5 retries ───────────────────────────
        otp_success = False
        needs_2fa = False

        for attempt in range(1, MAX_RETRIES + 1):
            remaining_attempts = MAX_RETRIES - attempt

            await msg.reply(
                f"📩 **Enter OTP** (Attempt {attempt}/{MAX_RETRIES})\n\n"
                f"Send the code you received on Telegram.\n"
                f"Format: `1 2 3 4 5` or `12345`\n\n"
                f"_Send /cancel to abort._"
            )

            try:
                code_msg: Message = await client.listen(
                    filters.text & filters.private & filters.user(user_id),
                    timeout=300
                )
            except asyncio.TimeoutError:
                await msg.reply("⌛ OTP timed out. Send /login to try again.")
                await temp_client.disconnect()
                _login_state.pop(user_id, None)
                return

            if code_msg.text.strip().lower() == "/cancel":
                await msg.reply("❌ Login cancelled.")
                await temp_client.disconnect()
                _login_state.pop(user_id, None)
                return

            otp = code_msg.text.replace(" ", "").strip()
            state = _login_state[user_id]

            try:
                await temp_client.sign_in(
                    phone_number=state["phone"],
                    phone_code_hash=state["phone_code_hash"],
                    phone_code=otp
                )
                otp_success = True
                break  # ✅ OTP correct

            except PhoneCodeInvalid:
                if remaining_attempts > 0:
                    await code_msg.reply(
                        f"❌ **Wrong OTP!**\n"
                        f"You have **{remaining_attempts}** attempt(s) left."
                    )
                else:
                    await code_msg.reply("❌ Wrong OTP. All attempts used. Try /login again.")
                    await temp_client.disconnect()
                    _login_state.pop(user_id, None)
                    return

            except PhoneCodeExpired:
                await code_msg.reply("❌ OTP expired. Try /login again.")
                await temp_client.disconnect()
                _login_state.pop(user_id, None)
                return

            except SessionPasswordNeeded:
                needs_2fa = True
                break  # Exit OTP loop, go to 2FA

            except Exception as e:
                await code_msg.reply(f"❌ Error: `{e}`\nTry /login again.")
                await temp_client.disconnect()
                _login_state.pop(user_id, None)
                return

        # ── Step 3: 2FA — 5 retries (if needed) ──────────────
        if needs_2fa:
            await msg.reply(
                "🔐 **2FA Password Required**\n\n"
                f"Your account has Two-Factor Authentication.\n"
                f"You have **{MAX_RETRIES}** attempts.\n\n"
                "_Send /cancel to abort._"
            )

            twofa_success = False
            for attempt in range(1, MAX_RETRIES + 1):
                remaining_attempts = MAX_RETRIES - attempt

                await msg.reply(
                    f"🔑 **Enter 2FA Password** (Attempt {attempt}/{MAX_RETRIES}):"
                )

                try:
                    pass_msg: Message = await client.listen(
                        filters.text & filters.private & filters.user(user_id),
                        timeout=300
                    )
                except asyncio.TimeoutError:
                    await msg.reply("⌛ 2FA timed out. Try /login again.")
                    await temp_client.disconnect()
                    _login_state.pop(user_id, None)
                    return

                if pass_msg.text.strip().lower() == "/cancel":
                    await msg.reply("❌ Login cancelled.")
                    await temp_client.disconnect()
                    _login_state.pop(user_id, None)
                    return

                try:
                    await temp_client.check_password(pass_msg.text.strip())
                    twofa_success = True
                    otp_success = True
                    break  # ✅ 2FA correct

                except BadRequest:
                    if remaining_attempts > 0:
                        await pass_msg.reply(
                            f"❌ **Wrong password!**\n"
                            f"You have **{remaining_attempts}** attempt(s) left."
                        )
                    else:
                        await pass_msg.reply(
                            "❌ Wrong password. All attempts used.\n"
                            "Try /login again."
                        )
                        await temp_client.disconnect()
                        _login_state.pop(user_id, None)
                        return

                except Exception as e:
                    await pass_msg.reply(f"❌ Error: `{e}`\nTry /login again.")
                    await temp_client.disconnect()
                    _login_state.pop(user_id, None)
                    return

        # ── Save session ──────────────────────────────────────
        if not otp_success:
            await temp_client.disconnect()
            _login_state.pop(user_id, None)
            return

        session_string = await temp_client.export_session_string()
        await db.save_session(user_id, session_string)
        await db.upsert_user(user_id, {"flood_count": 0})

        me = await temp_client.get_me()
        await temp_client.disconnect()
        _login_state.pop(user_id, None)

        await msg.reply(
            f"✅ **Logged in successfully!**\n\n"
            f"👤 **Name:** {me.first_name}\n"
            f"📱 **Phone:** `{me.phone_number}`\n\n"
            f"Now set target with /target and start with /forward 🚀"
        )

    # ── /logout ────────────────────────────────────────────────
    @bot.on_message(filters.command("logout") & filters.private)
    async def logout_cmd(client: Client, msg: Message):
        user_id = msg.from_user.id
        if not await db.get_session(user_id):
            await msg.reply("❌ You are not logged in.")
            return
        await stop_user_client(user_id)
        await db.delete_session(user_id)
        await msg.reply("✅ Logged out. Session deleted.")
