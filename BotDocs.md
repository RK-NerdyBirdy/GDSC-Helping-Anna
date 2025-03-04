**Helping Anna - Command List**

    General Commands:
    - `!help` - Displays this help message.
    - `!summarize [message_id]` - Summarizes a message or text. Reply to a message or provide a message ID.
    - `!remind <time> <message>` - Sets a reminder. Use formats like `1h`, `30m`, `2023-12-31 23:59`.
    - `!reminders` - Lists all your active reminders.
    - `!delreminder <index>` - Deletes a reminder by its index (use `!reminders` to see indices).
    - `!delallreminders` - Deletes all your reminders.

    **Poll Commands:**
    - `!poll "Question?" "Option 1" "Option 2" [more options] [duration]` - Creates a poll. Example: `!poll "Best fruit?" "Apple" "Banana" "Orange" 1h`.

    **Welcome Message Commands:**
    - `!setwelcome <message>` - Sets a custom welcome message for new members. Use placeholders like `{user}`, `{username}`, and `{server}`.

    **Music Commands:**
    - `!play <song_name_or_url>` - Plays a song from YouTube or adds it to the queue.
    - `!skip` - Skips the current song and plays the next one in the queue.
    - `!queue` - Displays the current music queue.
    - `!stop` - Stops the music and clears the queue.
    - `!join` - Joins your voice channel.
    - `!leave` - Leaves the voice channel.

    **Admin Commands:**
    - `!setwelcome <message>` - (Admin only) Sets a custom welcome message for new members.

    **Examples:**
    1. **Set a Reminder:**
       ```
       !remind 1h Do your homework!
       !remind 2023-12-31 23:59 New Year's Eve!
       ```

    2. **Create a Poll:**
       ```
       !poll "Best programming language?" "Python" "JavaScript" "Java" 30m
       ```

    3. **Play Music:**
       ```
       !play Never Gonna Give You Up
       !play https://www.youtube.com/watch?v=dQw4w9WgXcQ
       ```

    4. **Summarize a Message:**
       ```
       !summarize 123456789012345678 (message ID)
       ```

    5. **Set a Welcome Message:**
       ```
       !setwelcome Welcome to {server}, {user}! Enjoy your stay.
       ```

    **Notes:**
    - Use `!help <command>` for more details on a specific command.
    - Make sure the bot has the necessary permissions to join voice channels and send messages.
    - For music commands, ensure FFmpeg and PyNaCl are installed.
    