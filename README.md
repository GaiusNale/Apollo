# Apollo Music Bot

Apollo is a feature-rich Discord bot designed to play music in voice channels. With commands to join, leave, play, pause, skip, and manage music queues, Apollo offers a smooth and customizable experience for Discord servers.

---

## Features

- **Play Music**: Play music from YouTube directly in your server's voice channel.
- **Queue Management**: Add, skip, and manage songs in a server-specific queue.
- **Playback Controls**: Pause, resume, and stop music playback easily.
- **Error Handling**: Logs errors for better debugging and performance.

---

## Requirements

To set up and run Apollo, ensure you have the following installed:

- **Python 3.10+**
- **pip** (Python package manager)
- **FFmpeg** (for handling audio streams)

---

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd Apollo
   ```

2. **Install Dependencies**:
   Install the required Python libraries using pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   - Create a `.env` file in the project directory.
   - Add the following variables:
     ```
     DISCORD_TOKEN=<your-discord-bot-token>
     SPOTIPY_CLIENT_ID=<your-spotify-client-id>
     SPOTIPY_CLIENT_SECRET=<your-spotify-client-secret>
     ```

4. **Install FFmpeg**:
   - Linux:
     ```bash
     sudo apt update
     sudo apt install ffmpeg
     ```
   - Windows:
     Download from [FFmpeg's official site](https://ffmpeg.org/download.html) and add it to your system's PATH.

5. **Run the Bot**:
   Start the bot using:
   ```bash
   python3 main.py
   ```

---

## Command Overview

### General Commands
| Command  | Description                         |
|----------|-------------------------------------|
| `/join`  | Join the voice channel of the user. |
| `/leave` | Disconnect from the voice channel.  |
| `/ping`  | Check if the bot is online.         |

### Music Commands
| Command        | Description                                 |
|----------------|---------------------------------------------|
| `/play [query]` | Play music from YouTube.                   |
| `/pause`       | Pause the current song.                     |
| `/resume`      | Resume playback.                            |
| `/next`        | Skip to the next song in the queue.         |
| `/queue`       | View the current music queue.               |

Although most of these commands can be handled by the buttons 
---

## File Structure

```plaintext
Apollo/
├── cogs/
│   ├── music_join.py      # Handles the `/join` command.
│   ├── music_leave.py     # Handles the `/leave` command.
│   ├── music_play.py      # Handles `/play` and playback logic.
│   ├── music_next.py      # Handles `/next` to skip songs.
│   ├── music_pause.py     # Handles `/pause` and `/resume`.
│   ├── music_queue.py     # Handles queue management.
│   ├── ping.py            # Handles `/ping`.
├── logs/                  # Stores bot activity logs.
├── modules/               # Optional additional modules.
│   ├── queue_manager.py   # Manages the music queue.
│   ├── music_control_view.py # UI view for music control buttons.
├── main.py                # Entry point of the bot.
├── requirements.txt       # Python dependencies.
├── README.md              # Project documentation (this file).
```

---

## Contributing

If you'd like to contribute to Apollo, feel free to fork the repository and submit a pull request. For major changes, please open an issue first to discuss your proposed changes.

---

## Troubleshooting

- **Bot Not Responding**: Ensure the bot is added to your server and has permission to read and send messages in the target channel.
- **Audio Issues**: Verify that FFmpeg is correctly installed and accessible from your system's PATH.
- **Dependencies**: Ensure all libraries in `requirements.txt` are installed.

---

## License

This project is licensed under the [MIT License](LICENSE).