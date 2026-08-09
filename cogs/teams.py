import random
import discord
from discord.ext import commands
from discord import app_commands

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="팀나누기", description="참여자를 입력받아 지정한 팀 수로 나눕니다.")
    @app_commands.describe(
        num_teams="생성할 팀 수",
        members="참여자 이름 (공백으로 구분, 예: 철수 영희 민수)"
    )
    async def split_teams(self, interaction: discord.Interaction, num_teams: int, members: str):
        member_list = members.split()
        
        if num_teams <= 0:
            await interaction.response.send_message("팀 수는 1개 이상이어야 합니다.", ephemeral=True)
            return

        if len(member_list) < num_teams:
            await interaction.response.send_message("참여자 수가 팀 수보다 적어서 나눌 수 없습니다.", ephemeral=True)
            return

        random.shuffle(member_list)

        teams = [[] for _ in range(num_teams)]
        for i, member in enumerate(member_list):
            teams[i % num_teams].append(member)

        embed = discord.Embed(title="🎲 팀 나누기 결과", color=discord.Color.blue())
        for idx, team in enumerate(teams, start=1):
            embed.add_field(
                name=f"🚩 팀 {idx}",
                value=", ".join(team) if team else "없음",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Teams(bot))
