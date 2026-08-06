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
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았어!")
        
        self.gemini_client = genai.Client(api_key=api_key)

    @app_commands.command(name="나노바나나", description="프롬프트를 입력받아 Nano Banana 모델로 이미지를 생성합니다.")
    @app_commands.describe(prompt="만들고 싶은 이미지 설명을 입력하세요")
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        try:
            # Nano Banana (Gemini 2.5 Flash Image) 모델 호출
            response = self.gemini_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"]
                )
            )

            # 생성된 바이너리 이미지 데이터 추출 후 디스코드 전송
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/png"
                    ext = "jpg" if "jpeg" in mime_type else "png"

                    file = discord.File(fp=io.BytesIO(image_bytes), filename=f"nanobanana.{ext}")
                    await interaction.followup.send(content=f"🍌 **프롬프트:** {prompt}", file=file)
                    return

            await interaction.followup.send(content="❌ 이미지를 생성하지 못했어.")

        except Exception as e:
            await interaction.followup.send(content=f"❌ 이미지 생성 중 오류가 발생했어: {e}")

async def setup(bot):
    await bot.add_cog(NanoBanana(bot))
