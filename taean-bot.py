import sys, subprocess, os, site, json, re, asyncio, base64
import discord
from discord import app_commands
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from keep_alive import keep_alive

site.main()
load_dotenv()
keep_alive()

# --- Initial.json 불러오기 함수 ---
def load_initial_replacements():
    filename = "Initial.json"
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Initial.json 로드 실패: {e}")
    return {}

INITIAL_REPLACEMENTS = load_initial_replacements()

private_key = os.getenv("private_key", "")
if private_key:
    private_key = private_key.replace("\\n", "\n")

google_credentials = {
    "type": "service_account",
    "project_id": "gen-lang-client-0463073512",
    "private_key_id": os.getenv("private_key_id"),
    "private_key": private_key,
    "client_email": "tts-bot-key@gen-lang-client-0463073512.iam.gserviceaccount.com",
    "client_id": "102784716861828821559",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/tts-bot-key%40gen-lang-client-0463073512.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

credentials = service_account.Credentials.from_service_account_info(google_credentials)

# --- 관리자 전용 채널 선택 셀렉트 메뉴 ---
class ChannelSelectView(discord.ui.ChannelSelect):
    def __init__(self, bot, guild_id, current_channel_id=None):
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder="📢 TTS 읽기 채널을 선택해 주세요"
        )
        self.bot = bot
        self.guild_id = guild_id

        if current_channel_id:
            try:
                self.default_values.append(
                    discord.SelectDefaultValue(id=current_channel_id, type=discord.SelectDefaultValueType.channel)
                )
            except (AttributeError, TypeError):
                pass

    async def callback(self, interaction: discord.Interaction):
        selected_channel = self.values[0]
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['channel_id'] = selected_channel.id
        settings['temp_channel_id'] = None
        await interaction.response.send_message(f"✅ {selected_channel.mention} 채널이 TTS 읽기 채널로 설정되었습니다.", ephemeral=True)

# --- 목소리 선택 셀렉트 메뉴 ---
class VoiceSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_voice):
        options = [
            discord.SelectOption(label="여성 1", value="ko-KR-Neural2-A", default=(current_voice == "ko-KR-Neural2-A")),
            discord.SelectOption(label="여성 2", value="ko-KR-Neural2-B", default=(current_voice == "ko-KR-Neural2-B")),
            discord.SelectOption(label="남성 1", value="ko-KR-Neural2-C", default=(current_voice == "ko-KR-Neural2-C")),
            discord.SelectOption(label="남성 2", value="ko-KR-Neural2-D", default=(current_voice == "ko-KR-Neural2-D")),
        ]
        super().__init__(placeholder="🎤 목소리를 선택해 주세요", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['voice_name'] = self.values[0]
        selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), self.values[0])
        await interaction.response.send_message(f"✅ TTS 목소리가 `{selected_label}`(으)로 변경되었습니다.", ephemeral=True)

# --- 속도 선택 셀렉트 메뉴 ---
class SpeedSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_speed):
        speeds = [
            ("0.25", "0.25"), ("0.5", "0.5"), ("0.75", "0.75"), ("1", "1.0"),
            ("1.25", "1.25"), ("1.5", "1.5"), ("1.75", "1.75"), ("2", "2.0")
        ]
        options = [
            discord.SelectOption(label=label, value=val, default=(current_speed == val))
            for label, val in speeds
        ]
        super().__init__(placeholder="⚡ 재생 속도를 선택해 주세요", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['speed'] = self.values[0]
        selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), self.values[0])
        await interaction.response.send_message(f"✅ TTS 속도가 `{selected_label}배속`(으)로 변경되었습니다.", ephemeral=True)

# --- TTS 설정 뷰 ---
class TTSSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, is_admin=False):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        
        settings = bot.get_guild_settings(guild_id)
        
        if is_admin:
            self.add_item(ChannelSelectView(bot, guild_id, settings.get('channel_id')))
        
        self.add_item(VoiceSelectView(bot, guild_id, settings.get('voice_name', 'ko-KR-Neural2-A')))
        self.add_item(SpeedSelectView(bot, guild_id, settings.get('speed', '1.0')))

class TTSBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.guild_settings = {}
        self.tts_client = build('texttospeech', 'v1', credentials=credentials)

    def get_guild_settings(self, guild_id):
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {
                'voice_name': 'ko-KR-Neural2-A',
                'speed': '1.0',
                'read_non_vc': False,
                'channel_id': None,
                'temp_channel_id': None
            }
        return self.guild_settings[guild_id]

    async def setup_hook(self):
        await self.tree.sync()

bot = TTSBot()

@bot.event
async def on_ready():
    activity = discord.Game(name="태안 촌놈들 관리 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"✅ 로그인 성공: {bot.user.name} (상태 메시지 설정 완료)")

async def remove_file_safely(filepath):
    await asyncio.sleep(1)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"❌ 파일 삭제 실패: {e}")

async def delete_message_after_delay(message, delay=10):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
    except Exception as e:
        print(f"❌ 메시지 자동 삭제 실패: {e}")

def generate_google_tts(client, text, voice_name):
    body = {
        'input': {'text': text},
        'voice': {'languageCode': 'ko-KR', 'name': voice_name},
        'audioConfig': {'audioEncoding': 'MP3'}
    }
    request = client.text().synthesize(body=body)
    response = request.execute()
    return base64.b64decode(response['audioContent'])

# --- 명령어 영역 ---

