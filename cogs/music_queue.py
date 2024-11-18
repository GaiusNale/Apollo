import discord
from discord import app_commands
from discord.ext import commands
from collections import deque
import yt_dlp as youtube_dl
import logging

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
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Access the bot instance

    async def search_youtube_audio(self, query):
        """Search YouTube for a video and return its audio URL and title."""
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {"audio_url": info['url'], "title": info['title']}
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return None

    @app_commands.command(name="add", description="Add a song to the queue.")
    async def add(self, interaction: discord.Interaction, query: str):
        """Add a song to the queue."""
        try:
            await interaction.response.defer()

            audio_data = await self.search_youtube_audio(query)
            if not audio_data:
                await interaction.followup.send("Could not find the song.")
                return

            guild_id = interaction.guild.id
            # Access the shared queues dictionary from the bot
            if guild_id not in self.bot.queues:
                self.bot.queues[guild_id] = deque()  # Initialize the queue for the guild

            self.bot.queues[guild_id].append(audio_data)  # Add audio data (title and URL) to the queue
            await interaction.followup.send(f"Added to queue: **{audio_data['title']}**")
            logger.info(f"Added to queue: {audio_data['title']} for guild {guild_id}")
        except Exception as e:
            await interaction.followup.send("An error occurred while adding the song to the queue.")
            logger.error(f"Failed to add song to queue: {e}")

    @app_commands.command(name="queue", description="View the current song queue.")
    async def view_queue(self, interaction: discord.Interaction):
        """Display the current song queue."""
        try:
            guild_id = interaction.guild.id
            # Access the shared queues dictionary from the bot
            if guild_id not in self.bot.queues or not self.bot.queues[guild_id]:
                await interaction.response.send_message("The queue is empty.")
                return

            queue = self.bot.queues[guild_id]
            queue_display = "\n".join([f"{i + 1}. {song['title']}" for i, song in enumerate(queue)])
            await interaction.response.send_message(f"Current Queue:\n{queue_display}")
            logger.info(f"Displayed the current queue for guild {guild_id}")
        except Exception as e:
            await interaction.response.send_message("An error occurred while displaying the queue.")
            logger.error(f"Failed to display queue: {e}")

async def setup(bot):
    await bot.add_cog(QueueCog(bot))
