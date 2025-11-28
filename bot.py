# bot.py
# FREE Discord Voice Changer Bot
# Video -> Extract Audio -> Apply Effect -> Return MP3

import os
import asyncio
import aiohttp
import shutil
import subprocess
import tempfile

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")  # Bot Token from .env file

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def run_cmd(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout, proc.stderr


FFMPEG_EFFECTS = {
    "deep": lambda inp, out: [
        "ffmpeg", "-y", "-i", inp,
        "-af", "asetrate=44100*0.8,aresample=44100,atempo=1",
        "-vn", out
    ],
    "chipmunk": lambda inp, out: [
        "ffmpeg", "-y", "-i", inp,
        "-af", "asetrate=44100*1.5,aresample=44100,atempo=0.9",
        "-vn", out
    ],
    "robot": lambda inp, out: [
        "ffmpeg", "-y", "-i", inp,
        "-af", "afftfilt=real='re*0.6':imag='im*0.6',aecho=0.8:0.9:1000:0.3",
        "-vn", out
    ],
    "slow": lambda inp, out: [
        "ffmpeg", "-y", "-i", inp,
        "-af", "atempo=0.85",
        "-vn", out
    ],
    "fast": lambda inp, out: [
        "ffmpeg", "-y", "-i", inp,
        "-af", "atempo=1.3",
        "-vn", out
    ],
}

@bot.event
async def on_ready():
    print(f"Logged in as: {bot.user.name} (ID: {bot.user.id})")
    print("Bot is ready!")


async def download_file(url, dest_path):
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(await resp.read())


@bot.command(name="convert")
async def convert(ctx, effect: str = "deep"):
    if not ctx.message.attachments:
        await ctx.reply("❌ Attach a video.\nExample: `!convert deep` + attach video")
        return

    effect = effect.lower()
    if effect not in FFMPEG_EFFECTS:
        await ctx.reply("❌ Unknown effect. Use: deep, chipmunk, robot, slow, fast")
        return

    att = ctx.message.attachments[0]
    await ctx.reply("⬇️ Downloading video...")

    tmp = tempfile.mkdtemp(prefix="bot_")

    try:
        video = os.path.join(tmp, att.filename)
        audio = os.path.join(tmp, "audio.wav")
        processed = os.path.join(tmp, "processed.wav")
        output = os.path.join(tmp, "voice_changed.mp3")

        await download_file(att.url, video)

        await ctx.reply("🎵 Extracting audio...")
        code, out, err = run_cmd(
            ["ffmpeg", "-y", "-i", video, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", audio]
        )
        if code != 0:
            await ctx.reply("❌ Audio extract failed.")
            return

        await ctx.reply(f"🔊 Applying `{effect}` effect...")
        code, out, err = run_cmd(FFMPEG_EFFECTS[effect](audio, processed))
        if code != 0:
            await ctx.reply("❌ Effect processing failed.")
            return

        await ctx.reply("🎧 Converting to MP3...")
        code, out, err = run_cmd(
            ["ffmpeg", "-y", "-i", processed, "-vn", "-codec:a", "libmp3lame", "-qscale:a", "2", output]
        )
        if code != 0:
            await ctx.reply("❌ MP3 conversion failed.")
            return

        await ctx.reply("✅ Done!", file=discord.File(output))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


bot.run(TOKEN)
