import random
import discord
from discord.ext import commands
from discord import app_commands

class Ladder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="사다리타기", description="참가자 목록과 결과 목록을 쉼표(,)로 구분해 무작위 매칭합니다.")
    @app_commands.describe(
        players="참가자 (쉼표로 구분, 예: 철수, 영희, 민수)",
        results="결과 목록 (쉼표로 구분, 예: 당첨, 꽝, 꽝)"
    )
    async def ladder_game(self, interaction: discord.Interaction, players: str, results: str):
        player_list = [p.strip() for p in players.split(",") if p.strip()]
        result_list = [r.strip() for r in results.split(",") if r.strip()]

        if len(player_list) != len(result_list):
            await interaction.response.send_message(
                f"참가자 수({len(player_list)}명)와 결과 수({len(result_list)}개)가 일치해야 합니다.",
                ephemeral=True
            )
            return

        shuffled_results = result_list.copy()
        random.shuffle(shuffled_results)

        matched = list(zip(player_list, shuffled_results))

        embed = discord.Embed(title="🪜 사다리 타기 결과", color=discord.Color.green())
        
        result_text = ""
        for player, res in matched:
            result_text += f"• **{player}** ➔ {res}\n"

        embed.description = result_text
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Ladder(bot))
