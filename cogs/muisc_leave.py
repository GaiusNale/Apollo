import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class LeaveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction):
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
    await bot.add_cog(LeaveCog(bot))
