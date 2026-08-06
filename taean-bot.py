import os, discord, asyncio
from dotenv import load_dotenv
from discord.ext import commands
from keep_alive import keep_alive

load_dotenv()
keep_alive()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(command_prefix="!", help_command=None, intents=intents)

        # .env 파일에서 Gemini API 키 로드
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        self.guild_settings = {}
        self.user_settings = {}

    def get_guild_settings(self, guild_id: int) -> dict:
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {
                'read_non_vc': False,           
                'channel_id': None,
                'temp_channel_id': None         
            }
        return self.guild_settings[guild_id]

    def get_user_settings(self, user_id: int) -> dict:
        if user_id not in self.user_settings:
            self.user_settings[user_id] = {
                'voice_name': 'tc_69f2e455ea79fd197aa0476f',
                'tempo': 1.0,
                'pitch': 0,
                'emotion_preset': 'normal',
                'emotion_intensity': 1.0,
            }
        return self.user_settings[user_id]

    async def setup_hook(self):
        initial_extensions = [
            'cogs.tts',
            'cogs.emoji',
            'cogs.meetup',
            'cogs.nanobanana'  # NanoBanana Cog 추가
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    # 슬래시 명령어를 디스코드 서버와 동기화
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    activity = discord.Game(name="태안 촌놈들 관리 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)

bot.run(os.getenv("DISCORD_TOKEN"))
