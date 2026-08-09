import random
import discord
from discord.ext import commands
from discord import app_commands

class VoicePick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="음성지목", description="현재 접속 중인 음성 채널 인원 중 한 명을 무작위로 지목합니다.")
    async def pick_voice_member(self, interaction: discord.Interaction):
        # 유저의 음성 채널 접속 여부 확인
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("음성 채널에 먼저 접속하신 후 사용해주세요.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        # 봇을 제외한 실제 유저 목록 추출
        members = [m for m in channel.members if not m.bot]

        if not members:
            await interaction.response.send_message("음성 채널에 지목할 유저가 없습니다.", ephemeral=True)
            return

        selected = random.choice(members)
        embed = discord.Embed(
            title="🔊 음성 채널 랜덤 지목",
            description=f"**{channel.name}** 채널에서 **{selected.mention}**님이 당첨되셨습니다!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(VoicePick(bot))
