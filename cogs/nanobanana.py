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
            # response_format을 설정하여 모델이 이미지를 생성하고 반환하도록 지시합니다.
            response = self.gemini_client.interactions.create(
                model="gemini-3.1-flash-image",
                input=prompt,
                response_format=[
                    {"type": "text"},
                    {
                        "type": "image",
                        "mime_type": "image/png",  # 또는 "image/jpeg"
                        "aspect_ratio": "1:1",     # 이미지 비율 (1:1, 16:9 등)
                        "image_size": "1K"         # 이미지 화질 (1K, 2K, 4K, 512p 등)
                    }
                ]
            )

            # response.output_image 혹은 steps 안의 content에서 이미지를 확인합니다.
            output_image = getattr(response, "output_image", None)

            if response is None or not output_image or not output_image.data:
                await interaction.followup.send(
                    content=f"⚠️ 이미지를 생성하지 못했어. 안전 정책(Safety Filter)에 걸렸을 수 있어. (프롬프트: '{prompt}')"
                )
                return

            # output_image.data는 base64로 인코딩된 문자열입니다. 디코딩하여 바이트로 변환합니다.
            image_bytes = base64.b64decode(output_image.data)
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
