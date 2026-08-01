import sys, subprocess, os, site, json, re, asyncio, time, discord
from discord import app_commands
from dotenv import load_dotenv
from typecast import Typecast
from keep_alive import keep_alive

site.main()
load_dotenv()

keep_alive()

# --- 환경변수 로드 및 Typecast 클라이언트 생성 ---
TTS_API = os.getenv("TTS_API")
if not TTS_API:
    print("⚠️ 경고: .env 파일에 TTS_API 키가 설정되지 않았습니다.")

tc = Typecast(api_key=TTS_API)

# --- 채팅 메시지 변환용 딕셔너리 ---
INITIAL_REPLACEMENTS = {
    "ㅎㅇ": "하이",
    "ㅂㅇ": "바이",
    "ㅂㅂ": "바바",
    "ㄳ": "감사",
    "ㄱㅅ": "감사",
    "ㄷㄷ": "덜덜",
    "ㅇㅈ": "인정",
    "ㄹㅇ": "레알",
    "ㅅㄱ": "수고",
    "?": "응?",
    "ㅇ": "응",
    "ㅇㅇ": "응응",
    "ㅅㅅ": "섹스",
    "ㅎㅎ": "히히",
    "ㄴㄴ": "노노",
    "ㅈㄹ": "지랄",
    "ㅇㅋ": "오키"
}

# --- Typecast SDK 호출 동기 함수 ---
def generate_typecast_tts(text: str, actor_id: str, speed: str) -> bytes:
    if not TTS_API:
        raise ValueError("TTS_API가 설정되지 않았습니다.")

    try:
        xspeed_val = float(speed)
    except ValueError:
        xspeed_val = 1.0

    print(f"🎙 [Typecast SDK 요청] Actor ID: {actor_id} | Speed: {xspeed_val} | Text: '{text}'")

    # Typecast 공식 SDK 오디오 생성 호출
    audio = tc.speak(
        text=text,
        actor_id=actor_id,
        xspeed=xspeed_val,
        lang="auto"
    )

    if not audio or not audio.bytes:
        raise Exception("Typecast SDK로부터 음성 데이터를 받아오지 못했습니다.")

    print(f"✅ [Typecast SDK 성공] 오디오 변환 완료 ({len(audio.bytes)} bytes)")
    return audio.bytes


# --- 관리자 전용 채널 선택 셀렉트 메뉴 ---
class ChannelSelectView(discord.ui.ChannelSelect):
    def __init__(self, bot, guild_id, current_channel_id=None):
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder="TTS 채널을 선택해 주세요."
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
        await interaction.response.send_message(f"✅ {selected_channel.mention} 채널이 TTS 채널로 설정되었습니다.", ephemeral=True)


# --- 목소리 선택 셀렉트 메뉴 (찬구 전용) ---
class VoiceSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_voice):
        options = [
            discord.SelectOption(
                label="남성 - 찬구", 
                value="tc_5c547544fcfee90007fed455", 
                default=(current_voice == "tc_5c547544fcfee90007fed455")
            ),
        ]
        super().__init__(placeholder="목소리 설정", options=options)
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
            ("0.5 배속", "0.5"), ("0.75 배속", "0.75"), ("1 배속", "1.0"),
            ("1.25 배속", "1.25"), ("1.5 배속", "1.5"), ("2 배속", "2.0")
        ]
        options = [
            discord.SelectOption(label=label, value=val, default=(current_speed == val))
            for label, val in speeds
        ]
        super().__init__(placeholder="재생 속도를 선택해 주세요.", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['speed'] = self.values[0]
        selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), self.values[0])
        await interaction.response.send_message(f"✅ TTS 속도가 `{selected_label}`(으)로 변경되었습니다.", ephemeral=True)


# --- TTS 설정 뷰 ---
class TTSSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, is_admin=False):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id

        settings = bot.get_guild_settings(guild_id)

        if is_admin:
            self.add_item(ChannelSelectView(bot, guild_id, settings.get('channel_id')))

        self.add_item(VoiceSelectView(bot, guild_id, settings.get('voice_name', 'tc_5c547544fcfee90007fed455')))
        self.add_item(SpeedSelectView(bot, guild_id, settings.get('speed', '1.0')))


class TTSBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.guild_settings = {}

    def get_guild_settings(self, guild_id):
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = {
                'voice_name': 'tc_5c547544fcfee90007fed455',
                'speed': '1.0',
                'read_non_vc': False,
                'channel_id': None,
                'temp_channel_id': None
            }
        return self.guild_settings[guild_id]

    async def setup_hook(self):
        await self.tree.sync()

bot = TTSBot()

async def play_tts(vc, filename):
    """음성 재생 공통 함수"""
    ffmpeg_executable = "./ffmpeg.exe" if os.path.exists("./ffmpeg.exe") else "ffmpeg"
    
    ffmpeg_options = {
        'options': '-vn',
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }

    try:
        raw_audio = discord.FFmpegPCMAudio(
            filename,
            executable=ffmpeg_executable,
            **ffmpeg_options
        )
        audio_source = discord.PCMVolumeTransformer(raw_audio, volume=1.0)
        
        def after_playing(error):
            if error:
                print(f"❌ 재생 중 디스코드 오디오 오류: {error}")
            asyncio.run_coroutine_threadsafe(remove_file_safely(filename), bot.loop)

        vc.play(audio_source, after=after_playing)
    except Exception as e:
        print(f"❌ FFmpeg 재생 예외 발생: {e}")


@bot.event
async def on_ready():
    activity = discord.Game(name="태안 촌놈들 관리 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f"✅ 로그인 성공: {bot.user.name} (상태 메시지 설정 완료)")


# --- 음성 상태 변경 이벤트 ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    settings = bot.get_guild_settings(member.guild.id)
    vc = member.guild.voice_client

    if before.channel is None and after.channel is not None:
        if vc and after.channel == vc.channel:
            tts_text = f"{member.display_name} 어하"
            voice_name = settings.get('voice_name', 'tc_5c547544fcfee90007fed455')
            speed = settings.get('speed', '1.0')
            filename = f"tts_join_{member.id}_{int(time.time())}.mp3"

            try:
                audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, voice_name, speed)
                with open(filename, "wb") as out:
                    out.write(audio_content)

                while vc.is_playing():
                    await asyncio.sleep(0.3)

                await play_tts(vc, filename)
            except Exception as e:
                print(f"❌ 입장 TTS 생성 및 재생 실패: {e}")

    elif before.channel is not None and after.channel is None:
        if vc and before.channel == vc.channel:
            tts_text = f"{member.display_name} 어바"
            voice_name = settings.get('voice_name', 'tc_5c547544fcfee90007fed455')
            speed = settings.get('speed', '1.0')
            filename = f"tts_leave_{member.id}_{int(time.time())}.mp3"

            try:
                audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, voice_name, speed)
                with open(filename, "wb") as out:
                    out.write(audio_content)

                while vc.is_playing():
                    await asyncio.sleep(0.3)

                await play_tts(vc, filename)
            except Exception as e:
                print(f"❌ 퇴장 TTS 생성 및 재생 실패: {e}")

    if not vc or not vc.is_connected():
        return

    human_members = [m for m in vc.channel.members if not m.bot]
    if len(human_members) == 0:
        await vc.disconnect()
        settings['temp_channel_id'] = None
        print(f"⚠ {member.guild.name} 서버 음성 채널에 아무도 없어서 자동 퇴장했습니다.")

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


# --- 명령어 영역 ---

