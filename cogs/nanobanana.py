import discord
from discord import app_commands
from discord.ext import commands
import io
import asyncio
import base64
import logging
from google import genai

logger = logging.getLogger(__name__)

class NanoBananaCog(commands.Cog):
    """Google GenAI Interactions API (gemini-3.1-flash-image) 기반 이미지 생성 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = None

    def _get_client(self):
        """GenAI Client 생성 또는 반환"""
        if self.client is None:
            api_key = getattr(self.bot, "gemini_api_key", None)
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                self.client = genai.Client() # 환경 변수 GEMINI_API_KEY 기본 참조
        return self.client

    @app_commands.command(name="생성", description="Gemini 3.1 Flash Image API로 이미지를 생성합니다.")
    @app_commands.describe(prompt="생성하고 싶은 이미지의 설명을 입력하세요.")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        client = self._get_client()

        try:
            # 공식 Interactions API 호출
            def call_api():
                return client.interactions.create(
                    model="gemini-3.1-flash-image",
                    input=prompt,
                )

            res = await asyncio.to_thread(call_api)

            # 응답 데이터에서 Base64 디코딩
            if not hasattr(res, "output_image") or not res.output_image or not res.output_image.data:
                await interaction.followup.send("❌ 이미지를 생성하지 못했거나 응답 결과가 없어.")
                return

            image_bytes = base64.b64decode(res.output_image.data)

            file = discord.File(fp=io.BytesIO(image_bytes), filename="generated_image.png")
            
            embed = discord.Embed(
                title="🍌 나노 바나나 이미지 생성 완료!",
                description=f"**프롬프트:** {prompt}",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            embed.set_image(url="attachment://generated_image.png")
            embed.set_footer(
                text=f"요청자: {interaction.user.display_name}", 
                icon_url=interaction.user.display_avatar.url
            )

            await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            error_str = str(e)
            logger.exception("이미지 생성 중 에러 발생")
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                await interaction.followup.send(
                    "🚨 **Google API 요청 제한(429/Resource Exhausted)이 발생했어!**\n"
                    "분당 요청 제한(RPM)에 걸렸거나 해당 모델의 할당량이 다 찼을 수 있어. 약 1분 뒤에 다시 시도해 줘~"
                )
            else:
                await interaction.followup.send(f"❌ 오류가 발생했습니다: {error_str}")

    @generate_image.error
    async def on_generate_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ 너무 자주 요청했어! **{error.retry_after:.1f}초** 뒤에 다시 시도해 줘~",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(NanoBananaCog(bot))
