"""
database.py — Async MongoDB layer using Motor
All DB operations for users, sessions, tasks.
"""
import motor.motor_asyncio
from config import MONGO_URI

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["tgforward"]

users_col = db["users"]
tasks_col = db["tasks"]


# ── User / Session ─────────────────────────────────────────────

async def save_session(user_id: int, session_string: str):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"session_string": session_string}},
        upsert=True
    )

async def get_session(user_id: int) -> str | None:
    doc = await users_col.find_one({"user_id": user_id})
    return doc.get("session_string") if doc else None

async def delete_session(user_id: int):
    await users_col.update_one(
        {"user_id": user_id},
        {"$unset": {"session_string": ""}}
    )

async def get_user(user_id: int) -> dict | None:
    return await users_col.find_one({"user_id": user_id})

async def upsert_user(user_id: int, data: dict):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": data},
        upsert=True
    )


# ── Target ────────────────────────────────────────────────────

async def set_target(user_id: int, target: str):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"target": target}},
        upsert=True
    )

async def get_target(user_id: int) -> str | None:
    doc = await users_col.find_one({"user_id": user_id})
    return doc.get("target") if doc else None


# ── Flood Count ────────────────────────────────────────────────

async def get_flood_count(user_id: int) -> int:
    doc = await users_col.find_one({"user_id": user_id})
    return doc.get("flood_count", 0) if doc else 0

async def increment_flood_count(user_id: int) -> int:
    await users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"flood_count": 1}},
        upsert=True
    )
    return await get_flood_count(user_id)

async def reset_flood_count(user_id: int):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"flood_count": 0}}
    )


# ── Task Progress (Resume Support) ────────────────────────────

async def save_progress(user_id: int, last_msg_id: int, forwarded: int,
                        source_chat: str = "", start_msg_id: int = 0):
    await tasks_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "last_msg_id": last_msg_id,
            "forwarded": forwarded,
            "source_chat": source_chat,
            "start_msg_id": start_msg_id,
            "active": True
        }},
        upsert=True
    )

async def get_progress(user_id: int) -> dict | None:
    return await tasks_col.find_one({"user_id": user_id})

async def clear_progress(user_id: int):
    await tasks_col.delete_one({"user_id": user_id})

async def set_task_active(user_id: int, active: bool):
    await tasks_col.update_one(
        {"user_id": user_id},
        {"$set": {"active": active}},
        upsert=True
    )
