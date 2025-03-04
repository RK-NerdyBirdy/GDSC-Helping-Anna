# Discord Bot Documentation

## Overview
This Discord bot is built using Python and the `discord.py` library. It provides various functionalities, including:
- Playing audio from YouTube.
- Managing reminders and polls.
- Sending welcome messages.
- Responding to user messages and mentions.

## Prerequisites
Ensure you have the following installed:
- Python 3.8+
- Required dependencies from `requirements.txt`:
  ```
  discord.py
  python-dotenv
  google-generativeai
  yt-dlp
  asyncio
  ```
- An API key for Google Gemini stored in `.env` as `GEMINI`.
- A Discord bot token stored in `.env` as `TOKEN`.

## Installation
1. Clone the repository:
   ```sh
   git clone <repository-url>
   cd <repository-folder>
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add:
   ```
   TOKEN=<your-discord-bot-token>
   GEMINI=<your-google-gemini-api-key>
   ```
4. Run the bot:
   ```sh
   python bot.py
   ```

## Features

### 1. Audio Playback
- Uses `yt-dlp` to download and play YouTube audio.
- Commands:
  - `!play <url>`: Plays audio from a YouTube link.
  - `!stop`: Stops the audio playback.

### 2. Reminders
- Users can set reminders.
- The bot checks and notifies users every 60 seconds.
- Reminders are stored in `reminders.json`.

### 3. Polls
- Users can create polls, and the bot tracks votes using reactions.
- Polls expire at a set time and results are announced.
- Poll data is stored in `polls.json`.

### 4. Welcome Messages
- Sends a customizable welcome message when a new member joins.
- Configurable via `settings.json`.

### 5. AI Responses
- When the bot is mentioned, it uses Google Gemini AI to generate a response.
- Responses are split if they exceed Discord's character limit.

### 6. Summarization
- Users can summarize messages by replying to them with `!summarize` or by providing a message ID.

## Configuration Files
- `reminders.json`: Stores reminder data.
- `polls.json`: Stores poll data.
- `settings.json`: Stores server settings like welcome messages and channels.

## Bot Events
- `on_ready`: Loads data and starts background tasks.
- `on_member_join`: Sends a welcome message.
- `on_message`: Responds when mentioned.
- `on_reaction_add`: Tracks poll votes.
- `on_reaction_remove`: Updates poll votes.

## Contributing
1. Fork the repository.
2. Create a new branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m "Add feature"`.
4. Push to your branch: `git push origin feature-name`.
5. Create a pull request.

## License
This project is licensed under the MIT License.