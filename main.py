import os
import discord
import logging  # Import logging
from discord.ext import commands
from decouple import config
from logs.log_config import setup_logging  # Import the logging setup function
from queue_manager import QueueManager

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Intents: enable message content intent to avoid warnings and ensure proper functionality
intents = discord.Intents.default()
intents.message_content = True  # Enable privileged intent for reading message content

# Initialize the bot with command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

queue_manager = QueueManager()
bot.QueueManager = queue_manager


# Settings
DISCORD_TOKEN = config("DISCORD_TOKEN", default=None)
AUTHORIZED_USER_ID = 759228225271496756

# Load the cogs from the cogs subfolder
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logger.info(f"Loaded cog: {filename}")
            except Exception as e:
                logger.error(f"Failed to load cog {filename}: {e}")

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    await load_cogs()

# AdminSync command to sync commands globally
@bot.command(name='as', description="Sync bot commands globally")
async def adminsync(ctx):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("You are not authorized to use this command.")
        return

    await ctx.send("Syncing commands globally...")
    try:
        await bot.tree.sync()
        logger.info("Commands synced globally.")
        await ctx.send("Commands synced globally successfully.")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
        await ctx.send(f"Error syncing commands: {e}")

# Handling unforeseen errors in commands
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send("You are not authorized to use this command.")
    else:
        logger.error(f"An error occurred: {error}")

# Runs the bot 
if __name__ == '__main__':
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f'Failed to start bot: {e}')
