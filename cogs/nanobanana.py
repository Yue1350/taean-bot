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

    @app_commands.command(name="나노바나나", description="프롬프트를 입력받아 이미지를 생성합니다.")
    @app_commands.describe(prompt="만들고 싶은 이미지 설명을 입력하세요")
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        # 이미지 생성 시간이 소요되므로 대기 상태 전환
        await interaction.response.defer()

        try:
            # Gemini / Imagen 이미지 생성 호출
            response = self.gemini_client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="1:1"
                )
            )

            # 1. response 객체 자체가 None인지 확인
            if response is None:
                raise ValueError("API 응답이 비어있습니다. (None)")

            # 2. generated_images 속성이 존재하고 비어있지 않은지 확인
            # getattr를 사용하여 속성이 없을 경우 None을 반환받아 검증
            generated_list = getattr(response, 'generated_images', None)
            
            if generated_list is None:
                 await interaction.followup.send(content=f"⚠️ 이미지를 생성하지 못했습니다. 안전 정책(Safety Filter)에 걸렸을 가능성이 높습니다. (프롬프트: '{prompt}')")
                 return

            if not generated_list: # 빈 리스트[] 인 경우
                 await interaction.followup.send(content=f"⚠️ 이미지가 생성되지 않았습니다. 다른 프롬프트를 시도해 주세요. (프롬프트: '{prompt}')")
                 return

            # 3. 정상적인 이미지 처리
            for generated_image in generated_list:
                image_bytes = generated_image.image.image_bytes
                file = discord.File(fp=io.BytesIO(image_bytes), filename="nanobanana.jpg")
                await interaction.followup.send(content=f"🍌 **프롬프트:** {prompt}", file=file)
                return # 첫 번째 이미지만 전송 후 종료

        except Exception as e:
            # 'NoneType' object is not iterable 에러는 여기서 잡힘
            await interaction.followup.send(content=f"❌ 이미지 생성 중 예기치 않은 오류가 발생했습니다. 잠시 후 다시 시도해 주세요: `{e}`")

async def setup(bot):
    await bot.add_cog(NanoBanana(bot))
