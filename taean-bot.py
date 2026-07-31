import sys, subprocess, os, site, json, yt_dlp, re, asyncio, urllib.request
import discord
from discord import app_commands
from dotenv import load_dotenv
from keep_alive import keep_alive

site.main()
load_dotenv()

keep_alive()

MUSIC_TOKEN = os.getenv('MUSIC_TOKEN')
SPOTIFY_CLIENT_ID = os.getenv('spotify_client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('spotify_client_secret')
if not MUSIC_TOKEN:
    print("❌ 오류: MUSIC_TOKEN 환경변수가 설정되지 않았습니다.")
    print("💡 해결방법: 터미널에서 'fly secrets set MUSIC_TOKEN=당신의디스코드봇토큰' 명령어를 실행해 주세요.")
    sys.exit(1)

# yt-dlp 옵션
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class MusicBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.music_channels = {} 
        self.queue_messages = {} 
        self.music_queues = {}   
        self.current_song = {}   
        self.volumes = {}        
        self.inactive_tasks = {} 

    async def setup_hook(self):
        await self.tree.sync()

bot = MusicBot()

@bot.event
async def on_ready():
    await update_bot_presence()
    print(f"✅ 음악 봇 로그인 성공: {bot.user.name}")

async def update_bot_presence():
    playing_any = any(guild.voice_client and guild.voice_client.is_playing() for guild in bot.guilds)
    activity = discord.Game(name="음악 재생 중") if playing_any else discord.Game(name="음악 재생 대기 중")
    await bot.change_presence(status=discord.Status.online, activity=activity)

def cancel_inactive_timer(guild_id):
    if guild_id in bot.inactive_tasks:
        bot.inactive_tasks[guild_id].cancel()
        del bot.inactive_tasks[guild_id]

def start_inactive_timer(guild):
    guild_id = guild.id
    cancel_inactive_timer(guild_id)

    async def inactive_timeout():
        try:
            await asyncio.sleep(300) 
            vc = guild.voice_client
            if vc and vc.is_connected():
                bot.music_queues[guild_id] = []
                bot.current_song[guild_id] = None
                await clear_queue_message(guild)
                await vc.disconnect()
                await update_music_embed(guild)
                await update_bot_presence()
                print(f"🚪 5분 동안 사용이 없어 자동으로 퇴장했습니다: {guild.name}")
        except asyncio.CancelledError:
            pass

    bot.inactive_tasks[guild_id] = asyncio.create_task(inactive_timeout())

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    vc = guild.voice_client

    if vc and vc.channel:
        human_members = [m for m in vc.channel.members if not m.bot]
        if len(human_members) == 0:
            await asyncio.sleep(3)
            human_members_recheck = [m for m in vc.channel.members if not m.bot]
            if len(human_members_recheck) == 0 and vc.is_connected():
                guild_id = guild.id
                cancel_inactive_timer(guild_id)
                bot.music_queues[guild_id] = []
                bot.current_song[guild_id] = None
                await clear_queue_message(guild)
                await vc.disconnect()
                await update_music_embed(guild)
                await update_bot_presence()
                print(f"🚪 통화방에 아무도 없어 자동으로 퇴장했습니다: {guild.name}")

async def clear_queue_message(guild):
    guild_id = guild.id
    if guild_id in bot.queue_messages:
        ch_info = bot.music_channels.get(guild_id)
        if ch_info:
            channel = guild.get_channel(ch_info['channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(bot.queue_messages[guild_id])
                    await msg.delete()
                except Exception:
                    pass
        del bot.queue_messages[guild_id]

async def update_queue_message(guild):
    guild_id = guild.id
    vc = guild.voice_client
    ch_info = bot.music_channels.get(guild_id)
    if not ch_info:
        return
    
    channel = guild.get_channel(ch_info['channel_id'])
    if not channel or not vc or not vc.is_connected():
        await clear_queue_message(guild)
        return

    queue = bot.music_queues.get(guild_id, [])
    if queue:
        q_list = [f"{i+1}. {song['title']}" for i, song in enumerate(queue)]
        queue_text = "\n".join(q_list[:15])
        if len(queue) > 15:
            queue_text += f"\n... 외 {len(queue) - 15}곡"
    else:
        queue_text = "대기 중인 곡이 없습니다."

    embed = discord.Embed(title="📜 대기열", description=queue_text, color=discord.Color.purple())

    if guild_id in bot.queue_messages:
        try:
            msg = await channel.fetch_message(bot.queue_messages[guild_id])
            await msg.edit(embed=embed)
            return
        except Exception:
            pass

    msg = await channel.send(embed=embed)
    bot.queue_messages[guild_id] = msg.id

async def play_next_song(guild):
    guild_id = guild.id
    voice_client = guild.voice_client

    if not voice_client:
        cancel_inactive_timer(guild_id)
        bot.current_song[guild_id] = None
        await clear_queue_message(guild)
        await update_music_embed(guild)
        await update_bot_presence()
        return

    queue = bot.music_queues.get(guild_id, [])
    if not queue:
        bot.current_song[guild_id] = None
        await update_queue_message(guild)
        await update_music_embed(guild)
        await update_bot_presence()
        start_inactive_timer(guild)
        return

    cancel_inactive_timer(guild_id)
    song = queue.pop(0)
    bot.current_song[guild_id] = song

    await update_queue_message(guild)

    if not song.get('url'):
        await play_next_song(guild)
        return

    ffmpeg_executable = "./ffmpeg.exe" if os.path.exists("./ffmpeg.exe") else "ffmpeg"
    
    def after_playing(error):
        if error:
            print(f"❌ 음악 재생 오류: {error}")
        coro = play_next_song(guild)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"❌ 다음 곡 재생 실패: {e}")

    audio_source = discord.FFmpegPCMAudio(song['url'], executable=ffmpeg_executable, **FFMPEG_OPTIONS)
    current_vol = bot.volumes.get(guild_id, 0.05)
    volume_source = discord.PCMVolumeTransformer(audio_source, volume=current_vol)

    voice_client.play(volume_source, after=after_playing)
    await update_bot_presence()
    await update_music_embed(guild)

class MusicControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏯️ 재생/일시정지", style=discord.ButtonStyle.secondary, custom_id="music_pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ 연결된 음성 채널이 없습니다.", ephemeral=True)
        
        if vc.is_paused():
            vc.resume()
            cancel_inactive_timer(interaction.guild_id)
            await update_bot_presence()
            await interaction.response.send_message("▶️ 재생을 다시 시작하겠습니다.", ephemeral=True)
        elif vc.is_playing():
            vc.pause()
            await update_bot_presence()
            await interaction.response.send_message("⏸️ 일시정지했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 재생 중인 음악이 없습니다.", ephemeral=True)

    @discord.ui.button(label="⏭️ 스킵", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("❌ 재생 중인 음악이 없습니다.", ephemeral=True)
        vc.stop()
        await interaction.response.send_message("⏭️ 다음 곡으로 넘어가겠습니다.", ephemeral=True)

    @discord.ui.button(label="⏹️ 강제종료", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        guild_id = interaction.guild_id
        cancel_inactive_timer(guild_id)
        bot.music_queues[guild_id] = []
        bot.current_song[guild_id] = None
        await clear_queue_message(interaction.guild)

        if vc:
            await vc.disconnect()
            await update_music_embed(interaction.guild)
            await update_bot_presence()
            await interaction.response.send_message("⏹️ 음성 채널에서 퇴장하고 대기열을 초기화했습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 접속 중인 음성 채널이 없습니다.", ephemeral=True)

def create_music_embed(guild_id):
    current = bot.current_song.get(guild_id)
    current_vol = bot.volumes.get(guild_id, 0.05)
    percent = int(round((current_vol / 0.05) * 100))

    if current:
        embed = discord.Embed(
            title=f"🎵 {current['title']}",
            description=f"신청자: {current['requester'].mention}\n🔊 현재 음량: **{percent}%**",
            color=discord.Color.green()
        )
        if current.get('thumbnail'):
            embed.set_image(url=current['thumbnail'])
        return embed, None
    else:
        embed = discord.Embed(
            title="🎵 현재 재생 중인 음악이 없습니다.",
            description="",
            color=discord.Color.blue()
        )
        file = None
        if os.path.exists("music_idle.png"):
            file = discord.File("music_idle.png", filename="music_idle.png")
            embed.set_image(url="attachment://music_idle.png")
        return embed, file

async def update_music_embed(guild):
    guild_id = guild.id
    if guild_id not in bot.music_channels:
        return

    ch_info = bot.music_channels[guild_id]
    channel = guild.get_channel(ch_info['channel_id'])
    if not channel:
        return

    try:
        msg = await channel.fetch_message(ch_info['message_id'])
        embed, file = create_music_embed(guild_id)
        view = MusicControlView() if bot.current_song.get(guild_id) else None
        
        if file:
            await msg.edit(embed=embed, view=view, attachments=[file])
        else:
            await msg.edit(embed=embed, view=view, attachments=[])
    except Exception as e:
        print(f"❌ 임베드 업데이트 실패: {e}")

async def setup_music_channel(channel):
    guild = channel.guild
    try:
        await channel.purge(limit=100)
    except Exception as e:
        print(f"⚠️ 기존 메시지 삭제 실패: {e}")

    bot.queue_messages.pop(guild.id, None)
    embed, file = create_music_embed(guild.id)
    if file:
        msg = await channel.send(embed=embed, file=file)
    else:
        msg = await channel.send(embed=embed)
        
    bot.music_channels[guild.id] = {'channel_id': channel.id, 'message_id': msg.id}

@bot.tree.command(name="음악채널", description="음악 전용 채널을 지정하거나 생성합니다.")
@app_commands.choices(지정생성=[
    app_commands.Choice(name="지정", value="지정"),
    app_commands.Choice(name="생성", value="생성")
])
async def music_channel_command(interaction: discord.Interaction, 지정생성: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if 지정생성.value == "지정":
        await setup_music_channel(interaction.channel)
        await interaction.followup.send("✅ 현재 채널이 음악 전용 채널로 지정되었습니다.", ephemeral=True)
    elif 지정생성.value == "생성":
        channel = await guild.create_text_channel(name="🎵-음악-신청")
        await setup_music_channel(channel)
        await interaction.followup.send(f"✅ 새로운 음악 채널이 생성되었습니다: {channel.mention}", ephemeral=True)

@bot.tree.command(name="볼륨", description="음악 재생 음량을 조절합니다 (1~100%).")
@app_commands.describe(volume="설정할 음량 크기 (1 ~ 100)")
async def set_volume(interaction: discord.Interaction, volume: app_commands.Range[int, 1, 100]):
    guild = interaction.guild
    vc = guild.voice_client
    
    vol_float = (volume / 100.0) * 0.05
    bot.volumes[guild.id] = vol_float

    if vc and vc.source:
        vc.source.volume = vol_float

    await update_music_embed(guild)
    await interaction.response.send_message(f"🔊 음량을 **{volume}%**로 설정했습니다.", ephemeral=True)

@bot.tree.command(name="스킵", description="현재 재생 중인 음악을 스킵합니다.")
async def skip_command(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("❌ 재생 중인 음악이 없습니다.", ephemeral=True)
    vc.stop()
    await interaction.response.send_message("⏭️ 다음 곡으로 넘어가겠습니다.", ephemeral=True)

@bot.tree.command(name="강제종료", description="음악 재생을 중지하고 음성 채널에서 퇴장합니다.")
async def stop_command(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    vc = interaction.guild.voice_client

    cancel_inactive_timer(guild_id)
    bot.music_queues[guild_id] = []
    bot.current_song[guild_id] = None
    await clear_queue_message(interaction.guild)

    if vc:
        await vc.disconnect()
        await update_music_embed(interaction.guild)
        await update_bot_presence()
        await interaction.response.send_message("⏹️ 음성 채널에서 퇴장하고 대기열을 초기화했습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 접속 중인 음성 채널이 없습니다.", ephemeral=True)

async def get_spotify_query(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if match:
            return match.group(1).split('|')[0].strip()
    except Exception as e:
        print(f"⚠️ 스포티파이 파싱 실패: {e}")
    return None

async def search_yt(query):
    if "open.spotify.com" in query:
        parsed_title = await get_spotify_query(query)
        if parsed_title:
            query = parsed_title
        else:
            raise Exception("스포티파이 정보를 가져오지 못했습니다.")

    loop = asyncio.get_event_loop()
    yt_input = query if query.startswith("http") else f"ytsearch1:{query}"

    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(yt_input, download=False))
    if data is None:
        raise Exception("추출된 데이터가 없습니다.")

    songs = []
    entries = data.get('entries', [data])
    for entry in entries:
        if entry:
            audio_url = entry.get('url')
            if not audio_url and 'formats' in entry:
                for f in entry['formats']:
                    if f.get('acodec') != 'none' and f.get('url'):
                        audio_url = f.get('url')
                        break
            
            songs.append({
                'title': entry.get('title', '제목 없음'),
                'url': audio_url,
                'thumbnail': entry.get('thumbnail')
            })

    return songs

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id

    if guild_id in bot.music_channels and message.channel.id == bot.music_channels[guild_id]['channel_id']:
        if message.id != bot.music_channels[guild_id]['message_id']:
            query = message.content.strip()
            try:
                await message.delete()
            except Exception:
                pass

            if not message.author.voice:
                return

            voice_channel = message.author.voice.channel
            vc = message.guild.voice_client

            if not vc:
                vc = await voice_channel.connect()
                await update_queue_message(message.guild)
            elif vc.channel != voice_channel:
                await vc.move_to(voice_channel)

            try:
                songs_data = await search_yt(query)
                for song_data in songs_data:
                    bot.music_queues.setdefault(guild_id, []).append({
                        'title': song_data['title'],
                        'url': song_data['url'],
                        'thumbnail': song_data['thumbnail'],
                        'requester': message.author
                    })

                if not vc.is_playing() and not vc.is_paused():
                    await play_next_song(message.guild)
                else:
                    cancel_inactive_timer(guild_id)
                    await update_queue_message(message.guild)
            except Exception as e:
                print(f"❌ 검색 오류: {e}")

bot.run(MUSIC_TOKEN)
