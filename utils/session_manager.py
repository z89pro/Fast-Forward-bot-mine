"""
utils/session_manager.py
Manages per-user Pyrogram clients (StringSession).
"""
import asyncio
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, PeerIdInvalid
from config import API_ID, API_HASH
import database as db


async def resolve_chat(client: Client, chat_id: str):
    """
    Resolves a chat by ID or username, with a dialog-scan fallback.

    Pyrogram raises PeerIdInvalid for private channels/groups if it
    hasn't "seen" that peer before. The fix: scan the user's dialogs
    to load the peer into Pyrogram's internal cache, then retry.

    Returns the Chat object, or raises Exception with a clear message.
    """
    # Normalize: convert numeric string to int
    try:
        chat_input = int(chat_id) if chat_id.lstrip('-').isdigit() else chat_id
    except Exception:
        chat_input = chat_id

    # First attempt
    try:
        return await client.get_chat(chat_input)
    except PeerIdInvalid:
        pass  # Peer not cached yet — try dialog scan
    except Exception as e:
        raise Exception(str(e))

    # Dialog scan fallback: iterate all dialogs to cache peers
    target_id = str(chat_id).replace("-100", "")  # strip -100 prefix for comparison
    async for dialog in client.get_dialogs():
        dlg_id = str(dialog.chat.id)
        if dlg_id == str(chat_id) or dlg_id.lstrip('-') == target_id:
            return dialog.chat  # Found and cached

    # Last attempt after dialog scan
    try:
        return await client.get_chat(chat_input)
    except Exception:
        raise Exception(
            f"Cannot find chat `{chat_id}`.\n\n"
            "Make sure your **logged-in Telegram account** is a member of this chat.\n"
            "If it's a private group, forward any message from it to @userinfobot to get the correct ID."
        )

# In-memory client cache: {user_id: Client}
_clients: dict[int, Client] = {}
_locks: dict[int, asyncio.Lock] = {}


def _get_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _locks:
        _locks[user_id] = asyncio.Lock()
    return _locks[user_id]


async def get_user_client(user_id: int) -> Client | None:
    """
    Returns an authenticated Pyrogram client for the given user.
    Uses cached client if already connected, else creates from StringSession.
    Returns None if no session found or session is invalid.
    """
    async with _get_lock(user_id):
        # Return cached client if already connected
        if user_id in _clients and _clients[user_id].is_connected:
            return _clients[user_id]

        session_string = await db.get_session(user_id)
        if not session_string:
            return None

        try:
            client = Client(
                name=f"user_{user_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True,
            )
            await client.start()
            _clients[user_id] = client
            return client
        except (AuthKeyUnregistered, UserDeactivated):
            # Session expired — clean up
            await db.delete_session(user_id)
            return None
        except Exception:
            return None


async def stop_user_client(user_id: int):
    """Disconnects and removes a user's client from the cache."""
    async with _get_lock(user_id):
        client = _clients.pop(user_id, None)
        if client and client.is_connected:
            try:
                await client.stop()
            except Exception:
                pass


async def create_temp_client(user_id: int) -> Client:
    """
    Creates a temporary Pyrogram client for OTP login flow.
    Name is unique per user_id so concurrent logins don't conflict.
    Caller is responsible for stopping it.
    """
    return Client(
        name=f"temp_login_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
