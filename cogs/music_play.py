import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl
import logging

logger = logging.getLogger(__name__)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class PlayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = False

    async def search_youtube_audio(self, query):
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {"audio_url": info['url'], "title": info['title']}
        except Exception as e:
            logger.error(f"Error extracting audio stream: {e}")
            return None

    @app_commands.command(name="play", description="Play music from a YouTube search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        try:
            await interaction.response.defer()
            voice_client = interaction.guild.voice_client

            if not voice_client:
                join_cog = self.bot.get_cog("JoinCog")
                if join_cog:
                    await join_cog.join(interaction)
                voice_client = interaction.guild.voice_client

            audio_data = await self.search_youtube_audio(query)
            if not audio_data:
                await interaction.followup.send("Could not find the song.")
                return

            if voice_client.is_playing():
                voice_client.stop()

            voice_client.play(
                discord.FFmpegPCMAudio(audio_data['audio_url'], **ffmpeg_options),
                after=lambda e: logger.info(f"Finished playing: {query}") if e is None else logger.error(e)
            )
            await interaction.followup.send(f"Now playing: {audio_data['title']}")
            logger.info(f"Now playing: {audio_data['title']}")
        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")

async def setup(bot):
    await bot.add_cog(PlayCog(bot))
