import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl  # Use yt-dlp for better compatibility
import logging
from collections import deque

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
        self.queue = deque()
        self.is_playing = False

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
    @app_commands.command(name="pause", description="Pause the currently playing music.")
    async def pause(self, interaction: discord.Interaction):
        """Pause the currently playing audio."""
        try:
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_playing():
                voice_client.pause()
                await interaction.response.send_message("Music paused. ⏸️")
                logger.info("Music paused.")
            else:
                await interaction.response.send_message("No music is currently playing.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to pause the music.")
            logger.error(f"Failed to pause music: {e}")

    @app_commands.command(name="resume", description="Resume the paused music.")
    async def resume(self, interaction: discord.Interaction):
        """Resume paused audio."""
        try:
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_paused():
                voice_client.resume()
                await interaction.response.send_message("Music resumed. ▶️")
                logger.info("Music resumed.")
            else:
                await interaction.response.send_message("No music is currently paused.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to resume the music.")
            logger.error(f"Failed to resume music: {e}")


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

    async def play_next(self, voice_client):
        """Play the next song in the queue."""
        if self.queue:
            self.is_playing = True
            next_song = self.queue.popleft()  # Get the next song from the queue
            voice_client.play(
                discord.FFmpegPCMAudio(next_song, **ffmpeg_options),
                after=lambda e: self.bot.loop.create_task(self.play_next(voice_client))
            )
            logger.info(f"Now playing: {next_song}")
        else:
            self.is_playing = False

    @app_commands.command(name="add", description="Add a song to the queue.")
    async def add(self, interaction: discord.Interaction, query: str):
        """Add a song to the queue."""
        try:
            await interaction.response.defer()

            audio_url = await self.search_youtube_audio(query)
            if audio_url is None:
                await interaction.followup.send("Could not find the song.")
                return

            self.queue.append(audio_url)
            await interaction.followup.send(f"Added to queue: {query}")
            logger.info(f"Added to queue: {audio_url}")

            voice_client = interaction.guild.voice_client
            if not self.is_playing and voice_client and not voice_client.is_playing():
                await self.play_next(voice_client)

        except Exception as e:
            await interaction.followup.send("An error occurred while adding the song to the queue.")
            logger.error(f"Failed to add song to queue: {e}")

    @app_commands.command(name="queue", description="View the current song queue.")
    async def view_queue(self, interaction: discord.Interaction):
        """Display the current song queue."""
        try:
            if not self.queue:
                await interaction.response.send_message("The queue is empty.")
                return

            queue_list = "\n".join([f"{i + 1}. {url}" for i, url in enumerate(self.queue)])
            await interaction.response.send_message(f"Current Queue:\n{queue_list}")
            logger.info("Displayed the current queue.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while displaying the queue.")
            logger.error(f"Failed to display queue: {e}")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))

