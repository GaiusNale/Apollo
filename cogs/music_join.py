import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class JoinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Join the user's voice channel.")
    async def join(self, interaction: discord.Interaction):
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

async def setup(bot):
    await bot.add_cog(JoinCog(bot))