@bot.tree.command(name="입장", description="TTS 봇을 음성 채널에 입장시킵니다.")
async def join_vc(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ 먼저 음성 채널에 입장해야 합니다.", ephemeral=True)
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

    await interaction.response.send_message(f"🔊 {voice_channel.mention} 채널이 설정되었습니다.", ephemeral=True)

@bot.tree.command(name="퇴장", description="봇을 음성 채널에서 내보냅니다.")
async def leave_vc(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        settings = bot.get_guild_settings(interaction.guild_id)
        settings['temp_channel_id'] = None
        await interaction.response.send_message("✔ 음성 채널에서 퇴장하였습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 현재 통화방에 입장해 있지 않습니다.", ephemeral=True)

@bot.tree.command(name="tts설정", description="TTS 목소리, 속도 및 전용 채널을 설정합니다.")
async def config_tts(interaction: discord.Interaction):
    permissions = interaction.channel.permissions_for(interaction.user)
    is_admin = permissions.manage_channels or permissions.administrator

    view = TTSSettingsView(bot, interaction.guild_id, is_admin=is_admin)
    await interaction.response.send_message("", view=view, ephemeral=True)


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
                    voice_name = settings.get('voice_name', 'tc_5c547544fcfee90007fed455')
                    speed = settings.get('speed', '1.0')
                    filename = f"tts_emoji_{message.id}.mp3"

                    try:
                        audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, voice_name, speed)
                        with open(filename, "wb") as out:
                            out.write(audio_content)

                        while voice_client.is_playing():
                            await asyncio.sleep(0.3)

                        await play_tts(voice_client, filename)
                    except Exception as e:
                        print(f"❌ Typecast SDK 생성 실패: {e}")
            return
        except Exception as e:
            print(f"❌ 이모지 전송 실패: {e}")

    if message.channel.id != target_channel_id: 
        return

    asyncio.create_task(delete_message_after_delay(message, 10))
    voice_client = message.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        if message.author.voice:
            voice_client = await message.author.voice.channel.connect(reconnect=True, timeout=60.0)
        else:
            return

    author_in_vc = message.author.voice and message.author.voice.channel == voice_client.channel
    if not author_in_vc and not settings.get('read_non_vc'): 
        return

    author_name = message.author.display_name
    raw_text = message.content.strip()

    # --- 1. 유저 언급(<@ID>, <@!ID>) 치환 ---
    def replace_user_mention(match):
        user_id = int(match.group(1))
        member = message.guild.get_member(user_id)
        return member.display_name if member else "알 수 없는 유저"

    raw_text = re.sub(r"<@!?(\d+)>", replace_user_mention, raw_text)

    # --- 2. 채널 언급(<#ID>) 치환 ---
    def replace_channel_mention(match):
        channel_id = int(match.group(1))
        channel = message.guild.get_channel(channel_id)
        return channel.name if channel else "알 수 없는 채널"

    raw_text = re.sub(r"<#(\d+)>", replace_channel_mention, raw_text)

    if not raw_text:
        if message.stickers:
            tts_text = f"{author_name}님이 스티커를 보냈습니다."
        elif message.attachments:
            is_image = any(att.content_type and att.content_type.startswith('image') for att in message.attachments)
            file_type = "사진" if is_image else "파일"
            tts_text = f"{author_name}님이 {file_type}을 보냈습니다."
        else:
            return
    else:
        if raw_text in INITIAL_REPLACEMENTS:
            tts_text = INITIAL_REPLACEMENTS[raw_text]
        else:
            words = raw_text.split()
            replaced_words = []
            for word in words:
                clean_word = re.sub(r'[^가-힣a-zA-Z0-9?]', '', word)
                if clean_word in INITIAL_REPLACEMENTS:
                    replaced_word = word.replace(clean_word, INITIAL_REPLACEMENTS[clean_word])
                    replaced_words.append(replaced_word)
                else:
                    replaced_words.append(word)
            tts_text = " ".join(replaced_words)

    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, tts_text):
        if re.fullmatch(url_pattern, tts_text):
            tts_text = f"{author_name}님이 링크를 보냈습니다."
        else:
            tts_text = re.sub(url_pattern, "링크", tts_text)

    filename = f"tts_{message.id}.mp3"
    try:
        audio_content = await asyncio.to_thread(
            generate_typecast_tts,
            tts_text,
            settings.get('voice_name', 'tc_5c547544fcfee90007fed455'),
            settings.get('speed', '1.0')
        )
        with open(filename, "wb") as out:
            out.write(audio_content)
    except Exception as e:
        print(f"❌ Typecast SDK 생성 실패: {e}")
        return

    while voice_client.is_playing(): 
        await asyncio.sleep(0.3)

    await play_tts(voice_client, filename)

bot.run(os.getenv("DISCORD_TOKEN"))
