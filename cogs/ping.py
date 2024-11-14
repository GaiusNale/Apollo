# ping.py
"""
This cog provides a simple slash command to check the bot's latency.
The command returns the round-trip time from the bot to the Discord server,
indicating how responsive the bot currently is.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging 

# Get a logger instance for this module
logger = logging.getLogger(__name__)

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Initialize the cog with the bot instance

    @app_commands.command(name='ping', description='Check the bot\'s latency.')
    async def ping(self, interaction: discord.Interaction):
        """A simple ping command to check the bot's latency."""
        try:
            # Calculate the bot's latency in milliseconds
            latency = round(self.bot.latency * 1000)  # Convert latency to milliseconds
            
            # Send the latency to the user as a response to the interaction
            await interaction.response.send_message(f'Pong! Latency: {latency}ms')
            
            # Log the successful execution of the ping command
            logger.info(f'Ping command executed. Latency: {latency}ms')
        except Exception as e:
            # Handle any errors that occur during the execution of the ping command
            await interaction.response.send_message('An error occurred while processing the ping command.')
            logger.error(f'Failed to execute ping command: {e}')

async def setup(bot):
    # Function to add the cog to the bot during setup
    await bot.add_cog(PingCog(bot))