@bot.tree.command(name="입장", description="TTS 봇을 음성 채널에 수동으로 입장시킵니다.")
async def join_vc(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ 먼저 통화방(음성 채널)에 들어가 계셔야 합니다.", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client

    if vc:
        await vc.move_to(voice_channel)
    else:
        await voice_channel.connect(reconnect=True, timeout=60.0)

    settings = bot.get_guild_settings(interaction.guild_id)
    if not settings.get('channel_id'):
        settings['temp_channel_id'] = interaction.channel_id

    await interaction.response.send_message(f"🔊 {voice_channel.mention} 채널에 입장하였습니다.", ephemeral=True)

@bot.tree.command(name="퇴장", description="봇을 음성 채널에서 내보냅니다.")
async def leave_vc(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        settings = bot.get_guild_settings(interaction.guild_id)
        settings['temp_channel_id'] = None
        await interaction.response.send_message("👋 음성 채널에서 퇴장하였습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 현재 통화방에 들어가 있지 않습니다.", ephemeral=True)

@bot.tree.command(name="tts설정", description="TTS 목소리, 속도 및 전용 읽기 채널을 설정합니다.")
async def config_tts(interaction: discord.Interaction):
    permissions = interaction.channel.permissions_for(interaction.user)
    is_admin = permissions.manage_channels or permissions.administrator

    view = TTSSettingsView(bot, interaction.guild_id, is_admin=is_admin)
    await interaction.response.send_message("⚙️ 변경할 옵션을 아래 목록에서 선택해 주세요.", view=view, ephemeral=True)

# --- 메시지 감지 영역 ---

@bot.event
async def on_message(message):
    if message.guild is None or (message.author.bot and message.webhook_id is None):
        return

    settings = bot.get_guild_settings(message.guild.id)
    target_channel_id = settings.get('channel_id') or settings.get('temp_channel_id')

    if message.webhook_id is not None:
        if message.channel.id == target_channel_id:
            asyncio.create_task(delete_message_after_delay(message, 10))
        return

    # 커스텀 이모지 처리
    custom_emojis = re.findall(r"<(a?):(\w+):(\d+)>", message.content)
    if custom_emojis:
        try:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            new_content = message.content
            for is_animated, emoji_name, emoji_id in custom_emojis:
                ext = "gif" if is_animated else "png"
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=1024"
                new_content = new_content.replace(f"<{'a' if is_animated else ''}:{emoji_name}:{emoji_id}>", emoji_url)

            webhook = await message.channel.create_webhook(name="EmojiTransmitter")
            await webhook.send(
                content=new_content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            )
            await webhook.delete()

            if message.channel.id == target_channel_id:
                voice_client = message.guild.voice_client
                if voice_client and (message.author.voice and message.author.voice.channel == voice_client.channel or settings.get('read_non_vc')):
                    tts_text = f"{message.author.display_name}님이 이모지를 보냈습니다."
                    voice_name = settings.get('voice_name', 'ko-KR-Neural2-A')
                    speed = settings.get('speed', '1.0')
                    filename = f"tts_emoji_{message.id}.mp3"
                    
                    try:
                        audio_content = generate_google_tts(bot.tts_client, tts_text, voice_name)
                        with open(filename, "wb") as out:
                            out.write(audio_content)
                        
                        while voice_client.is_playing():
                            await asyncio.sleep(0.5)

                        def after_playing(error):
                            if error: print(f"❌ 재생 중 오류 발생: {error}")
                            asyncio.run_coroutine_threadsafe(remove_file_safely(filename), bot.loop)

                        ffmpeg_executable = "./ffmpeg.exe" if os.path.exists("./ffmpeg.exe") else "ffmpeg"
                        raw_audio = discord.FFmpegPCMAudio(filename, executable=ffmpeg_executable, options=f'-af atempo={speed}')
                        audio_source = discord.PCMVolumeTransformer(raw_audio, volume=0.25)
                        voice_client.play(audio_source, after=after_playing)
                    except Exception as e:
                        print(f"❌ 구글 TTS 생성 실패: {e}")
            return
        except Exception as e:
            print(f"❌ 이모지 전송 실패: {e}")

    # 일반 텍스트 및 지정 채널 판별
    if message.channel.id != target_channel_id: 
        return

    asyncio.create_task(delete_message_after_delay(message, 10))
    voice_client = message.guild.voice_client
    
    if not voice_client:
        if message.author.voice:
            voice_client = await message.author.voice.channel.connect(reconnect=True, timeout=60.0)
        else:
            return

    author_in_vc = message.author.voice and message.author.voice.channel == voice_client.channel
    if not author_in_vc and not settings.get('read_non_vc'): 
        return

    author_name = message.author.display_name
    tts_text = message.content.strip()

    if not tts_text:
        if message.stickers:
            tts_text = f"{author_name}님이 스티커를 보냈습니다."
        elif message.attachments:
            is_image = any(att.content_type and att.content_type.startswith('image') for att in message.attachments)
            file_type = "사진" if is_image else "파일"
            tts_text = f"{author_name}님이 {file_type}을 보냈습니다."
        else:
            return

    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, tts_text):
        if re.fullmatch(url_pattern, tts_text):
            tts_text = f"{author_name}님이 링크를 보냈습니다."
        else:
            tts_text = re.sub(url_pattern, "링크", tts_text)

    # --- Initial.json 기반 초성 및 줄임말 치환 ---
    for target, replacement in INITIAL_REPLACEMENTS.items():
        pattern = rf"\b({re.escape(target)})\b"
        tts_text = re.sub(pattern, replacement, tts_text)

    filename = f"tts_{message.id}.mp3"
    try:
        audio_content = generate_google_tts(bot.tts_client, tts_text, settings.get('voice_name', 'ko-KR-Neural2-A'))
        with open(filename, "wb") as out:
            out.write(audio_content)
    except Exception as e:
        print(f"❌ 구글 TTS 생성 실패: {e}")
        return

    while voice_client.is_playing(): 
        await asyncio.sleep(0.5)

    def after_playing(error):
        if error: print(f"❌ 재생 중 오류 발생: {error}")
        asyncio.run_coroutine_threadsafe(remove_file_safely(filename), bot.loop)

    ffmpeg_executable = "./ffmpeg.exe" if os.path.exists("./ffmpeg.exe") else "ffmpeg"
    raw_audio = discord.FFmpegPCMAudio(filename, executable=ffmpeg_executable, options=f"-af atempo={settings.get('speed', '1.0')}")
    audio_source = discord.PCMVolumeTransformer(raw_audio, volume=0.25)
    voice_client.play(audio_source, after=after_playing)

bot.run(os.getenv("DISCORD_TOKEN"))
