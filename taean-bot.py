import sys, subprocess, os, site, json, re, asyncio, time, discord
from discord import app_commands
from dotenv import load_dotenv
from typecast import Typecast
from typecast.models import TTSRequest, Output, PresetPrompt
from keep_alive import keep_alive
from korean_romanizer.romanizer import Romanizer

site.main()
load_dotenv()

keep_alive()

# --- 1. Typecast 클라이언트 엄격한 초기화 ---
print("🔑 Typecast 클라이언트 초기화를 시도합니다...")
client = Typecast()
print("✅ Typecast 클라이언트 초기화 성공!")

# --- 채팅 메시지 변환용 딕셔너리 ---
INITIAL_REPLACEMENTS = {
    "ㅎㅇ": "하이", "ㅂㅇ": "바이", "ㅂㅂ": "바바",
    "ㄳ": "감사", "ㄱㅅ": "감사", "ㄷㄷ": "덜덜",
    "ㅇㅈ": "인정", "ㄹㅇ": "레알", "ㅅㄱ": "수고",
    "?": "응?", "ㅇ": "응", "ㅇㅇ": "응응",
    "ㅅㅅ": "섹스", "ㅎㅎ": "히히", "ㄴㄴ": "노노",
    "ㅈㄹ": "지랄", "ㅇㅋ": "오키"
}

# --- 영문/언더바 닉네임 및 단어 한글 자동 변환 함수 ---
def auto_roman_to_korean(text: str) -> str:
    text = text.replace("_", " ").replace("-", " ")
    words = text.split()
    processed_words = []

    for word in words:
        clean_word = re.sub(r'[^a-zA-Z]', '', word)
        if clean_word:
            try:
                r = Romanizer(clean_word.lower())
                korean_word = r.pronounce()
                word = word.replace(clean_word, korean_word)
            except Exception:
                pass
        processed_words.append(word)

    return " ".join(processed_words)

# --- Typecast SDK 호출 함수 ---
def generate_typecast_tts(text: str, settings: dict) -> bytes:
    voice_id = settings.get('voice_name', 'tc_5c547544fcfee90007fed455')
    tempo = settings.get('tempo', 1.0)
    pitch = settings.get('pitch', 0)
    emotion_preset = settings.get('emotion_preset', 'normal')
    emotion_intensity = settings.get('emotion_intensity', 1.0)

    print(f"🎙 [Typecast SDK] Voice: {voice_id} | Tempo: {tempo} | Pitch: {pitch} | Emotion: {emotion_preset}({emotion_intensity}) | Text: '{text}'")

    try:
        response = client.text_to_speech(TTSRequest(
            text=text,
            model="ssfm-v30",
            voice_id=voice_id,
            prompt=PresetPrompt(
                emotion_type="preset",
                emotion_preset=emotion_preset,
                emotion_intensity=emotion_intensity
            ),
            output=Output(
                audio_tempo=tempo,
                audio_pitch=pitch
            )
        ))

        if not response or not response.audio_data:
            raise Exception("Typecast SDK 응답에 오디오 데이터가 없습니다.")

        print(f"✅ [Typecast SDK 성공] 음성 변환 완료 (재생시간: {getattr(response, 'duration', '?')}s)")
        return response.audio_data

    except Exception as e:
        print(f"❌ [Typecast SDK API 오류 발생]: {e}")
        raise e


