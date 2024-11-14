import discord
from discord import app_commands
from discord.ext import commands
import youtube_dl
import logging

# Get a logger instance for this module
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
        self.bot = bot  # Initialize the cog with the bot instance

    async def search_youtube(self, query):
        """Search YouTube for a video and return the URL."""
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return info['webpage_url']
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return None

    @app_commands.command(name="join", description="Join the user's voice channel.")
    async def join(self, interaction: discord.Interaction):
        """Join the user's voice channel."""
        try:
            if interaction.user.voice:
                channel = interaction.user.voice.channel
                await channel.connect()
                await interaction.response.send_message("Joined the voice channel!")
                logger.info(f"Joined voice channel: {channel}")
            else:
                await interaction.response.send_message("You're not in a voice channel.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to join the voice channel.")
            logger.error(f"Failed to join voice channel: {e}")

    @app_commands.command(name="play", description="Play music from a YouTube search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play music from a YouTube search query."""
        try:
            voice_client = interaction.guild.voice_client
            if not voice_client:
                await self.join(interaction)  # Join voice channel if not connected
                voice_client = interaction.guild.voice_client

            # Search and play the music
            url = await self.search_youtube(query)
            if url is None:
                await interaction.response.send_message("Could not find the song.")
                return

            if voice_client.is_playing():
                voice_client.stop()

            voice_client.play(discord.FFmpegPCMAudio(url, **ffmpeg_options))
            await interaction.response.send_message(f"Now playing: {url}")
            logger.info(f"Playing song from URL: {url}")

        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")

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
    # Function to add the cog to the bot during setup
    await bot.add_cog(MusicCog(bot))
