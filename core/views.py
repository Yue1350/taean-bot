import json
import discord

with open('config/voice_config.json', 'r', encoding='utf-8') as f:
    VOICE_OPTIONS = json.load(f)

class VoiceSelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_voice):
        options = [
            discord.SelectOption(label=label, value=val, default=(current_voice == val))
            for label, val in VOICE_OPTIONS
        ]
        super().__init__(placeholder="목소리 선택", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        settings = await self.bot.get_user_settings(interaction.user.id)
        settings['voice_name'] = self.values[0]
        await self.bot.update_user_settings(interaction.user.id, settings)
        
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
        settings = await self.bot.get_user_settings(interaction.user.id)
        settings['tempo'] = selected_tempo
        await self.bot.update_user_settings(interaction.user.id, settings)
        
        await interaction.response.send_message(f"✅ 음성 속도가 `{selected_tempo}배속`(으)로 변경되었습니다.", ephemeral=True)


class PitchSelectView(discord.ui.Select):
    def __init__(self, bot, user_id, current_pitch):
        pitch_options = [
            ("-5 피치", -5.0), ("-2.5 피치", -2.5), ("0 피치", 0.0),
            ("+2.5 피치", 2.5), ("+5 피치", 5.0)
        ]
        options = [
            discord.SelectOption(label=label, value=str(val), default=(abs(current_pitch - val) < 0.05))
            for label, val in pitch_options
        ]
        super().__init__(placeholder="음성 피치 선택", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        selected_pitch = float(self.values[0])
        settings = await self.bot.get_user_settings(interaction.user.id)
        settings['pitch'] = selected_pitch
        await self.bot.update_user_settings(interaction.user.id, settings)
        
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
        settings = await self.bot.get_user_settings(interaction.user.id)
        settings['emotion_preset'] = selected_emotion
        await self.bot.update_user_settings(interaction.user.id, settings)
        
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
        settings = await self.bot.get_user_settings(interaction.user.id)
        settings['emotion_intensity'] = selected_intensity
        await self.bot.update_user_settings(interaction.user.id, settings)
        
        await interaction.response.send_message(f"✅ 음성 감정 강도가 `{selected_intensity}`(으)로 변경되었습니다.", ephemeral=True)


class TTSSettingsView(discord.ui.View):
    def __init__(self, bot, user_id, user_settings):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

        self.add_item(VoiceSelectView(bot, user_id, user_settings.get('voice_name', 'tc_5c547544fcfee90007fed455')))
        self.add_item(TempoSelectView(bot, user_id, user_settings.get('tempo', 1.0)))
        self.add_item(PitchSelectView(bot, user_id, user_settings.get('pitch', 0)))
        self.add_item(EmotionSelectView(bot, user_id, user_settings.get('emotion_preset', 'normal')))
        self.add_item(IntensitySelectView(bot, user_id, user_settings.get('emotion_intensity', 1.0)))
