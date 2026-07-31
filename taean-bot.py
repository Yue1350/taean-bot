import sys, subprocess, os, site, json, re, asyncio, discord
from discord import app_commands
from dotenv import load_dotenv
from google.cloud import texttospeech

site.main()
load_dotenv()

google_credentials = {
    "type": "service_account"
    "project_id": "gen-lang-client-0463073512",
    "private_key_id": os.getenv("private_key_id"),
    "private_key": os.getenv("private_key").replace("\\n", "\n"),  # 줄바꿈 문자 복원
    "client_email": "tts-bot-key@gen-lang-client-0463073512.iam.gserviceaccount.com",
    "client_id": "102784716861828821559",
    "auth_uri": os.getenv("auth_uri"),
    "token_uri": os.getenv("token_uri"),
    "auth_provider_x509_cert_url": os.getenv("auth_provider_x509_cert_url"),
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/tts-bot-key%40gen-lang-client-0463073512.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# 구글 TTS 클라이언트에 인증 정보 직접 주입
from google.oauth2 import service_account
credentials = service_account.Credentials.from_service_account_info(google_credentials)
class TTSBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.guild_settings = {} # {guild_id: {'channel_id': int, 'voice_name': str, 'speed': str, 'read_non_vc': bool}}
        self.tts_client = texttospeech.TextToSpeechClient(credentials=credentials)

    async def setup_hook(self):
        await self.tree.sync()

bot = TTSBot()

# --- 봇 준비 완료 시 상태 메시지 설정 ---
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
    except discord.NotFound:
        pass
    except discord.Forbidden:
        print("❌ 메시지 삭제 권한이 없습니다.")
    except Exception as e:
        print(f"❌ 메시지 자동 삭제 실패: {e}")

def generate_google_tts(client, text, voice_name):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="ko-KR", name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

# --- 슬래시 명령어 설정 ---
@bot.tree.command(name="tts설정", description="현재 채널을 TTS 읽기 채널로 지정합니다.")
async def set_tts_channel(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in bot.guild_settings:
        bot.guild_settings[guild_id] = {
            'voice_name': 'ko-KR-Neural2-A',
            'speed': '1.0',
            'read_non_vc': False
        }
    bot.guild_settings[guild_id]['channel_id'] = interaction.channel_id
    await interaction.response.send_message(f"✅ {interaction.channel.mention} 채널이 TTS 읽기 채널로 설정되었습니다.", ephemeral=True)

@bot.tree.command(name="퇴장", description="봇을 음성 채널에서 내보냅니다.")
async def leave_vc(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("👋 음성 채널에서 퇴장하였습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 연결된 음성 채널이 없습니다.", ephemeral=True)

# --- 메시지 이벤트 ---
@bot.event
async def on_message(message):
    # DM 메시지이거나 guild 정보가 없는 경우 무시
    if message.guild is None:
        return

    if message.author.bot and message.webhook_id is None:
        return

    # 웹훅 메시지 삭제 처리
    if message.webhook_id is not None:
        settings = bot.guild_settings.get(message.guild.id, {})
        if message.channel.id == settings.get('channel_id'):
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

            settings = bot.guild_settings.get(message.guild.id, {})
            if message.channel.id == settings.get('channel_id'):
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
                        # 기본 음량 25% (0.25) 설정
                        audio_source = discord.PCMVolumeTransformer(raw_audio, volume=0.25)
                        voice_client.play(audio_source, after=after_playing)
                    except Exception as e:
                        print(f"❌ 구글 TTS 생성 실패: {e}")
            return
        except Exception as e:
            print(f"❌ 이모지 전송 실패: {e}")

    # TTS 일반 채널 메시지 처리
    if message.guild.id not in bot.guild_settings: 
        return
        
    settings = bot.guild_settings[message.guild.id]
    if message.channel.id != settings.get('channel_id'): 
        return

    asyncio.create_task(delete_message_after_delay(message, 10))
    voice_client = message.guild.voice_client
    
    # 음성 채널 입장 처리
    if not voice_client:
        if message.author.voice:
            voice_client = await message.author.voice.channel.connect()
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

    # URL 처리
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, tts_text):
        if re.fullmatch(url_pattern, tts_text):
            tts_text = f"{author_name}님이 링크를 보냈습니다."
        else:
            tts_text = re.sub(url_pattern, "링크", tts_text)

    # 약어 변환
    tts_text = re.sub(r'\b(ㅎㅇ)\b', '하이', tts_text)
    tts_text = re.sub(r'\b(ㅂㅇ)\b', '바이', tts_text)
    tts_text = re.sub(r'\b(ㄳ|ㄱㅅ)\b', '감사', tts_text)
    tts_text = re.sub(r'\b(ㄷㄷ)\b', '덜덜', tts_text)
    tts_text = re.sub(r'\b(ㅇㅈ)\b', '인정', tts_text)
    tts_text = re.sub(r'\b(ㄹㅇ)\b', '레알', tts_text)

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
    # 기본 음량 25% (0.25) 설정
    audio_source = discord.PCMVolumeTransformer(raw_audio, volume=0.25)
    voice_client.play(audio_source, after=after_playing)

bot.run(os.getenv("DISCORD_TOKEN"))
