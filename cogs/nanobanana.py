import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NanoBananaCog(commands.Cog):
    """나노 바나나 API를 이용한 이미지 생성 및 크레딧 관리 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 일일 기본 한도 설정
        self.daily_limit = 100
        self.used_today = 0
        self.last_reset_date = datetime.now().date()

    def _check_and_reset_daily_limit(self):
        """날짜가 바뀌면 사용량을 초기화"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.used_today = 0
            self.last_reset_date = current_date

    @app_commands.command(name="생성", description="나노 바나나 API로 이미지를 생성합니다.")
    @app_commands.describe(prompt="생성하고 싶은 이미지의 설명을 입력하세요.")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        self._check_and_reset_daily_limit()

        # 봇 내부 로컬 카운트 검사
        if self.used_today >= self.daily_limit:
            await interaction.response.send_message(
                "🚨 **오늘 봇에 설정된 일일 사용 횟수(100회)를 모두 사용했어!**\n내일 자정 이후에 다시 시도해 줘~",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        api_key = getattr(self.bot, "gemini_api_key", None)
        if not api_key:
            await interaction.followup.send("❌ Gemini API 키가 설정되지 않았어. .env 파일이나 main.py를 확인해 줘!")
            return

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"Generate an image: {prompt}"}
                    ]
                }
            ]
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    # API 자체 한도(429)에 걸린 경우
                    if response.status == 429:
                        await interaction.followup.send(
                            "🚨 **Google API 요청 제한(429)이 발생했어!**\n"
                            "분당 요청 수가 너무 많거나 오늘 API 전체 사용량이 초과되었을 수 있어. 잠시(1~2분) 후 다시 시도해 봐~"
                        )
                        return
                    elif response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error ({response.status}): {error_text}")
                        await interaction.followup.send(f"❌ 이미지 생성 실패 (오류 코드: {response.status})\n잠시 후 다시 시도해 줘.")
                        return

                    data = await response.json()

                    candidates = data.get("candidates", [])
                    if not candidates:
                        await interaction.followup.send("❌ 이미지를 생성하지 못했어. (응답 데이터 없음)")
                        return

                    parts = candidates[0].get("content", {}).get("parts", [])
                    image_base64 = None

                    for part in parts:
                        if "inlineData" in part:
                            image_base64 = part["inlineData"].get("data")
                            break

                    if not image_base64:
                        await interaction.followup.send("❌ 이미지 데이터를 찾을 수 없어.")
                        return

                    # 정상 발급 시에만 카운트 올리기
                    self.used_today += 1
                    remaining = max(0, self.daily_limit - self.used_today)

                    image_bytes = base64.b64decode(image_base64)
                    file = discord.File(fp=io.BytesIO(image_bytes), filename="generated_image.png")
                    
                    embed = discord.Embed(
                        title="🍌 나노 바나나 이미지 생성 완료!",
                        description=f"**프롬프트:** {prompt}",
                        color=discord.Color.from_rgb(255, 215, 0)
                    )
                    embed.set_image(url="attachment://generated_image.png")
                    embed.set_footer(
                        text=f"요청자: {interaction.user.display_name} | 오늘 남은 생성 횟수: {remaining}회", 
                        icon_url=interaction.user.display_avatar.url
                    )

                    await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            logger.exception("이미지 생성 중 에러 발생")
            await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}")

    @app_commands.command(name="크레딧", description="오늘 남은 나노 바나나 이미지 생성 크레딧 및 잔여 횟수를 확인합니다.")
    async def check_credit(self, interaction: discord.Interaction):
        self._check_and_reset_daily_limit()

        remaining = max(0, self.daily_limit - self.used_today)
        progress_bar_length = 10
        filled = int((self.used_today / self.daily_limit) * progress_bar_length)
        bar = "🟩" * (progress_bar_length - filled) + "🟥" * filled

        embed = discord.Embed(
            title="🍌 금일 나노 바나나 API 잔여 크레딧 현황",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.add_field(name="총 일일 제공 횟수", value=f"`{self.daily_limit}회`", inline=True)
        embed.add_field(name="오늘 사용한 횟수", value=f"`{self.used_today}회`", inline=True)
        embed.add_field(name="남은 생성 횟수", value=f"`{remaining}회`", inline=True)
        embed.add_field(name="사용률 현황", value=f"{bar} ({self.used_today}/{self.daily_limit})", inline=False)
        embed.set_footer(text="매일 자정에 생성 한도가 자동으로 초기화돼~")

        await interaction.response.send_message(embed=embed)

    @generate_image.error
    async def on_generate_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ 너무 자주 요청했어! **{error.retry_after:.1f}초** 뒤에 다시 시도해 줘~",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(NanoBananaCog(bot))
