import discord
from discord import app_commands
from discord.ext import commands, tasks
from urllib.parse import urlparse, parse_qs
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
        'preferredquality': '320',
    }],
}
ffmpeg_options = {
    'options': '-vn',
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
        # Clean and sanitize the query
        sanitized_query = query.strip().encode("ascii", "ignore").decode()
        results = spotify.search(q=sanitized_query, type="track", limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            return {
                "song_title": track["name"],
                "artist_name": track["artists"][0]["name"],
                "album_cover": track["album"]["images"][0]["url"] if track["album"]["images"] else None
            }
        else:
            logger.warning("No tracks found on Spotify for query: %s", sanitized_query)
            return None
    except Exception as e:
        logger.error(f"Error searching Spotify with query '{query}': {e}")
        return None
    
class MusicControlView(discord.ui.View):
    """UI view for controlling music playback with buttons."""
    def __init__(self, cog, voice_client):
        super().__init__(timeout=None)
        self.cog = cog
        self.voice_client = voice_client
        self.is_paused = False

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏸️", custom_id="pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle pause/resume of the current song."""
        if not self.voice_client.is_playing() and not self.is_paused:
            await interaction.response.send_message("No music is currently playing.", ephemeral=True)
            return

        if self.is_paused:
            self.voice_client.resume()
            self.is_paused = False
            button.emoji = "⏸️"
            await interaction.response.edit_message(content="Music resumed.", view=self)
        else:
            self.voice_client.pause()
            self.is_paused = True
            button.emoji = "▶️"
            await interaction.response.edit_message(content="Music paused.", view=self)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏹️", custom_id="stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop the currently playing or paused song."""
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            await interaction.response.send_message("Music stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is playing currently.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip to the next song in the queue."""
        await interaction.response.defer()
        await self.cog.skip_song(interaction, self.voice_client)

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

                        # Send embed to the voice channel
                        view = MusicControlView(self, voice_client)
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

            view = MusicControlView(self, voice_client)
            await interaction.followup.send(embed=embed, view=view)
            logger.info(f"Skipped to: {next_song['title']} by {next_song['artist']}")
        except Exception as e:
            await interaction.followup.send("An error occurred while skipping the song.")
            logger.error(f"Failed to skip song: {e}")

    async def search_youtube_audio(self, query):
        """Search for audio on YouTube using the provided query."""
        try:
            # Clean and sanitize the query
            sanitized_query = query.strip().encode("ascii", "ignore").decode()
            logger.info("Searching YouTube with sanitized query: %s", sanitized_query)

            # Extract video information using yt_dlp
            info = ytdl.extract_info(f"ytsearch:{sanitized_query}", download=False)
            if 'entries' in info and info['entries']:
                video = info['entries'][0]  # First result

                # Extract metadata with fallback defaults
                title = video.get('title', 'Unknown Title')
                uploader = video.get('uploader', 'Unknown Artist')
                duration = video.get('duration', 0)  # Duration in seconds
                thumbnail = video.get('thumbnails', [{}])[-1].get('url', None)  # Last thumbnail URL
                audio_url = video.get('url', '')

                logger.info(f"Extracted YouTube metadata: title={title}, artist={uploader}, duration={duration}")

                return {
                    "audio_url": audio_url,
                    "title": title,
                    "artist": uploader,
                    "duration": duration,
                    "thumbnail": thumbnail,
                }
            else:
                logger.error("No results found for the query: %s", sanitized_query)
                return None
        except Exception as e:
            logger.error(f"Error extracting YouTube audio with query '{query}': {e}")
            return None
        
    async def process_spotify_query(self, query):
        """Process a Spotify link and return metadata for tracks."""
        try:
            parsed_url = urlparse(query)
            path_parts = parsed_url.path.split("/")

            if "track" in path_parts:
                # Handle single track
                spotify_track_id = path_parts[path_parts.index("track") + 1]
                spotify_track = self.spotify.track(spotify_track_id)
                return [{
                    "song_title": spotify_track["name"],
                    "artist_name": spotify_track["artists"][0]["name"],
                    "album_cover": (
                        spotify_track["album"]["images"][0]["url"]
                        if spotify_track["album"]["images"]
                        else None
                    )
                }]

            elif "playlist" in path_parts:
                # Handle playlist
                spotify_playlist_id = path_parts[path_parts.index("playlist") + 1]
                logger.info(f"Fetching playlist: {spotify_playlist_id}")
                
                try:
                    playlist_tracks = self.spotify.playlist_tracks(
                        spotify_playlist_id, 
                        market="US"  # Specify a market to handle region restrictions
                    )
                except Exception as e:
                    logger.error(f"Failed to fetch playlist tracks: {e}")
                    return None

                tracks = []
                for item in playlist_tracks["items"]:
                    track = item["track"]
                    if track:  # Check if track is not None
                        tracks.append({
                            "song_title": track["name"],
                            "artist_name": track["artists"][0]["name"],
                            "album_cover": (
                                track["album"]["images"][0]["url"]
                                if track["album"]["images"]
                                else None
                            )
                        })
                return tracks
            else:
                logger.error("Unsupported Spotify URL: %s", query)
                return None
        except Exception as e:
            logger.error(f"Error processing Spotify query '{query}': {e}")
            return None



    @app_commands.command(name="play", description="Play music from a YouTube or Spotify query.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play a song or a playlist based on a query from YouTube or Spotify."""
        try:
            await interaction.response.defer()
            voice_client = await self.join_voice_channel(interaction)
            if not voice_client:
                return

            is_spotify_url = "open.spotify.com" in query
            tracks_to_add = []

            if is_spotify_url:
                # Process Spotify link
                spotify_data = await self.process_spotify_query(query)
                if not spotify_data:
                    await interaction.followup.send("Could not process the Spotify link.")
                    return
                tracks_to_add = spotify_data
            else:
                # Treat as a regular query
                tracks_to_add.append({
                    "song_title": query,
                    "artist_name": "Unknown Artist",
                    "album_cover": None
                })

            for track in tracks_to_add:
                # Combine title and artist for YouTube search
                search_query = f"{track['song_title']} {track['artist_name']}".strip()
                logger.info(f"Searching YouTube for: {search_query}")

                # Search for YouTube audio
                audio_data = await self.search_youtube_audio(search_query)
                if not audio_data:
                    logger.warning(f"Could not find audio for: {track['song_title']}")
                    continue

                # Add track to queue
                self.queue_manager.add_to_queue(
                    interaction.guild.id,
                    {
                        "title": track["song_title"],
                        "artist": track["artist_name"],
                        "audio_url": audio_data["audio_url"],
                        "thumbnail": track["album_cover"] or audio_data["thumbnail"],
                        "duration": audio_data["duration"],
                    },
                )

                # Play immediately if nothing is currently playing
                if not voice_client.is_playing():
                    await self.skip_song(interaction, voice_client)

            await interaction.followup.send(f"Added {len(tracks_to_add)} track(s) to the queue.")
        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")



async def setup(bot):
    """Set up the PlayCog for the bot."""
    await bot.add_cog(PlayCog(bot))

