import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl  # Use yt-dlp for better compatibility
import logging

# Logger setup
logger = logging.getLogger(__name__)

# Configure YouTube downloader options
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

# Initialize YouTube downloader
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def search_youtube_audio(self, query):
        """Search YouTube for a video and return the audio stream URL."""
        try:
            # Extract info and get the audio stream URL
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            audio_url = info.get('url')  # This will provide a direct link to the audio stream
            return audio_url
        except Exception as e:
            logger.error(f"Error extracting audio stream from YouTube: {e}")
            return None

    @app_commands.command(name="join", description="Join the user's voice channel.")
    async def join(self, interaction: discord.Interaction):
        """Join the user's voice channel."""
        try:
            if interaction.user.voice:
                channel = interaction.user.voice.channel
                if interaction.guild.voice_client is None:
                    await channel.connect()
                    await interaction.response.send_message("Joined the voice channel!")
                    logger.info(f"Joined voice channel: {channel}")
                else:
                    await interaction.response.send_message("I'm already connected to a voice channel.")
            else:
                await interaction.response.send_message("You're not in a voice channel.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to join the voice channel.")
            logger.error(f"Failed to join voice channel: {e}")

    @app_commands.command(name="play", description="Play music from a YouTube search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play music from a YouTube search query."""
        try:
            # Defer response to avoid timeout
            await interaction.response.defer()

            voice_client = interaction.guild.voice_client
            if not voice_client:
                await self.join(interaction)  # Join voice channel if not connected
                voice_client = interaction.guild.voice_client

            # Search and play the music
            audio_url = await self.search_youtube_audio(query)
            if audio_url is None:
                await interaction.followup.send("Could not find the song or audio stream.")
                return

            if voice_client.is_playing():
                voice_client.stop()

            voice_client.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options))
            await interaction.followup.send(f"Now playing: {query}")
            logger.info(f"Playing audio stream from URL: {audio_url}")

        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play audio stream: {e}")

    @app_commands.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel."""
        try:
            voice_client = interaction.guild.voice_client
            if voice_client:
                await voice_client.disconnect()
                await interaction.response.send_message("Disconnected from the voice channel.")
                logger.info("Disconnected from voice channel.")
            else:
                await interaction.response.send_message("I'm not connected to a voice channel.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to disconnect.")
            logger.error(f"Failed to disconnect: {e}")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))

# test to connect the branches