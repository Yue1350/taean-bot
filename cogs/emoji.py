import io, re, asyncio, aiohttp, discord
from discord.ext import commands
from utils import (
    generate_typecast_tts,
    play_tts,
    auto_roman_to_korean,
    convert_numbers_to_korean,
    delete_message_after_delay
)

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
                            file = discord.File(io.BytesIO(emoji_bytes), filename=f"emoji.{ext}")
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
