import os, discord, asyncio
from dotenv import load_dotenv
from keep_alive import keep_alive

# 1. 환경 변수 및 24시간 서버 유지 설정
load_dotenv()
keep_alive()

# 2. 디스코드 커스텀 봇 클래스 정의
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)

        self.tree = discord.app_commands.CommandTree(self)

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

        await self.tree.sync()

# 3. 봇 인스턴스 생성 및 이벤트 핸들러
bot = MyBot()

@bot.event
async def on_ready():
    activity = discord.Game(name="태안 촌놈들 관리 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
    print(f"✅ 봇이 정상적으로 로그인 되었습니다.")

# 4. 봇 실행
bot.run(os.getenv("DISCORD_TOKEN"))
