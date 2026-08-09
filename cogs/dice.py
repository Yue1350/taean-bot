import random
import discord
from discord.ext import commands
from discord import app_commands

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="주사위", description="1부터 지정한 숫자 사이의 주사위를 굴립니다.")
    @app_commands.describe(max_num="주사위의 최대 숫자 (기본값: 100)")
    async def roll_dice(self, interaction: discord.Interaction, max_num: int = 100):
        if max_num < 1:
            await interaction.response.send_message("1 이상의 숫자를 입력해주세요.", ephemeral=True)
            return

        result = random.randint(1, max_num)
        embed = discord.Embed(
            title="🎲 주사위 굴리기",
            description=f"**{interaction.user.display_name}**님이 주사위를 굴려 **{result}** (1~{max_num})이(가) 나왔습니다!",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="골라줘", description="선택지 항목 중 하나를 무작위로 선택합니다.")
    @app_commands.describe(options="선택지 목록 (쉼표로 구분, 예: 짜장면, 짬뽕, 볶음밥)")
    async def choose_option(self, interaction: discord.Interaction, options: str):
        option_list = [opt.strip() for opt in options.split(",") if opt.strip()]

        if len(option_list) < 2:
            await interaction.response.send_message("최소 2개 이상의 선택지를 쉼표(,)로 구분해 입력해주세요.", ephemeral=True)
            return

        chosen = random.choice(option_list)
        embed = discord.Embed(
            title="🎯 무작위 선택",
            description=f"선택지: {', '.join(option_list)}\n\n👉 결과: **{chosen}**",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Dice(bot))
