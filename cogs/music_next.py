import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class NextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = {}  # Track whether playback is active per guild

    async def play_next(self, guild_id, voice_client):
        """Play the next song in the queue, if available."""
        if guild_id not in self.bot.queues or not self.bot.queues[guild_id]:
            self.is_playing[guild_id] = False
            logger.info(f"Queue is empty for guild {guild_id}. Stopping playback.")
            return

        next_song = self.bot.queues[guild_id].popleft()
        self.is_playing[guild_id] = True
        try:
            logger.info(f"Attempting to play: {next_song['title']} for guild {guild_id}.")
            voice_client.play(
                discord.FFmpegPCMAudio(next_song['audio_url'], options="-vn"),
                after=lambda e: self.bot.loop.create_task(self._on_song_end(guild_id, voice_client))
            )
        except Exception as e:
            logger.error(f"Error playing next song for guild {guild_id}: {e}")
            self.is_playing[guild_id] = False

    async def _on_song_end(self, guild_id, voice_client):
        """Callback when a song ends. Automatically play the next one."""
        logger.info(f"Song ended for guild {guild_id}. Attempting to play next.")
        if guild_id in self.is_playing and self.is_playing[guild_id]:
            await self.play_next(guild_id, voice_client)

    @app_commands.command(name="next", description="Skip to the next song in the queue.")
    async def next_song(self, interaction: discord.Interaction):
        """Skip to the next song manually."""
        try:
            guild_id = interaction.guild.id
            voice_client = interaction.guild.voice_client

            # Check if the bot is connected to a voice channel
            if not voice_client or not voice_client.is_connected():
                await interaction.response.send_message("I'm not connected to a voice channel.")
                logger.warning(f"Bot is not connected to a voice channel in guild {guild_id}.")
                return

            # Check if the queue is empty
            if guild_id not in self.bot.queues or not self.bot.queues[guild_id]:
                await interaction.response.send_message("The queue is empty. There's nothing to play next.")
                logger.info(f"No songs in queue for guild {guild_id}.")
                return

            # Stop the current song, triggering the `after` callback
            if voice_client.is_playing():
                voice_client.stop()
                logger.info(f"Stopped current song for guild {guild_id}, skipping to next.")
            else:
                # If nothing is playing, manually call play_next
                logger.info(f"No song currently playing in guild {guild_id}. Playing next manually.")
                await self.play_next(guild_id, voice_client)

            await interaction.response.send_message("Skipping to the next song.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to skip the song.")
            logger.error(f"Failed to skip song in guild {guild_id}: {e}")

async def setup(bot):
    await bot.add_cog(NextCog(bot))
