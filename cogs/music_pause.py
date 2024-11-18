import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class PauseResumeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pause", description="Pause the current song.")
    async def pause(self, interaction: discord.Interaction):
        """Pause the currently playing song."""
        try:
            guild_id = interaction.guild.id
            voice_client = interaction.guild.voice_client

            if not voice_client or not voice_client.is_connected():
                await interaction.response.send_message("I'm not connected to a voice channel.")
                logger.warning(f"Bot is not connected to a voice channel in guild {guild_id}.")
                return

            if voice_client.is_playing():
                voice_client.pause()
                await interaction.response.send_message("Playback paused.")
                logger.info(f"Playback paused for guild {guild_id}.")
            else:
                await interaction.response.send_message("There's nothing playing to pause.")
                logger.info(f"Pause command issued with nothing playing in guild {guild_id}.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to pause playback.")
            logger.error(f"Failed to pause playback in guild {guild_id}: {e}")

    @app_commands.command(name="resume", description="Resume the paused song.")
    async def resume(self, interaction: discord.Interaction):
        """Resume the paused song."""
        try:
            guild_id = interaction.guild.id
            voice_client = interaction.guild.voice_client

            if not voice_client or not voice_client.is_connected():
                await interaction.response.send_message("I'm not connected to a voice channel.")
                logger.warning(f"Bot is not connected to a voice channel in guild {guild_id}.")
                return

            if voice_client.is_paused():
                voice_client.resume()
                await interaction.response.send_message("Playback resumed.")
                logger.info(f"Playback resumed for guild {guild_id}.")
            else:
                await interaction.response.send_message("There's nothing paused to resume.")
                logger.info(f"Resume command issued with nothing paused in guild {guild_id}.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while trying to resume playback.")
            logger.error(f"Failed to resume playback in guild {guild_id}: {e}")

async def setup(bot):
    await bot.add_cog(PauseResumeCog(bot))
