import os, re, time, asyncio, discord
from discord import app_commands
from discord.ext import commands
from utils import (
    generate_typecast_tts,
    play_tts,
    auto_roman_to_korean,
    convert_numbers_to_korean,
    delete_message_after_delay,
    INITIAL_REPLACEMENTS
)

# 1. UI Select 클래스 정의
class VoiceSelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_voice):
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
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        settings = self.bot.get_user_settings(interaction.user.id)
        settings['voice_name'] = self.values[0]
        selected_label = next((opt.label for opt in self.options if opt.value == self.values[0]), self.values[0])
        await interaction.response.send_message(f"✅ 목소리가 `{selected_label}`(으)로 변경되었습니다.", ephemeral=True)


class TempoSelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_tempo):
        tempo_options = [
            ("0.25배속", 0.25), ("0.5배속", 0.5), ("0.75배속", 0.75), ("1.0배속", 1.0),
            ("1.25배속", 1.25), ("1.5배속", 1.5), ("1.75배속", 1.75), ("2.0배속", 2.0)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(abs(current_tempo - val) < 0.05))
            for label, val in tempo_options
        ]
        super().__init__(placeholder="음성 속도 선택", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        selected_tempo = float(self.values[0])
        settings = self.bot.get_user_settings(interaction.user.id)
        settings['tempo'] = selected_tempo
        await interaction.response.send_message(f"✅ 음성 속도가 `{selected_tempo}배속`(으)로 변경되었습니다.", ephemeral=True)

class PitchSelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_pitch):
        pitch_options = [
            ("-5 피치", -5), ("-2.5 피치", -2.5), ("0 피치", 0),
            ("+2.5 피치", 2.5), ("+5 피치", 5)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(current_pitch == val))
            for label, val in pitch_options
        ]
        super().__init__(placeholder="음성 피치 선택", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        selected_pitch = int(self.values[0])
        settings = self.bot.get_user_settings(interaction.user.id)
        settings['pitch'] = selected_pitch
        await interaction.response.send_message(f"✅ 음성 피치가 `{selected_pitch}` 반음으로 변경되었습니다.", ephemeral=True)


class EmotionSelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_emotion):
        emotions = [
            ("기본", "normal"),
            ("기쁨", "happy"),
            ("슬픔", "sad"),
            ("화남", "angry"),
            ("속삭임", "whisper"),
        ]
        options = [
            discord.SelectOption(label=label, value=val, default=(current_emotion == val))
            for label, val in emotions
        ]
        super().__init__(placeholder="음성 감정 선택", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        selected_emotion = self.values[0]
        settings = self.bot.get_user_settings(interaction.user.id)
        settings['emotion_preset'] = selected_emotion
        await interaction.response.send_message(f"✅ 음성 감정이 `{selected_emotion}`(으)로 변경되었습니다.", ephemeral=True)


class IntensitySelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_intensity):
        intensities = [
            ("강도 0.0", 0.0),
            ("강도 0.5", 0.5),
            ("강도 1.0", 1.0),
            ("강도 1.5", 1.5),
            ("강도 2.0", 2.0)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(abs(current_intensity - val) < 0.05))
            for label, val in intensities
        ]
        super().__init__(placeholder="음성 감정 강도 선택", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        selected_intensity = float(self.values[0])
        settings = self.bot.get_user_settings(interaction.user.id)
        settings['emotion_intensity'] = selected_intensity
        await interaction.response.send_message(f"✅ 음성 감정 강도가 `{selected_intensity}`(으)로 변경되었습니다.", ephemeral=True)


class TTSSettingsView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

        settings = bot.get_user_settings(user_id)

        self.add_item(VoiceSelectView(bot, user_id, settings.get('voice_name', 'tc_5c547544fcfee90007fed455')))
        self.add_item(TempoSelectView(bot, user_id, settings.get('tempo', 1.0)))
        self.add_item(PitchSelectView(bot, user_id, settings.get('pitch', 0)))
        self.add_item(EmotionSelectView(bot, user_id, settings.get('emotion_preset', 'normal')))
        self.add_item(IntensitySelectView(bot, user_id, settings.get('emotion_intensity', 1.0)))

class TTSCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        guild_settings = self.bot.get_guild_settings(member.guild.id)
        user_settings = self.bot.get_user_settings(member.id)
        vc = member.guild.voice_client
        display_name_korean = convert_numbers_to_korean(auto_roman_to_korean(member.display_name))

        if before.channel is None and after.channel is not None:
            if vc and after.channel == vc.channel:
                tts_text = f"{display_name_korean} 어하"
                filename = f"tts_join_{member.id}_{int(time.time())}.wav"

                try:
                    audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, user_settings)
                    with open(filename, "wb") as out:
                        out.write(audio_content)

                    while vc.is_playing():
                        await asyncio.sleep(0.3)

                    await play_tts(vc, filename, self.bot)

        elif before.channel is not None and after.channel is None:
            if vc and before.channel == vc.channel:
                tts_text = f"{display_name_korean} 어바"
                filename = f"tts_leave_{member.id}_{int(time.time())}.wav"

                try:
                    audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, user_settings)
                    with open(filename, "wb") as out:
                        out.write(audio_content)

                    while vc.is_playing():
                        await asyncio.sleep(0.3)

                    await play_tts(vc, filename, self.bot)

        if not vc or not vc.is_connected():
            return

        human_members = [m for m in vc.channel.members if not m.bot]
        if len(human_members) == 0:
            await vc.disconnect()
            guild_settings['temp_channel_id'] = None
            print(f"⚠ 음성 채널에 아무도 없어서 퇴장했습니다.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or (message.author.bot and message.webhook_id is None):
            return

        custom_emojis = re.findall(r"<(a?):(\w+):(\d+)>", message.content)
        if custom_emojis:
            return

        guild_settings = self.bot.get_guild_settings(message.guild.id)
        user_settings = self.bot.get_user_settings(message.author.id)
        target_channel_id = guild_settings.get('channel_id') or guild_settings.get('temp_channel_id')

        author_name = convert_numbers_to_korean(auto_roman_to_korean(message.author.display_name))

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
        if not author_in_vc and not guild_settings.get('read_non_vc'): 
            return

        raw_text = message.content.strip()
        raw_text = auto_roman_to_korean(raw_text)
        raw_text = convert_numbers_to_korean(raw_text)

        def replace_user_mention(match):
            user_id = int(match.group(1))
            member = message.guild.get_member(user_id)
            return convert_numbers_to_korean(auto_roman_to_korean(member.display_name)) if member else "알 수 없는 유저"

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
            audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, user_settings)
            with open(filename, "wb") as out:
                out.write(audio_content)
            return

        while voice_client.is_playing(): 
            await asyncio.sleep(0.3)

        await play_tts(voice_client, filename, self.bot)

    @app_commands.command(name="입장", description="봇을 음성 채널에 입장시킵니다.")
    async def join_vc(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("⚠ 먼저 음성 채널에 입장해야 합니다.", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc:
            await vc.move_to(voice_channel)
        else:
            await voice_channel.connect(reconnect=True, timeout=60.0)

        settings = self.bot.get_guild_settings(interaction.guild_id)
        if not settings.get('channel_id'):
            settings['temp_channel_id'] = interaction.channel_id

        await interaction.response.send_message(f"🔊 {voice_channel.mention} 채널이 설정되었습니다.", ephemeral=True)

    @app_commands.command(name="퇴장", description="봇을 음성 채널에서 퇴장시킵니다.")
    async def leave_vc(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect()
            settings = self.bot.get_guild_settings(interaction.guild_id)
            settings['temp_channel_id'] = None
            await interaction.response.send_message("✅ 음성 채널에서 퇴장하였습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠ 현재 통화방에 입장해 있지 않습니다.", ephemeral=True)

    @app_commands.command(name="tts채널", description="TTS 전용 채널을 생성, 지정 또는 해제합니다.")
    @app_commands.rename(action="작업")
    @app_commands.describe(action="수행할 작업을 선택하세요 (생성/지정/해제)")
    @app_commands.choices(action=[
        app_commands.Choice(name="생성", value="create"),
        app_commands.Choice(name="지정", value="set"),
        app_commands.Choice(name="해제", value="clear")
    ])
    async def set_tts_channel(self, interaction: discord.Interaction, action: str):
        permissions = interaction.channel.permissions_for(interaction.user)
        if not (permissions.manage_channels or permissions.administrator):
            await interaction.response.send_message("⚠ 관리자 권한이 필요합니다.", ephemeral=True)
            return

        settings = self.bot.get_guild_settings(interaction.guild_id)

        if action == "create":
            await interaction.response.defer(ephemeral=True)
            try:
                new_channel = await interaction.guild.create_text_channel(
                    name="𝗧𝗧𝗦",
                    reason="TTS 전용 채널 자동 생성"
                )
                settings['channel_id'] = new_channel.id
                settings['temp_channel_id'] = None
                await interaction.followup.send(f"🔊 {new_channel.mention} 채널이 TTS 채널로 지정되었습니다!", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠ 채널 관리 권한이 없어 채널을 생성하지 못했습니다.", ephemeral=True)

        elif action == "set":
            await interaction.response.defer(ephemeral=True)
            try:
                settings['channel_id'] = interaction.channel_id
                settings['temp_channel_id'] = None

                await interaction.channel.edit(name="𝗧𝗧𝗦", reason="TTS 채널 지정으로 인한 이름 변경")
                await interaction.followup.send(f"🔊 {interaction.channel.mention} 채널이 TTS 채널로 지정되었습니다!", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠ 채널 관리 권한이 없어 채널 이름을 변경하지 못했습니다.", ephemeral=True)

        elif action == "clear":
            await interaction.response.defer(ephemeral=True)
            settings['channel_id'] = None
            await interaction.followup.send("✅ TTS 채널 설정이 해제되었습니다.", ephemeral=True)

    @app_commands.command(name="tts설정", description="자신의 TTS 목소리, 속도, 피치, 감정 및 강도를 설정합니다.")
    async def config_tts(self, interaction: discord.Interaction):
        view = TTSSettingsView(self.bot, interaction.user.id)
        await interaction.response.send_message("", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TTSCog(bot))
