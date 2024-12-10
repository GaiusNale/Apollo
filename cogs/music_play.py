import discord
from discord import app_commands
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import logging
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from decouple import config

# Set up logging
logger = logging.getLogger(__name__)

# YouTube downloader configuration
ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',  # Increased from 128 for better audio quality
    }],
    'buffersize': 1024 * 1024 * 10,  # 10MB buffer is good
    'retries': 3,  # Add retry mechanism
    'fragment_retries': 3,  # Retry fragmented downloads
    'socket_timeout': 15,  # Increase socket timeout
    'source_address': '0.0.0.0',  # Bind to all network interfaces
    'no_color': True,
    'ignoreerrors': False,  # Be strict about errors
    'no_warnings': True,
    'quiet': True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # Added reconnection options
    'options': '-vn -err_detect ignore_err',  # Added error detection ignore
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Spotify API setup
def get_spotify_client():
    """Initialize and return the Spotify client using credentials."""
    SPOT_CLIENT_ID = config("SPOT_CLIENT_ID", default=None)
    SPOT_SECRET = config("SPOT_SECRET", default=None)

    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOT_CLIENT_ID,
        client_secret=SPOT_SECRET
    )
    spotify = Spotify(client_credentials_manager=client_credentials_manager)
    return spotify

async def search_song_on_spotify(spotify, query):
    """Search for a song on Spotify using the provided query."""
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

class PlayCog(commands.Cog):
    """Cog for handling music playback commands."""
    def __init__(self, bot):
        self.bot = bot
        self.spotify = get_spotify_client()
        self.queue_manager = bot.QueueManager
        self.song_check_loop.start()

    def cog_unload(self):
        """Cleanup when the cog is unloaded."""
        self.song_check_loop.cancel()

    @tasks.loop(seconds=5)
    async def song_check_loop(self):
        """Periodic task to check and play the next song in the queue."""
        for guild in self.bot.guilds:
            voice_client = guild.voice_client
            if voice_client and not voice_client.is_playing() and not voice_client.is_paused():
                logger.info("No song is currently playing. Checking queue.")
                next_song = self.queue_manager.pop_from_queue(guild.id)
                if next_song:
                    try:
                        voice_client.play(
                            discord.FFmpegPCMAudio(next_song['audio_url'], **ffmpeg_options),
                            after=lambda e: logger.info(f"Finished playing: {next_song['title']}") if not e else logger.error(f"Error during playback: {e}")
                        )

                        # Prepare and send embed message
                        embed = discord.Embed(
                            title="Now Playing",
                            description=f"[{next_song['title']}]({next_song['audio_url']})",
                            color=discord.Color.green()
                        )
                        if next_song['thumbnail']:
                            embed.set_thumbnail(url=next_song['thumbnail'])
                        embed.add_field(name="Artist", value=next_song['artist'], inline=True)
                        embed.add_field(name="Duration", value=f"{next_song['duration'] // 60}:{next_song['duration'] % 60:02}", inline=True)

                        # Use MusicControlView from bot attribute
                        view = self.bot.MusicControlView(self, voice_client)
                        await voice_client.channel.send(embed=embed, view=view)

                        logger.info(f"Playing next song: {next_song['title']} by {next_song['artist']}")
                    except Exception as e:
                        logger.error(f"Failed to play next song: {e}")

    async def join_voice_channel(self, interaction: discord.Interaction):
        """Join the voice channel that the user is currently in."""
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            if interaction.guild.voice_client is None:
                try:
                    vc = await channel.connect()
                    return vc
                except Exception as e:
                    logger.error(f"Error connecting to voice channel: {e}")
                    await interaction.followup.send("Could not connect to the voice channel.", ephemeral=True)
                    return None
            else:
                return interaction.guild.voice_client
        else:
            await interaction.followup.send("You are not connected to a voice channel.", ephemeral=True)
            return None

    async def skip_song(self, interaction: discord.Interaction, voice_client: discord.VoiceClient):
        """Skip the current song and play the next one in the queue."""
        try:
            guild_id = interaction.guild.id
            next_song = self.queue_manager.pop_from_queue(guild_id)

            if not next_song:
                voice_client.stop()
                await interaction.followup.send("Queue is empty. Stopping playback.")
                return

            voice_client.stop()
            voice_client.play(
                discord.FFmpegPCMAudio(next_song['audio_url'], **ffmpeg_options),
                after=lambda e: logger.info(f"Finished playing: {next_song['title']}") if not e else logger.error(f"Error during playback: {e}")
            )

            # Prepare and send embed message
            embed = discord.Embed(
                title="Now Playing",
                description=f"[{next_song['title']}]({next_song['audio_url']})",
                color=discord.Color.green()
            )
            if next_song['thumbnail']:
                embed.set_thumbnail(url=next_song['thumbnail'])
            embed.add_field(name="Artist", value=next_song['artist'], inline=True)
            embed.add_field(name="Duration", value=f"{next_song['duration'] // 60}:{next_song['duration'] % 60:02}", inline=True)

            # Use MusicControlView from bot attribute
            view = self.bot.MusicControlView(self, voice_client)
            await interaction.followup.send(embed=embed, view=view)
            logger.info(f"Skipped to: {next_song['title']} by {next_song['artist']}")
        except Exception as e:
            await interaction.followup.send("An error occurred while skipping the song.")
            logger.error(f"Failed to skip song: {e}")

    async def search_youtube_audio(self, query):
        """Search for audio on YouTube using the provided query."""
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info and info['entries']:
                video = info['entries'][0]
                return {
                    "audio_url": video['url'],
                    "title": video['title'],
                    "duration": video['duration'],
                    "thumbnail": video.get('thumbnails', [{}])[-1].get('url', None)
                }
            else:
                logger.error("No results found for the query.")
                return None
        except Exception as e:
            logger.error(f"Error extracting YouTube audio: {e}")
            return None

    @app_commands.command(name="play", description="Play music from a YouTube search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play a song based on a query from YouTube or Spotify."""
        try:
            await interaction.response.defer()
            voice_client = await self.join_voice_channel(interaction)
            if not voice_client:
                return

            spotify_data = await search_song_on_spotify(self.spotify, query)
            spotify_title = spotify_data["song_title"] if spotify_data else query
            spotify_artist = spotify_data["artist_name"] if spotify_data else "Unknown Artist"
            spotify_thumbnail = spotify_data["album_cover"] if spotify_data else None

            audio_data = await self.search_youtube_audio(spotify_title + " " + spotify_artist)
            if not audio_data:
                await interaction.followup.send("Could not find the song.")
                return

            self.queue_manager.add_to_queue(
                interaction.guild.id,
                {
                    "title": spotify_title,
                    "artist": spotify_artist,
                    "audio_url": audio_data["audio_url"],
                    "thumbnail": spotify_thumbnail or audio_data["thumbnail"],
                    "duration": audio_data["duration"]
                }
            )

            if not voice_client.is_playing():
                await self.skip_song(interaction, voice_client)

            await interaction.followup.send("Song added to the queue.")
        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")

async def setup(bot):
    """Set up the PlayCog for the bot."""
    await bot.add_cog(PlayCog(bot))