# --- 목소리 선택 셀렉트 메뉴 ---
class VoiceSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_voice):
        options = [
            discord.SelectOption(label="찬구", value="tc_5c547544fcfee90007fed455", default=(current_voice == "tc_5c547544fcfee90007fed455")),
            discord.SelectOption(label="주원", value="tc_5c547545fcfee90007fed459", default=(current_voice == "tc_5c547545fcfee90007fed459")),
            discord.SelectOption(label="우주", value="tc_5f8e95eae146f10007b85f45", default=(current_voice == "tc_5f8e95eae146f10007b85f45")),
            discord.SelectOption(label="용식", value="tc_5feb2085cca1a479e73bac37", default=(current_voice == "tc_5feb2085cca1a479e73bac37")),
            discord.SelectOption(label="채린", value="tc_5ffda44bcba8f6d3d46fc41f", default=(current_voice == "tc_5ffda44bcba8f6d3d46fc41f")),
            discord.SelectOption(label="미스터 변사", value="tc_603fa172a669dfd23f450abd", default=(current_voice == "tc_603fa172a669dfd23f450abd")),
            discord.SelectOption(label="창수", value="tc_6059dad0b83880769a50502f", default=(current_voice == "tc_6059dad0b83880769a50502f")),
            discord.SelectOption(label="일호", value="tc_61945d9c2c11c2c9fd934340", default=(current_voice == "tc_61945d9c2c11c2c9fd934340")),
            discord.SelectOption(label="자바바", value="tc_62a89753894c1004cb577d04", default=(current_voice == "tc_62a89753894c1004cb577d04")),
            discord.SelectOption(label="심호문", value="tc_63622aaa4109052e8067e303", default=(current_voice == "tc_63622aaa4109052e8067e303")),
            discord.SelectOption(label="핼런", value="tc_60ee43c93a301a495e8e554e", default=(current_voice == "tc_60ee43c93a301a495e8e554e")),
            discord.SelectOption(label="코난", value="tc_660645fb8db3e2c06ff7070b", default=(current_voice == "tc_660645fb8db3e2c06ff7070b")),
            discord.SelectOption(label="김반장", value="tc_63aaebf1cef3e7d6ce6d3628", default=(current_voice == "tc_63aaebf1cef3e7d6ce6d3628")),
            discord.SelectOption(label="학철", value="tc_63a3d9d14b235ddd6541a78e", default=(current_voice == "tc_63a3d9d14b235ddd6541a78e")),
            discord.SelectOption(label="한유격 교관", value="tc_5faa3acfac283a00075d0d2e", default=(current_voice == "tc_5faa3acfac283a00075d0d2e")),
            discord.SelectOption(label="덕춘", value="tc_5c3c52c95827e00008dd7f34", default=(current_voice == "tc_5c3c52c95827e00008dd7f34")),
            discord.SelectOption(label="키보", value="tc_6100287f568d6198a78bac31", default=(current_voice == "tc_6100287f568d6198a78bac31")),
        ]
        super().__init__(placeholder="목소리 선택", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['voice_name'] = self.values[0]
        selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), self.values[0])
        await interaction.response.send_message(f"✅ TTS 목소리가 `{selected_label}`(으)로 변경되었습니다.", ephemeral=True)


# --- 음성 속도 선택 셀렉트 메뉴 ---
class TempoSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_tempo):
        tempo_options = [
            ("0.5배속 (매우 느림)", 0.5), ("0.8배속", 0.8), ("1.0배속 (기본)", 1.0),
            ("1.2배속", 1.2), ("1.5배속", 1.5), ("1.8배속", 1.8), ("2.0배속 (매우 빠름)", 2.0)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(abs(current_tempo - val) < 0.05))
            for label, val in tempo_options
        ]
        super().__init__(placeholder="음성 속도 선택 (0.5x ~ 2.0x)", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        selected_tempo = float(self.values[0])
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['tempo'] = selected_tempo
        await interaction.response.send_message(f"✅ TTS 속도가 `{selected_tempo}배속`(으)로 변경되었습니다.", ephemeral=True)


# --- 음성 피치(Pitch) 선택 셀렉트 메뉴 ---
class PitchSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_pitch):
        pitch_options = [
            ("-6 반음 (낮음)", -6), ("-3 반음", -3), ("0 반음 (기본)", 0),
            ("+3 반음", 3), ("+6 반음 (높음)", 6)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(current_pitch == val))
            for label, val in pitch_options
        ]
        super().__init__(placeholder="음성 피치(Pitch) 선택 (-12 ~ +12)", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        selected_pitch = int(self.values[0])
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['pitch'] = selected_pitch
        await interaction.response.send_message(f"✅ TTS 피치가 `{selected_pitch}` 반음으로 변경되었습니다.", ephemeral=True)


# --- 감정(Emotion Preset) 선택 셀렉트 메뉴 ---
class EmotionSelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_emotion):
        emotions = [
            ("기본 (normal)", "normal"),
            ("기쁨 (happy)", "happy"),
            ("슬픔 (sad)", "sad"),
            ("화남 (angry)", "angry"),
            ("속삭임 (whisper)", "whisper"),
            ("톤업 (toneup)", "toneup"),
            ("톤다운 (tonedown)", "tonedown")
        ]
        options = [
            discord.SelectOption(label=label, value=val, default=(current_emotion == val))
            for label, val in emotions
        ]
        super().__init__(placeholder="감정(Emotion) 선택", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        selected_emotion = self.values[0]
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['emotion_preset'] = selected_emotion
        await interaction.response.send_message(f"✅ TTS 감정이 `{selected_emotion}`(으)로 변경되었습니다.", ephemeral=True)


# --- 감정 강도(Emotion Intensity) 선택 셀렉트 메뉴 ---
class IntensitySelectView(discord.ui.Select):
    def __init__(self, bot, guild_id, current_intensity):
        intensities = [
            ("강도 0.0 (없음)", 0.0),
            ("강도 0.5 (약함)", 0.5),
            ("강도 1.0 (기본)", 1.0),
            ("강도 1.5 (강함)", 1.5),
            ("강도 2.0 (매우 강함)", 2.0)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(abs(current_intensity - val) < 0.05))
            for label, val in intensities
        ]
        super().__init__(placeholder="감정 강도 선택 (0.0 ~ 2.0)", options=options)
        self.bot = bot
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        selected_intensity = float(self.values[0])
        settings = self.bot.get_guild_settings(self.guild_id)
        settings['emotion_intensity'] = selected_intensity
        await interaction.response.send_message(f"✅ 감정 강도가 `{selected_intensity}`(으)로 변경되었습니다.", ephemeral=True)


