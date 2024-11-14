# ping.py
import discord
from discord import app_commands
from discord.ext import commands
import logging 

# Get a logger instance for this module
logger = logging.getLogger(__name__)

class SayHiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Initialize the cog with the bot instance

    @app_commands.command(name='sayhi', description='Saying Hi')
    async def say_hi(self, interaction: discord.Interaction):
        try:
            
            # Send the latency to the user as a response to the interaction
            await interaction.response.send_message(f"Hello muthafucka")
            
        except Exception as e:
            # Handle any errors that occur during the execution of the ping command
            await interaction.response.send_message('An error occurred while processing the say hi command.')
            logger.error(f'Failed to execute say hi command: {e}')


async def setup(bot):
    # Function to add the cog to the bot during setup
    await bot.add_cog(SayHiCog(bot))