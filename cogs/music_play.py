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
ffmpeg_options = {
    'options': '-vn',
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
    spotify = Spotify(client_credentials_manager=client_credentials_manager)
    return spotify

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

class MusicControlView(discord.ui.View):
    def __init__(self, cog, voice_client):
        super().__init__(timeout=None)
        self.cog = cog
        self.voice_client = voice_client
        self.is_paused = False

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏸️", custom_id="pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            await interaction.response.send_message("Music stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is playing currently.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.voice_client.is_playing():
            await interaction.response.send_message("No music is currently playing to skip.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog.skip_song(interaction, self.voice_client)


class PlayCog(commands.Cog):
    def __init__(self, bot, queue_manager):
        self.bot = bot
        self.spotify = get_spotify_client()
        self.queue_manager = queue_manager

    async def join_voice_channel(self, interaction: discord.Interaction):
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
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {
                "audio_url": info['formats'][0]['url'],
                "title": info['title'],
                "duration": info['duration'],
                "thumbnail": info.get('thumbnails', [{}])[-1].get('url', None)
            }
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return None

    @app_commands.command(name="play", description="Play music from a YouTube search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        try:
            await interaction.response.defer()
            voice_client = await self.join_voice_channel(interaction)
            if not voice_client:
                return

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

            if not voice_client.is_playing():
                await self.skip_song(interaction, voice_client)

            await interaction.followup.send("Song added to the queue.")
        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")

async def setup(bot, queue_manager):
    await bot.add_cog(PlayCog(bot, queue_manager))