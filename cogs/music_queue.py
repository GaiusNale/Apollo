import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl
import logging
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from decouple import config

logger = logging.getLogger(__name__)

# YouTube downloader configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Spotify API setup
def get_spotify_client():
    SPOT_CLIENT_ID = config("SPOT_CLIENT_ID", default=None)
    SPOT_SECRET = config("SPOT_SECRET", default=None)

    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOT_CLIENT_ID,
        client_secret=SPOT_SECRET
    )
    return Spotify(client_credentials_manager=client_credentials_manager)

async def search_song_on_spotify(spotify, query):
    try:
        results = spotify.search(q=query, type="track", limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            return {
                "song_title": track["name"],
                "artist_name": track["artists"][0]["name"],
                "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            }
        else:
            return None
    except Exception as e:
        logger.error(f"Error searching Spotify: {e}")
        return None


class QueueCog(commands.Cog):
    def __init__(self, bot, queue_manager):
        self.bot = bot
        self.spotify = get_spotify_client()
        self.queue_manager = queue_manager

    async def search_youtube_audio(self, query):
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {
                "audio_url": info['formats'][0]['url'], #More robust URL extraction
                "title": info['title'],
                "duration": info['duration'],
                "thumbnail": info.get('thumbnails', [{}])[-1].get('url', None) #Safer thumbnail extraction
            }
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return None

    @app_commands.command(name="add", description="Add a song to the queue.")
    async def add(self, interaction: discord.Interaction, query: str):
        try:
            await interaction.response.defer()

            spotify_data = await search_song_on_spotify(self.spotify, query)
            spotify_title = spotify_data["song_title"] if spotify_data else query
            spotify_artist = spotify_data["artist_name"] if spotify_data else "Unknown Artist"

            audio_data = await self.search_youtube_audio(spotify_title + " " + spotify_artist)
            if not audio_data:
                await interaction.followup.send("Could not find the song.")
                return

            self.queue_manager.add_to_queue(
                guild_id=interaction.guild.id,
                song={
                    "title": spotify_title,
                    "artist": spotify_artist,
                    "audio_url": audio_data["audio_url"],
                    "thumbnail": audio_data["thumbnail"],
                    "duration": audio_data["duration"]
                }
            )

            await interaction.followup.send(f"Added to queue: **{spotify_title}** by **{spotify_artist}**")
            logger.info(f"Added to queue: {spotify_title} for guild {interaction.guild.id}")
        except Exception as e:
            await interaction.followup.send("An error occurred while adding the song to the queue.")
            logger.error(f"Failed to add song to queue: {e}")

    @app_commands.command(name="queue", description="View the current song queue.")
    async def view_queue(self, interaction: discord.Interaction):
        try:
            guild_id = interaction.guild.id
            queue = self.queue_manager.get_queue(guild_id)

            if not queue:
                await interaction.response.send_message("The queue is empty.")
                return

            queue_display = "\n".join([
                f"{i + 1}. **{song['title']}** by **{song['artist']}**"
                for i, song in enumerate(queue)
            ])
            await interaction.response.send_message(f"Current Queue:\n{queue_display}")
            logger.info(f"Displayed the current queue for guild {guild_id}")
        except Exception as e:
            await interaction.response.send_message("An error occurred while displaying the queue.")
            logger.error(f"Failed to display queue: {e}")

    @app_commands.command(name="clear", description="Clear the current song queue.")
    async def clear_queue(self, interaction: discord.Interaction):
        try:
            guild_id = interaction.guild.id
            self.queue_manager.clear_queue(guild_id)

            await interaction.response.send_message("The queue has been cleared.")
            logger.info(f"Cleared the queue for guild {guild_id}")
        except Exception as e:
            await interaction.response.send_message("An error occurred while clearing the queue.")
            logger.error(f"Failed to clear queue: {e}")


async def setup(bot, queue_manager): #Corrected this line
    await bot.add_cog(QueueCog(bot, queue_manager)) #Corrected this line