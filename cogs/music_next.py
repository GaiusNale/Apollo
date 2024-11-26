import discord
from discord.ext import commands, tasks
import logging
from discord import app_commands

logger = logging.getLogger(__name__)

class NextCog(commands.Cog):
    def __init__(self, bot, queue_manager):
        self.bot = bot
        self.is_playing = {}
        self.queue_manager = queue_manager
        self.background_task.before_loop(self.before_background_task) #Corrected this line
        self.background_task.start()

    async def play_next(self, guild_id, voice_client):
        next_song = self.queue_manager.pop_from_queue(guild_id)
        if not next_song:
            self.is_playing[guild_id] = False
            logger.info(f"Queue is empty for guild {guild_id}. Stopping playback.")
            return

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
        logger.info(f"Song ended for guild {guild_id}. Attempting to play next.")
        if guild_id in self.is_playing and self.is_playing[guild_id]:
            await self.play_next(guild_id, voice_client)

    @app_commands.command(name="next", description="Skip to the next song in the queue.")
    async def next_song(self, interaction: discord.Interaction):
        try:
            guild_id = interaction.guild.id
            voice_client = interaction.guild.voice_client

            if not voice_client or not voice_client.is_connected():
                await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
                logger.warning(f"Bot is not connected to a voice channel in guild {guild_id}.")
                return

            if not self.queue_manager.is_queue_available(guild_id):
                await interaction.response.send_message("No songs are in the queue.", ephemeral=True)
                logger.info(f"No songs in queue for guild {guild_id}.")
                return

            if voice_client.is_playing():
                voice_client.stop()
                await interaction.response.send_message("Skipping to the next song.", ephemeral=True)
                logger.info(f"Stopped current song for guild {guild_id}, skipping to next.")
            else:
                logger.info(f"No song currently playing in guild {guild_id}. Playing next manually.")
                await self.play_next(guild_id, voice_client)
                await interaction.response.send_message("Playing the next song in the queue.", ephemeral=True)

            logger.info(f"/next command executed successfully for guild {guild_id}.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while skipping the song.", ephemeral=True)
            logger.error(f"Failed to skip song in guild {guild_id}: {e}")

    @tasks.loop(seconds=5)
    async def background_task(self):
        for guild in self.bot.guilds:
            guild_id = guild.id
            voice_client = guild.voice_client

            if not voice_client or not voice_client.is_connected():
                continue

            if not voice_client.is_playing() and self.queue_manager.is_queue_available(guild_id):
                logger.info(f"Background task: No song playing in guild {guild_id}, starting next song.")
                await self.play_next(guild_id, voice_client)

    @background_task.before_loop
    async def before_background_task(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.background_task.cancel()

async def setup(bot, queue_manager): #Corrected this line
    await bot.add_cog(NextCog(bot, queue_manager)) #Corrected this line