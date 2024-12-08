import discord
import logging

logger = logging.getLogger(__name__)

class MusicControlView(discord.ui.View):
    """UI view for controlling music playback with buttons."""
    def __init__(self, cog, voice_client):
        super().__init__(timeout=600)
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
