import discord
from discord import app_commands
from discord.ext import commands
import io
import asyncio
import logging
from datetime import datetime
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class NanoBananaCog(commands.Cog):
    """Google GenAI SDK(Nano Banana / gemini-2.5-flash-image)를 이용한 이미지 생성 및 크레딧 관리 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_limit = 100
        self.used_today = 0
        self.last_reset_date = datetime.now().date()
        self.client = None

    def _check_and_reset_daily_limit(self):
        """날짜 변경 시 사용량 초기화"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.used_today = 0
            self.last_reset_date = current_date

    def _get_client(self):
        """GenAI Client 생성 또는 반환"""
        if self.client is None:
            api_key = getattr(self.bot, "gemini_api_key", None)
            if api_key:
                self.client = genai.Client(api_key=api_key)
        return self.client

    @app_commands.command(name="생성", description="나노 바나나 API로 이미지를 생성합니다.")
    @app_commands.describe(prompt="생성하고 싶은 이미지의 설명을 입력하세요.")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        self._check_and_reset_daily_limit()

        if self.used_today >= self.daily_limit:
            await interaction.response.send_message(
                "🚨 **오늘 사용할 수 있는 일일 생성 한도(100회)를 모두 소진했어!**\n내일 자정 이후에 다시 시도해 줘~",
                ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        client = self._get_client()
        if not client:
            await interaction.followup.send("❌ Gemini API 키가 설정되지 않았어. bot.gemini_api_key 설정을 확인해 줘!")
            return

        try:
            # 공식 문서 기준: gemini-2.5-flash-image 모델 및 response_modalities=["IMAGE"] 설정
            def call_api():
                return client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"]
                    )
                )

            # SDK 동기 요청을 비동기 타스크로 실행하여 Discord Bot 블로킹 방지
            response = await asyncio.to_thread(call_api)

            # 응답에서 이미지 바이너리 추출
            image_bytes = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        image_bytes = part.inline_data.data
                        break

            if not image_bytes:
                await interaction.followup.send("❌ 이미지를 생성하지 못했거나 응답 결과가 없어.")
                return

            self.used_today += 1
            remaining = max(0, self.daily_limit - self.used_today)

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
            error_str = str(e)
            logger.exception("이미지 생성 중 에러 발생")
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                await interaction.followup.send(
                    "🚨 **Google API 요청 제한(429/Resource Exhausted)이 발생했어!**\n"
                    "분당 요청 제한(RPM)에 걸렸거나 API Key의 사용량이 초과되었을 수 있어. 잠시 후 다시 시도해 줘~"
                )
            else:
                await interaction.followup.send(f"❌ 오류가 발생했습니다: {error_str}")

    @app_commands.command(name="크레딧", description="오늘 남은 나노 바나나 이미지 생성 크레딧 현황을 확인합니다.")
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
