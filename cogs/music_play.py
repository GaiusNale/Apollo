import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl
import logging

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


class MusicControlView(discord.ui.View):
    def __init__(self, cog, voice_client):
        super().__init__(timeout=None)
        self.cog = cog
        self.voice_client = voice_client
        self.is_paused = False  # Start with playback not paused

    # Pause/Resume button
    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏸️", custom_id="pause_resume")
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle between pausing and resuming the music."""
        if not self.voice_client.is_playing() and not self.is_paused:
            await interaction.response.send_message("No music is currently playing.", ephemeral=True)
            return

        if self.is_paused:
            self.voice_client.resume()
            self.is_paused = False
            button.emoji = "⏸️"  # Change to pause icon
            await interaction.response.edit_message(content="Music resumed.", view=self)
        else:
            self.voice_client.pause()
            self.is_paused = True
            button.emoji = "▶️"  # Change to play icon
            await interaction.response.edit_message(content="Music paused.", view=self)

    # Stop button
    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏹️", custom_id="stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop playback."""
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            await interaction.response.send_message("Music stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("No music is playing currently.", ephemeral=True)


class PlayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def search_youtube_audio(self, query):
        """Search YouTube and get the audio URL and title."""
        try:
            info = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {
                "audio_url": info['url'],
                "title": info['title'],
                "duration": info['duration'],
                "thumbnail": info.get('thumbnail', None),
                "uploader": info.get('uploader', 'Unknown')
            }
        except Exception as e:
            logger.error(f"Error extracting audio stream: {e}")
            return None

    async def join_voice_channel(self, interaction: discord.Interaction):
        """Automatically join the voice channel of the user."""
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("You need to be in a voice channel for me to join.")
            logger.warning(f"User {interaction.user} is not in a voice channel.")
            return None

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.channel == voice_channel:
            # Already connected to the correct channel
            return voice_client

        if voice_client:
            await voice_client.disconnect()
            logger.info(f"Disconnected from the previous channel in guild {interaction.guild.id}.")

        try:
            voice_client = await voice_channel.connect()
            logger.info(f"Joined voice channel: {voice_channel.name} in guild {interaction.guild.id}.")
            return voice_client
        except Exception as e:
            await interaction.followup.send("Failed to join the voice channel.")
            logger.error(f"Failed to join voice channel: {e}")
            return None

    @app_commands.command(name="play", description="Play music from a YouTube search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play music in the user's current voice channel."""
        try:
            await interaction.response.defer()

            # Ensure the bot is in a voice channel
            voice_client = await self.join_voice_channel(interaction)
            if not voice_client:
                return

            # Search for the song
            audio_data = await self.search_youtube_audio(query)
            if not audio_data:
                await interaction.followup.send("Could not find the song.")
                return

            # Stop current playback if any
            if voice_client.is_playing():
                voice_client.stop()

            # Play the requested song
            voice_client.play(
                discord.FFmpegPCMAudio(audio_data['audio_url'], **ffmpeg_options),
                after=lambda e: logger.info(f"Finished playing: {audio_data['title']}") if not e else logger.error(f"Error during playback: {e}")
            )

            # Create an embed for the song
            embed = discord.Embed(
                title="Now Playing",
                description=f"[{audio_data['title']}]({audio_data['audio_url']})",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=audio_data['thumbnail'] if audio_data['thumbnail'] else "")
            embed.add_field(name="Artist", value=audio_data['uploader'], inline=True)
            embed.add_field(name="Duration", value=f"{audio_data['duration'] // 60}:{audio_data['duration'] % 60:02}", inline=True)

            # Add the control view
            view = MusicControlView(self, voice_client)
            await interaction.followup.send(embed=embed, view=view)
            logger.info(f"Now playing: {audio_data['title']}")
        except Exception as e:
            await interaction.followup.send("An error occurred while trying to play the song.")
            logger.error(f"Failed to play song: {e}")


async def setup(bot):
    await bot.add_cog(PlayCog(bot))
