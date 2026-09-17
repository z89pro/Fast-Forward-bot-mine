from os import environ 
from config import Config
import motor.motor_asyncio
from pymongo import MongoClient

async def mongodb_version():
    try:
        x = MongoClient(Config.DATABASE_URI, serverSelectionTimeoutMS=5000)
        version = x.server_info().get('version', 'Unknown')
        x.close()
        return version
    except Exception:
        return "Unknown"

class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels 
        self.live = self.db.live_forwards 
        
    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )      
                
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount

    async def total_channels(self):
        count = await self.chl.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})
    
    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})
 
    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    async def update_configs(self, id, configs):
        await self.col.update_one({'id': int(id)}, {'$set': {'configs': configs}})
         
    async def get_configs(self, id):
        default = {
            'caption': None,
            'duplicate': True,
            'forward_tag': False,
            'file_size': 0,
            'size_limit': None,
            'extension': None,
            'keywords': None,
            'protect': None,
            'button': None,
            'db_uri': None,
            'clean_caption': False,
            'replace_words': {},
            'dump_channel': None,
            'dump_enabled': False,
            'speed_cfg': {
               'mode': 'fast',
               'delay': 1.0,
               'jitter': True,
               'batch_size': 100
            },
            'filters': {
               'poll': True,
               'text': True,
               'audio': True,
               'voice': True,
               'video': True,
               'photo': True,
               'document': True,
               'animation': True,
               'sticker': True
            },
            'course_seller_mode': False,
            'auto_course_list': False,
            'auto_numbering': False,
            'username_remover': False,
            'username_replacer': None,
            'link_remover': False,
            'link_replacer': None,
            'hidden_link_remover': False,
            'hidden_link_replacer': None,
            'remove_tags': True,
            'upload_type': 'media',
            'watermark_text': None
        }
        user = await self.col.find_one({'id':int(id)})
        if user:
            configs = user.get('configs', default)
            for k, v in default.items():
                if k not in configs:
                    configs[k] = v
            if 'speed_cfg' not in configs or not isinstance(configs['speed_cfg'], dict):
                configs['speed_cfg'] = default['speed_cfg']
            if 'replace_words' not in configs or not isinstance(configs['replace_words'], dict):
                configs['replace_words'] = {}
            return configs
        return default 
       
    async def add_live_forward(self, user_id, from_chat, to_chat, from_title="Source", to_title="Target"):
        await self.live.delete_many({'user_id': int(user_id), 'from_chat': str(from_chat)})
        return await self.live.insert_one({
            'user_id': int(user_id),
            'from_chat': str(from_chat),
            'to_chat': str(to_chat),
            'from_title': str(from_title),
            'to_title': str(to_title),
            'active': True
        })

    async def remove_live_forward(self, user_id, from_chat):
        return await self.live.delete_many({'user_id': int(user_id), 'from_chat': str(from_chat)})

    async def get_user_live_forwards(self, user_id):
        cursor = self.live.find({'user_id': int(user_id)})
        return [doc async for doc in cursor]

    async def get_all_active_live_forwards(self):
        cursor = self.live.find({'active': True})
        return [doc async for doc in cursor]

    async def get_admin_dump(self):
        doc = await self.db.admin_config.find_one({'_id': 'dump_settings'})
        if doc:
            return doc.get('dump_channel'), doc.get('dump_enabled', False)
        return (Config.DUMP_CHANNEL if Config.DUMP_CHANNEL else None), bool(Config.DUMP_CHANNEL)

    async def update_admin_dump(self, dump_channel, dump_enabled=True):
        await self.db.admin_config.update_one(
            {'_id': 'dump_settings'},
            {'$set': {'dump_channel': dump_channel, 'dump_enabled': dump_enabled}},
            upsert=True
        ) 
       
    async def add_bot(self, datas):
       await self.bot.delete_many({'user_id': int(datas['user_id'])})
       await self.bot.insert_one(datas)

    async def remove_bot(self, user_id):
       await self.bot.delete_many({'user_id': int(user_id)})
      
    async def get_bot(self, user_id: int):
       bot = await self.bot.find_one({'user_id': int(user_id)})
       return bot if bot else None
                                          
    async def is_bot_exist(self, user_id):
       bot = await self.bot.find_one({'user_id': int(user_id)})
       return bool(bot)
                                          
    async def in_channel(self, user_id: int, chat_id: int) -> bool:
       channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       return bool(channel)
    
    async def add_channel(self, user_id: int, chat_id: int, title, username):
       channel = await self.in_channel(user_id, chat_id)
       if channel:
         return False
       return await self.chl.insert_one({"user_id": user_id, "chat_id": chat_id, "title": title, "username": username})
    
    async def remove_channel(self, user_id: int, chat_id: int):
       channel = await self.in_channel(user_id, chat_id )
       if not channel:
         return False
       return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})
    
    async def get_channel_details(self, user_id: int, chat_id: int):
       return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       
    async def get_user_channels(self, user_id: int):
       channels = self.chl.find({"user_id": int(user_id)})
       return [channel async for channel in channels]
     
    async def get_filters(self, user_id):
       filters = []
       filter = (await self.get_configs(user_id))['filters']
       for k, v in filter.items():
          if v == False:
            filters.append(str(k))
       return filters
              
    async def add_frwd(self, user_id):
       return await self.nfy.insert_one({'user_id': int(user_id)})
    
    async def rmve_frwd(self, user_id=0, all=False):
       data = {} if all else {'user_id': int(user_id)}
       return await self.nfy.delete_many(data)
    
    async def get_all_frwd(self):
       return self.nfy.find({})
    
db = Database(Config.DATABASE_URI, Config.DATABASE_NAME)

# ── Backwards Compatibility Module-Level Helpers ─────────────
async def get_session(user_id: int):
    b = await db.get_bot(user_id)
    return b.get("session") if (b and not b.get("is_bot")) else None

async def save_session(user_id: int, session_string: str):
    await db.add_bot({
        "user_id": int(user_id),
        "name": "UserBot",
        "username": "UserBot",
        "session": session_string,
        "is_bot": False
    })

async def delete_session(user_id: int):
    await db.remove_bot(user_id)

async def get_target(user_id: int):
    channels = await db.get_user_channels(user_id)
    return channels[0]["chat_id"] if channels else None

async def set_target(user_id: int, target: str):
    cid = int(target) if str(target).lstrip("-").isdigit() else target
    await db.add_channel(user_id, cid, str(target), str(target))

