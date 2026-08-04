import io, os, re, asyncio, discord
from typecast import Typecast
from num2words import num2words
from initial_config import INITIAL_REPLACEMENTS
from korean_romanizer.romanizer import Romanizer
from typecast.models import TTSRequest, Output, PresetPrompt

client = Typecast()

def auto_roman_to_korean(text: str) -> str:
    text = text.replace("_", " ").replace("-", " ")
    words = text.split()
    processed_words = []

    for word in words:
        clean_word = re.sub(r'[^a-zA-Z]', '', word)
        if clean_word:
            try:
                r = Romanizer(clean_word.lower())
                korean_word = r.pronounce()
                word = word.replace(clean_word, korean_word)
            except Exception:
                pass
        processed_words.append(word)

    return " ".join(processed_words)

def convert_numbers_to_korean(text: str) -> str:
    def replace_num(match):
        num_str = match.group()
        try:
            return num2words(int(num_str), lang='ko')
        except Exception:
            return num_str

    return re.sub(r'\d+', replace_num, text)

def generate_typecast_tts(text: str, settings: dict) -> bytes:
    voice_id = settings.get('voice_name', 'tc_69fc0cff784968297fb45daa')
    tempo = settings.get('tempo', 1.0)
    pitch = settings.get('pitch', 0)
    emotion_preset = settings.get('emotion_preset', 'normal')
    emotion_intensity = settings.get('emotion_intensity', 1.0)

    try:
        response = client.text_to_speech(TTSRequest(
            text=text,
            model="ssfm-v30",
            voice_id=voice_id,
            prompt=PresetPrompt(
                emotion_type="preset",
                emotion_preset=emotion_preset,
                emotion_intensity=emotion_intensity
            ),
            output=Output(
                audio_tempo=tempo,
                audio_pitch=pitch
            )
        ))

        return response.audio_data

async def play_tts(vc, filename, bot):
    ffmpeg_executable = "./ffmpeg.exe" if os.path.exists("./ffmpeg.exe") else "ffmpeg"
    ffmpeg_options = {'options': '-vn'}

    try:
        raw_audio = discord.FFmpegPCMAudio(filename, executable=ffmpeg_executable, **ffmpeg_options)
        audio_source = discord.PCMVolumeTransformer(raw_audio, volume=1.0)

        def after_playing(error):
            asyncio.run_coroutine_threadsafe(remove_file_safely(filename), bot.loop)

        vc.play(audio_source, after=after_playing)

async def remove_file_safely(filepath):
    await asyncio.sleep(1)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)

async def delete_message_after_delay(message, delay=600):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