# --- TTS 설정 통합 뷰 ---
class TTSSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id

        settings = bot.get_guild_settings(guild_id)

        self.add_item(VoiceSelectView(bot, guild_id, settings.get('voice_name', 'tc_5c547544fcfee90007fed455')))
        self.add_item(TempoSelectView(bot, guild_id, settings.get('tempo', 1.0)))
        self.add_item(PitchSelectView(bot, guild_id, settings.get('pitch', 0)))
        self.add_item(EmotionSelectView(bot, guild_id, settings.get('emotion_preset', 'normal')))
        self.add_item(IntensitySelectView(bot, guild_id, settings.get('emotion_intensity', 1.0)))


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
                'tempo': 1.0,
                'pitch': 0,
                'emotion_preset': 'normal',
                'emotion_intensity': 1.0,
                'read_non_vc': False,
                'channel_id': None,
                'original_channel_name': None,
                'temp_channel_id': None
            }
        return self.guild_settings[guild_id]

    async def setup_hook(self):
        await self.tree.sync()

bot = TTSBot()

async def play_tts(vc, filename):
    ffmpeg_executable = "./ffmpeg.exe" if os.path.exists("./ffmpeg.exe") else "ffmpeg"
    ffmpeg_options = {'options': '-vn'}

    try:
        raw_audio = discord.FFmpegPCMAudio(filename, executable=ffmpeg_executable, **ffmpeg_options)
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
    display_name_korean = auto_roman_to_korean(member.display_name)

    if before.channel is None and after.channel is not None:
        if vc and after.channel == vc.channel:
            tts_text = f"{display_name_korean} 어하"
            filename = f"tts_join_{member.id}_{int(time.time())}.wav"

            try:
                audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, settings)
                with open(filename, "wb") as out:
                    out.write(audio_content)

                while vc.is_playing():
                    await asyncio.sleep(0.3)

                await play_tts(vc, filename)
            except Exception as e:
                print(f"❌ 입장 TTS 실패 상세 원인: {e}")

    elif before.channel is not None and after.channel is None:
        if vc and before.channel == vc.channel:
            tts_text = f"{display_name_korean} 어바"
            filename = f"tts_leave_{member.id}_{int(time.time())}.wav"

            try:
                audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, settings)
                with open(filename, "wb") as out:
                    out.write(audio_content)

                while vc.is_playing():
                    await asyncio.sleep(0.3)

                await play_tts(vc, filename)
            except Exception as e:
                print(f"❌ 퇴장 TTS 실패 상세 원인: {e}")

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

