import discord
from discord.ext import commands, tasks
import logging
from discord import app_commands

logger = logging.getLogger(__name__)

class NextCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = {}  # Track whether playback is active per guild
        self.background_task.start()  # Start the background task on cog load

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
                logger.warning(f"Bot is not connected to a voice channel in guild {guild_id}.")
                return

            # Check if the queue is empty
            if guild_id not in self.bot.queues or not self.bot.queues[guild_id]:
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

            logger.info(f"/next command executed successfully for guild {guild_id}.")
        except Exception as e:
            logger.error(f"Failed to skip song in guild {guild_id}: {e}")

    @tasks.loop(seconds=5)  # Periodically checks every 5 seconds
    async def background_task(self):
        """Background task to automatically play the next song."""
        for guild in self.bot.guilds:
            guild_id = guild.id
            voice_client = guild.voice_client

            if not voice_client or not voice_client.is_connected():
                continue  # Skip if the bot is not connected to a voice channel

            # Check if something is playing or if the queue is empty
            if not voice_client.is_playing() and guild_id in self.bot.queues and self.bot.queues[guild_id]:
                logger.info(f"Background task: No song playing in guild {guild_id}, starting next song.")
                await self.play_next(guild_id, voice_client)

    @background_task.before_loop
    async def before_background_task(self):
        """Ensure the bot is ready before starting the background task."""
        await self.bot.wait_until_ready()

    def cog_unload(self):
        """Cancel the background task when the cog is unloaded."""
        self.background_task.cancel()

async def setup(bot):
    await bot.add_cog(NextCog(bot))


# class MusicControlView(discord.ui.View):
#     def __init__(self, cog, voice_client):
#         super().__init__(timeout=None)
#         self.cog = cog
#         self.voice_client = voice_client
#         self.is_paused = False  # Start with playback not paused



