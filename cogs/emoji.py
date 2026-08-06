import io, re, asyncio, aiohttp, discord
from discord.ext import commands
from PIL import Image, ImageSequence
from core.utils import (
    generate_typecast_tts,
    play_tts,
    auto_roman_to_korean,
    convert_numbers_to_korean,
    delete_message_after_delay
)

def resize_image_to_square(img_bytes: bytes, target_size: int = 512) -> bytes:
    """
    이미지(PNG/GIF)를 비율을 유지하며 target_size x target_size 투명 캔버스 중앙에 배치해 업스케일링합니다.
    """
    with Image.open(io.BytesIO(img_bytes)) as img:
        is_animated = getattr(img, "is_animated", False)
        
        def process_frame(frame):
            # 투명 배경의 512x512 캔버스 생성
            canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            frame_rgba = frame.convert("RGBA")
            
            # 비율 유지 리사이징 계산
            w, h = frame_rgba.size
            ratio = min(target_size / w, target_size / h)
            new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
            
            resized_frame = frame_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # 중앙 배치 위치 계산
            paste_x = (target_size - new_w) // 2
            paste_y = (target_size - new_h) // 2
            
            canvas.paste(resized_frame, (paste_x, paste_y), resized_frame)
            return canvas

        output = io.BytesIO()

        if is_animated:
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(img):
                frames.append(process_frame(frame))
                durations.append(frame.info.get('duration', 100))
            
            frames[0].save(
                output,
                format='GIF',
                save_all=True,
                append_images=frames[1:],
                loop=img.info.get('loop', 0),
                duration=durations,
                disposal=2,
                transparency=0
            )
        else:
            processed = process_frame(img)
            processed.save(output, format='PNG')

        return output.getvalue()


class EmojiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or (message.author.bot and message.webhook_id is None):
            return

        guild_settings = self.bot.get_guild_settings(message.guild.id)
        user_settings = self.bot.get_user_settings(message.author.id)
        target_channel_id = guild_settings.get('channel_id') or guild_settings.get('temp_channel_id')

        author_name = convert_numbers_to_korean(auto_roman_to_korean(message.author.display_name))

        if message.webhook_id is not None:
            if message.channel.id == target_channel_id:
                asyncio.create_task(delete_message_after_delay(message, 600))
            return

        custom_emojis = re.findall(r"<(a?):(\w+):(\d+)>", message.content)
        if custom_emojis:
            try:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass

                cleaned_content = re.sub(r"<(a?):(\w+):(\d+)>", "", message.content).strip()

                is_animated, emoji_name, emoji_id = custom_emojis[0]
                ext = "gif" if is_animated else "png"
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=1024"

                async with aiohttp.ClientSession() as session:
                    async with session.get(emoji_url) as resp:
                        if resp.status == 200:
                            emoji_bytes = await resp.read()
                            # Pillow 처리는 동기 작업이므로 asyncio.to_thread로 실행하여 블로킹 방지
                            processed_bytes = await asyncio.to_thread(resize_image_to_square, emoji_bytes, 512)
                            file = discord.File(io.BytesIO(processed_bytes), filename=f"emoji.{ext}")
                        else:
                            file = None

                webhook = await message.channel.create_webhook(name="EmojiTransmitter")
                await webhook.send(
                    content=cleaned_content if cleaned_content else None,
                    file=file,
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url
                )
                await webhook.delete()

                if message.channel.id == target_channel_id:
                    voice_client = message.guild.voice_client
                    if voice_client and (message.author.voice and message.author.voice.channel == voice_client.channel or guild_settings.get('read_non_vc')):
                        if cleaned_content:
                            tts_text = cleaned_content
                            tts_text = auto_roman_to_korean(tts_text)
                            tts_text = convert_numbers_to_korean(tts_text)
                        else:
                            tts_text = f"{author_name}님이 이모지를 보냈습니다."

                        filename = f"tts_emoji_{message.id}.wav"

                        try:
                            audio_content = await asyncio.to_thread(generate_typecast_tts, tts_text, user_settings)
                            with open(filename, "wb") as out:
                                out.write(audio_content)

                            while voice_client.is_playing():
                                await asyncio.sleep(0.3)

                            await play_tts(voice_client, filename, self.bot)
                        except Exception:
                            pass
            except Exception:
                pass

async def setup(bot):
    await bot.add_cog(EmojiCog(bot))