# --- 채널 생성 / 지정 / 해제 통합 명령어 ---
@bot.tree.command(name="tts채널", description="TTS 전용 채널을 생성, 지정 또는 해제합니다.")
@app_commands.rename(action="작업")
@app_commands.describe(action="생성/지정/해제")
@app_commands.choices(action=[
    app_commands.Choice(name="생성", value="create"),
    app_commands.Choice(name="지정", value="set"),
    app_commands.Choice(name="해제", value="clear")
])
async def set_tts_channel(interaction: discord.Interaction, action: str):
    permissions = interaction.channel.permissions_for(interaction.user)
    if not (permissions.manage_channels or permissions.administrator):
        await interaction.response.send_message("❌ 관리자 권한이 필요합니다.", ephemeral=True)
        return

    settings = bot.get_guild_settings(interaction.guild_id)

    if action == "create":
        await interaction.response.defer(ephemeral=True)
        try:
            # 특수 폰트 채널명 '𝗧𝗧𝗦' 생성
            new_channel = await interaction.guild.create_text_channel(
                name="𝗧𝗧𝗦",
                reason="TTS 전용 채널 자동 생성"
            )
            settings['channel_id'] = new_channel.id
            settings['original_channel_name'] = "𝗧𝗧𝗦"
            settings['temp_channel_id'] = None
            await interaction.followup.send(f"🔊 {new_channel.mention} 채널이 TTS 채널로 지정되었습니다!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ 봇에게 '채널 관리(Manage Channels)' 권한이 없어 채널을 생성하지 못했습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ 채널 생성 중 오류가 발생했습니다: {e}", ephemeral=True)

    elif action == "set":
        await interaction.response.defer(ephemeral=True)
        try:
            original_name = interaction.channel.name
            settings['original_channel_name'] = original_name
            settings['channel_id'] = interaction.channel_id
            settings['temp_channel_id'] = None

            await interaction.channel.edit(name="𝗧𝗧𝗦", reason="TTS 채널 지정으로 인한 이름 변경")
            await interaction.followup.send(f"🔊 {interaction.channel.mention} 채널이 TTS 채널로 지정되었습니다!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ 봇에게 '채널 관리(Manage Channels)' 권한이 없어 채널 이름을 변경하지 못했습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ 채널 이름 변경 중 오류가 발생했습니다: {e}", ephemeral=True)

    elif action == "clear":
        await interaction.response.defer(ephemeral=True)
        
        settings['channel_id'] = None
        settings['original_channel_name'] = None
        
        await interaction.followup.send("✅ TTS 채널 설정이 해제되었습니다.", ephemeral=True)

@bot.tree.command(name="tts설정", description="TTS 목소리, 속도, 피치, 감정 및 강도를 설정합니다.")
async def config_tts(interaction: discord.Interaction):
    view = TTSSettingsView(bot, interaction.guild_id)
    await interaction.response.send_message("🎙 **TTS 음성 옵션 설정**", view=view, ephemeral=True)


# --- 메시지 감지 영역 ---

@bot.event
async def on_message(message):
    if message.guild is None or (message.author.bot and message.webhook_id is None):
        return

    settings = bot.get_guild_settings(message.guild.id)
    target_channel_id = settings.get('channel_id') or settings.get('temp_channel_id')

    author_name = auto_roman_to_korean(message.author.display_name)

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
                    tts_text = f"{author_name}님이 이모지를 보냈습니다."
                    filename = f"tts_emoji_{message.id}.wav"

                    try:
                        audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, settings)
                        with open(filename, "wb") as out:
                            out.write(audio_content)

                        while voice_client.is_playing():
                            await asyncio.sleep(0.3)

                        await play_tts(voice_client, filename)
                    except Exception as e:
                        print(f"❌ 이모지 TTS 생성 실패 원인: {e}")
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

    raw_text = message.content.strip()
    raw_text = auto_roman_to_korean(raw_text)

    def replace_user_mention(match):
        user_id = int(match.group(1))
        member = message.guild.get_member(user_id)
        return auto_roman_to_korean(member.display_name) if member else "알 수 없는 유저"

    raw_text = re.sub(r"<@!?(\d+)>", replace_user_mention, raw_text)

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

    filename = f"tts_{message.id}.wav"
    try:
        audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, settings)
        with open(filename, "wb") as out:
            out.write(audio_content)
    except Exception as e:
        print(f"❌ 채팅 메시지 TTS 생성 실패 원인: {e}")
        return

    while voice_client.is_playing(): 
        await asyncio.sleep(0.3)

    await play_tts(voice_client, filename)

bot.run(os.getenv("DISCORD_TOKEN"))
