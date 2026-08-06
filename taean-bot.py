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
            'cogs.meetup'
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
            except Exception:
                pass

bot = MyBot()

@bot.event
async def on_ready():
    activity = discord.Game(name="태안 촌놈들 관리 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)

bot.run(os.getenv("DISCORD_TOKEN"))
