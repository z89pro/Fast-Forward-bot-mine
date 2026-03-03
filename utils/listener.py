"""
utils/listener.py
A lightweight, natively-async listener to replace pyromod for Pyrogram v2.
Avoids the "Future attached to different loop" and thread executor bugs.
"""
import asyncio
from pyrogram import Client
from pyrogram.handlers import MessageHandler

# Store pending listeners: list of (future, filter_callable)
_pending_listens = []

async def _listen_dispatcher(client: Client, message, *args):
    global _pending_listens
    # Check all pending listeners safely
    for item in list(_pending_listens):
        future, flt = item
        try:
            # In Pyrogram v2, filters are callable async functions or normal functions
            passed = await flt(client, message) if flt else True
            if passed:
                if not future.done():
                    future.set_result(message)
                if item in _pending_listens:
                    _pending_listens.remove(item)
                message.stop_propagation()
                return
        except Exception:
            continue
    
    # If no active listener matched, let it pass to group 0
    message.continue_propagation()

def patch_client():
    """Patch the listen method onto pyrogram.Client"""
    async def listen(self: Client, filters=None, timeout=None):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        _pending_listens.append((future, filters))
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            # Ensure cleanup on timeout
            _pending_listens[:] = [(f, flt) for f, flt in _pending_listens if f != future]
            raise asyncio.TimeoutError()

    Client.listen = listen

def register_listener(bot: Client):
    """Register the interceptor on group -1 to run before normal handlers."""
    bot.add_handler(MessageHandler(_listen_dispatcher), group=-1)
