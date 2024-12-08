from collections import deque

class QueueManager:
    """Utility class to manage song queues for multiple guilds."""
    def __init__(self):
        self.queues = {}  # Dictionary to hold queues for each guild

    def get_queue(self, guild_id):
        """
        Get the queue for a specific guild, or initialize it if it doesn't exist.
        
        Returns:
            deque: The queue for the specified guild.
        """
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    def add_to_queue(self, guild_id, song_data):
        """
        Add a song to the guild's queue.
        
        Args:
            guild_id (int): The ID of the guild.
            song_data (dict): The song's data (e.g., title, URL).
        """
        queue = self.get_queue(guild_id)
        queue.append(song_data)

    def view_queue(self, guild_id):
        """
        Return the list of songs in the queue.
        
        Args:
            guild_id (int): The ID of the guild.
        
        Returns:
            list: A list of songs currently in the queue.
        """
        return list(self.get_queue(guild_id))

    def clear_queue(self, guild_id):
        """
        Clear the guild's queue.
        
        Args:
            guild_id (int): The ID of the guild.
        """
        if guild_id in self.queues:
            self.queues[guild_id].clear()

    def skip_song(self, guild_id):
        """
        Remove and return the next song in the queue.
        
        Args:
            guild_id (int): The ID of the guild.
        
        Returns:
            dict or None: The next song's data, or None if the queue is empty.
        """
        queue = self.get_queue(guild_id)
        return queue.popleft() if queue else None

    def is_queue_available(self, guild_id):
        """
        Check if there are any songs in the queue for a guild.
        
        Args:
            guild_id (int): The ID of the guild.
        
        Returns:
            bool: True if the queue has songs, False otherwise.
        """
        return len(self.get_queue(guild_id)) > 0

    def pop_from_queue(self, guild_id):
        """
        Alias for skip_song, providing consistency with cog calls.
        
        Args:
            guild_id (int): The ID of the guild.
        
        Returns:
            dict or None: The next song's data, or None if the queue is empty.
        """
        return self.skip_song(guild_id)