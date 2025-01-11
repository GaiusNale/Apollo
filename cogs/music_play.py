import discord
from discord import app_commands
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import logging
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from decouple import config
import re
import asyncio

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
    'buffersize': 1024 * 1024 * 10,  # 10MB buffer
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

SPOTIFY_TRACK_REGEX = re.compile(r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)")
YOUTUBE_VIDEO_REGEX = re.compile(r"https?://(www\.)?(youtube\.com|youtu\.be)/(watch\?v=)?([a-zA-Z0-9_-]+)")
SPOTIFY_PLAYLIST_REGEX = re.compile(r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)")

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

async def get_spotify_track_info(spotify, track_id):
    """Get track information from Spotify using the track ID."""
    try:
        track = spotify.track(track_id)
        return {
            "song_title": track["name"],
            "artist_name": track["artists"][0]["name"],
            "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None
        }
    except Exception as e:
        logger.error(f"Error fetching Spotify track info: {e}")
        return None

# Parses through the playlist a song at a time
async def get_spotify_playlist_tracks(spotify, playlist_id):
    """Get tracks from a Spotify playlist using the playlist ID."""
    # Inshallah this works
    try:
        results = spotify.playlist_tracks(playlist_id)
        tracks = []
        for item in results['items']:
            track = item['track']
            tracks.append({
                "song_title": track["name"],
                "artist_name": track["artists"][0]["name"],
                "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            })
        return tracks
    except Exception as e:
        logger.error(f"Error fetching Spotify playlist tracks: {e}")
        return []

async def get_youtube_video_info(video_id):
    """Get video information from YouTube using the video ID."""
    try:
        info = ytdl.extract_info(video_id, download=False)
        return {
            "audio_url": info['url'],
            "title": info['title'],
            "duration": info['duration'],
            "thumbnail": info.get('thumbnails', [{}])[-1].get('url', None)
        }
    except Exception as e:
        logger.error(f"Error fetching YouTube video info: {e}")
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

    @tasks.loop(seconds=10)
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
                description=f"**[{next_song['title']}]({next_song['audio_url']})**",
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

    @app_commands.command(name="play", description="Play music from a YouTube search query or a Spotify/YouTube link.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play a song based on a query from YouTube, Spotify, or a direct link."""
        try:
            await interaction.response.defer()
            voice_client = await self.join_voice_channel(interaction)
            if not voice_client:
                return

            spotify_playlist_match = SPOTIFY_PLAYLIST_REGEX.match(query)
            spotify_match = SPOTIFY_TRACK_REGEX.match(query)
            youtube_match = YOUTUBE_VIDEO_REGEX.match(query)

            spotify_data = None  # Initialize spotify_data to avoid referencing before assignment

            if spotify_playlist_match:
                playlist_id = spotify_playlist_match.group(1)
                tracks = await get_spotify_playlist_tracks(self.spotify, playlist_id)
                if not tracks:
                    await interaction.followup.send("Could not find the Spotify playlist.")
                    return

                # Play the first song in the playlist
                first_track = tracks.pop(0)
                audio_data = await self.search_youtube_audio(first_track["song_title"] + " " + first_track["artist_name"] + " official audio")
                if not audio_data:
                    await interaction.followup.send("Could not find the first song in the playlist.")
                    return

                self.queue_manager.add_to_queue(
                    interaction.guild.id,
                    {
                        "title": first_track["song_title"],
                        "artist": first_track["artist_name"],
                        "audio_url": audio_data["audio_url"],
                        "thumbnail": first_track["album_cover"] or audio_data["thumbnail"],
                        "duration": audio_data["duration"]
                    }
                )

                if not voice_client.is_playing():
                    await self.skip_song(interaction, voice_client)

                await interaction.followup.send(f"Playing first song in the playlist: **{first_track['song_title']}** by **{first_track['artist_name']}**")

                # Periodically add the remaining songs to the queue
                for track in tracks:
                    await self.add_song_to_queue(interaction.guild.id, track)
            elif spotify_match:
                track_id = spotify_match.group(1)
                spotify_data = await get_spotify_track_info(self.spotify, track_id)
                if not spotify_data:
                    await interaction.followup.send("Could not find the Spotify track.")
                    return
                audio_data = await self.search_youtube_audio(spotify_data["song_title"] + " " + spotify_data["artist_name"] + " official audio")
            elif youtube_match:
                video_id = youtube_match.group(4)
                audio_data = await get_youtube_video_info(video_id)
                if not audio_data:
                    await interaction.followup.send("Could not find the YouTube video.")
                    return
                spotify_data = {
                    "song_title": audio_data["title"],
                    "artist_name": "Unknown Artist",
                    "album_cover": audio_data["thumbnail"]
                }
            else:
                spotify_data = await search_song_on_spotify(self.spotify, query)
                spotify_title = spotify_data["song_title"] if spotify_data else query
                spotify_artist = spotify_data["artist_name"] if spotify_data else "Unknown Artist"
                spotify_thumbnail = spotify_data["album_cover"] if spotify_data else None
                audio_data = await self.search_youtube_audio(spotify_title + " " + spotify_artist + " official audio")

            if not audio_data:
                await interaction.followup.send("Could not find the song.")
                return

            self.queue_manager.add_to_queue(
                interaction.guild.id,
                {
                    "title": spotify_data["song_title"],
                    "artist": spotify_data["artist_name"],
                    "audio_url": audio_data["audio_url"],
                    "thumbnail": spotify_data["album_cover"] or audio_data["thumbnail"],
                    "duration": audio_data["duration"]
                }
            )

            if not voice_client.is_playing():
                await self.skip_song(interaction, voice_client)

            await interaction.followup.send("Song added to the queue.")
        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")

    async def add_song_to_queue(self, guild_id, track):
        """Add a song to the queue periodically."""
        try:
            await asyncio.sleep(10)  # Adjust the delay as needed
            audio_data = await self.search_youtube_audio(track["song_title"] + " " + track["artist_name"] + " official audio")
            if not audio_data:
                logger.error(f"Could not find the song: {track['song_title']} by {track['artist_name']}")
                return

            self.queue_manager.add_to_queue(
                guild_id,
                {
                    "title": track["song_title"],
                    "artist": track["artist_name"],
                    "audio_url": audio_data["audio_url"],
                    "thumbnail": track["album_cover"] or audio_data["thumbnail"],
                    "duration": audio_data["duration"]
                }
            )
            logger.info(f"Added to queue: {track['song_title']} by {track['artist_name']}")
        except Exception as e:
            logger.error(f"Failed to add song to queue: {e}")

async def setup(bot):
    """Set up the PlayCog for the bot."""
    await bot.add_cog(PlayCog(bot))



