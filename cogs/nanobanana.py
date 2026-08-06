import base64, io, os, discord
from discord import app_commands
from discord.ext import commands
from google import genai


class NanoBanana(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았어!")

        self.gemini_client = genai.Client(api_key=api_key)

    @app_commands.command(
        name="나노바나나",
        description="Gemini Flash 모델을 사용해 이미지를 생성합니다.",
    )
    @app_commands.describe(prompt="만들고 싶은 이미지 설명을 입력하세요")
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        try:
            # Gemini 3.1 Flash Image (Nano Banana 2) 모델 사용
            response = self.gemini_client.interactions.create(
                model="gemini-3.1-flash-image", input=prompt
            )

            if response is None or not getattr(response, "output_image", None):
                await interaction.followup.send(
                    content=f"⚠️ 이미지를 생성하지 못했어. 안전 정책(Safety Filter)에 걸렸을 수 있어. (프롬프트: '{prompt}')"
                )
                return

            # output_image.data에서 base64 디코딩하여 파일 생성
            image_bytes = base64.b64decode(response.output_image.data)
            file = discord.File(
                fp=io.BytesIO(image_bytes), filename="nanobanana.png"
            )

            await interaction.followup.send(
                content=f"🍌 **프롬프트:** {prompt}", file=file
            )

        except Exception as e:
            await interaction.followup.send(
                content=f"❌ 이미지 생성 중 오류가 발생했어: `{e}`"
            )


async def setup(bot):
    await bot.add_cog(NanoBanana(bot))
