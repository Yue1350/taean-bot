import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io
import base64
import logging

logger = logging.getLogger(__name__)

class NanoBananaCog(commands.Cog):
    """나노 바나나 API를 이용한 이미지 생성 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # main.py에서 설정한 API 키를 가져옵니다.
        self.api_key = getattr(bot, "gemini_api_key", "YOUR_GEMINI_API_KEY")
        # Google Imagen / Gemini 이미지 생성 API 엔드포인트
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={self.api_key}"

    @app_commands.command(name="생성", description="나노 바나나 API로 이미지를 생성합니다.")
    @app_commands.describe(prompt="생성하고 싶은 이미지의 설명을 입력하세요.")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)  # 사용자당 30초 쿨타임
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        # 이미지 생생에는 시간이 소요되므로 대기 상태(Thinking...)로 전환
        await interaction.response.defer(thinking=True)

        payload = {
            "instances": [
                {"prompt": prompt}
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "1:1"
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error ({response.status}): {error_text}")
                        await interaction.followup.send(
                            f"❌ 이미지 생성 실패 (오류 코드: {response.status})\n잠시 후 다시 시도해 주세요."
                        )
                        return

                    data = await response.json()

                    # Base64 이미지 데이터 추출
                    predictions = data.get("predictions", [])
                    if not predictions or "bytesBase64Encoded" not in predictions[0]:
                        await interaction.followup.send("❌ 이미지를 생성하지 못했습니다. (응답 데이터 없음)")
                        return

                    base64_data = predictions[0]["bytesBase64Encoded"]
                    image_bytes = base64.b64decode(base64_data)

                    # 디스코드 첨부파일로 변환
                    file = discord.File(fp=io.BytesIO(image_bytes), filename="generated_image.png")
                    
                    # Embed 생성 (바나나 느낌의 노란색)
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
            logger.exception("이미지 생성 중 에러 발생")
            await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}")

    # 쿨타임 발생 시 처리 핸들러
    @generate_image.error
    async def on_generate_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ 너무 자주 요청했어! **{error.retry_after:.1f}초** 뒤에 다시 시도해 줘~",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(NanoBananaCog(bot))
