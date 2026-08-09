import os, discord, asyncio
from dotenv import load_dotenv
from discord.ext import commands
from keep_alive import keep_alive
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
keep_alive()

# MongoDB 연결
MONGO_URI = os.getenv("MONGODB_URI")
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["taean_bot_db"]

guilds_col = db["guild_settings"]
users_col = db["user_settings"]

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", help_command=None, intents=intents)

    # --- 서버 설정 DB 조회 / 저장 ---
    async def get_guild_settings(self, guild_id: int) -> dict:
        doc = await guilds_col.find_one({"guild_id": str(guild_id)})
        if not doc:
            return {
                'guild_id': str(guild_id),
                'read_non_vc': False,           
                'channel_id': None,
                'temp_channel_id': None         
            }
        return doc

    async def update_guild_settings(self, guild_id: int, settings: dict):
        update_data = settings.copy()
        update_data.pop('_id', None)
        
        await guilds_col.update_one(
            {"guild_id": str(guild_id)},
            {"$set": update_data},
            upsert=True
        )

    # --- 유저 설정 DB 조회 / 저장 ---
    async def get_user_settings(self, user_id: int) -> dict:
        doc = await users_col.find_one({"user_id": str(user_id)})
        if not doc:
            return {
                'user_id': str(user_id),
                'voice_name': 'tc_69f2e455ea79fd197aa0476f',
                'tempo': 1.0,
                'pitch': 0,
                'emotion_preset': 'normal',
                'emotion_intensity': 1.0,
            }
        return doc

    async def update_user_settings(self, user_id: int, settings: dict):
        update_data = settings.copy()
        update_data.pop('_id', None)
        
        await users_col.update_one(
            {"user_id": str(user_id)},
            {"$set": update_data},
            upsert=True
        )

    async def setup_hook(self):
        initial_extensions = [
            'cogs.tts',
            'cogs.emoji',
            'cogs.meetup',
            'cogs.teams',       # 팀 나누기
            'cogs.ladder',      # 사다리 타기
            'cogs.dice',        # 주사위 / 골라줘
            'cogs.voice_pick',  # 음성 채널 랜덤 지목
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    activity = discord.Game(name="태안 촌놈들 관리 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)

bot.run(os.getenv("DISCORD_TOKEN"))
