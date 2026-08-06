import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import io
import base64
import logging

logger = logging.getLogger(__name__)

class NanoBananaCog(commands.Cog):
    """나노 바나나(Gemini Flash Image) API를 이용한 이미지 생성 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="생성", description="나노 바나나 API로 이미지를 생성합니다.")
    @app_commands.describe(prompt="생성하고 싶은 이미지의 설명을 입력하세요.")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)

        api_key = getattr(self.bot, "gemini_api_key", None)
        if not api_key:
            await interaction.followup.send("❌ Gemini API 키가 설정되지 않았어. .env 파일을 확인해 줘!")
            return

        # 나노 바나나 (Gemini 2.5 Flash Image) 표준 엔드포인트
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
                    if response.status == 429:
                        await interaction.followup.send("🚨 **오늘 사용할 수 있는 API 이미지 생성 한도를 모두 소진했어!**\n잠시 후 다시 시도해 줘~")
                        return
                    elif response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error ({response.status}): {error_text}")
                        await interaction.followup.send(f"❌ 이미지 생성 실패 (오류 코드: {response.status})\n잠시 후 다시 시도해 줘.")
                        return

                    data = await response.json()

                    # Gemini multimodal 응답에서 이미지 데이터(inlineData) 추출
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

                    image_bytes = base64.b64decode(image_base64)
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
            logger.exception("이미지 생성 중 에러 발생")
            await interaction.followup.send(f"❌ 오류가 발생했습니다: {str(e)}")

    @generate_image.error
    async def on_generate_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ 너무 자주 요청했어! **{error.retry_after:.1f}초** 뒤에 다시 시도해 줘~",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(NanoBananaCog(bot))
