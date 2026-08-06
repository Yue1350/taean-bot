import os
import io
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types

class NanoBanana(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 환경 변수에서 GEMINI_API_KEY 불러오기
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았어!")
        
        self.gemini_client = genai.Client(api_key=api_key)

    @app_commands.command(name="나노바나나", description="프롬프트를 입력받아 Gemini/Imagen 모델로 이미지를 생성합니다.")
    @app_commands.describe(prompt="만들고 싶은 이미지 설명을 입력하세요")
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        try:
            response = self.gemini_client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="1:1"
                )
            )

            for generated_image in response.generated_images:
                image_bytes = generated_image.image.image_bytes
                file = discord.File(fp=io.BytesIO(image_bytes), filename="nanobanana.jpg")
                await interaction.followup.send(content=f"🍌 **프롬프트:** {prompt}", file=file)

        except Exception as e:
            await interaction.followup.send(content=f"❌ 이미지 생성 중 오류가 발생했어: {e}")

async def setup(bot):
    await bot.add_cog(NanoBanana(bot))
