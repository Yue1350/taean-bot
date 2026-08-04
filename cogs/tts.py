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
from views import TTSSettingsView

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
                except Exception as e:
                    print(f"Error generating join TTS: {e}")

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
                except Exception as e:
                    print(f"Error generating leave TTS: {e}")

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

        asyncio.create_task(delete_message_after_delay(message, 600))
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

            while voice_client.is_playing(): 
                await asyncio.sleep(0.3)

            await play_tts(voice_client, filename, self.bot)
        except Exception as e:
            print(f"Error handling message TTS: {e}")

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
                await interaction.followup.send("⚠ **채널 관리** 권한이 없어 채널을 생성하지 못했습니다.", ephemeral=True)

        elif action == "set":
            await interaction.response.defer(ephemeral=True)
            try:
                settings['channel_id'] = interaction.channel_id
                settings['temp_channel_id'] = None

                await interaction.channel.edit(name="𝗧𝗧𝗦", reason="TTS 채널 지정으로 인한 이름 변경")
                await interaction.followup.send(f"🔊 {interaction.channel.mention} 채널이 TTS 채널로 지정되었습니다!", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("⚠ **채널 관리** 권한이 없어 채널 이름을 변경하지 못했습니다.", ephemeral=True)

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
