import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from google import genai
import re
import json
import datetime
from typing import List, Dict, Any, Optional, Union
import yt_dlp as youtube_dl
import asyncio
load_dotenv()
# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
ggclient = genai.Client(api_key=os.getenv("GEMNI"))

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # Bind to IPv4 since IPv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Queue system
queues = {}

Reminders_file = "reminders.json"
Polls_file = "polls.json"

Settings_file = 'settings.json'
reminders =[]
polls ={}
settings = {"servers": {}}
def parse_time(time_str: str) -> Optional[datetime.datetime]:
    """Parse time string into datetime object."""
    now = datetime.datetime.now()
    
    # Check if it's a relative time (e.g., 1h, 30m)
    rel_time_match = re.match(r'^(\d+)([mhdw])$', time_str)
    if rel_time_match:
        amount, unit = rel_time_match.groups()
        amount = int(amount)
        
        if unit == 'm':
            return now + datetime.timedelta(minutes=amount)
        elif unit == 'h':
            return now + datetime.timedelta(hours=amount)
        elif unit == 'd':
            return now + datetime.timedelta(days=amount)
        elif unit == 'w':
            return now + datetime.timedelta(weeks=amount)
    
    # Check if it's an absolute date (YYYY-MM-DD HH:MM)
    try:
        return datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    except ValueError:
        pass
    
    return None

def save_settings():
    """Save settings to file."""
    with open(Settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
def save_reminders():
    """Save reminders to file."""
    with open(Reminders_file, 'w') as f:
        json.dump(reminders, f, indent=2)
def save_polls():
    """Save polls to file."""
    with open(Polls_file, 'w') as f:
        json.dump(polls, f, indent=2)   
def load_data():
    global reminders,polls
    if os.path.exists(Reminders_file):
        with open(Reminders_file, 'r') as f:
            reminders = json.load(f)
    else:
        reminders=[]
        save_reminders()
    if os.path.exists(Polls_file):
        with open(Polls_file, 'r') as f:
            polls = json.load(f)
    else:
        polls = {}
        save_polls()
    if os.path.exists(Settings_file):
        with open(Settings_file, 'r') as f:
            settings = json.load(f)
    else:
        settings = {"servers": {}}
        save_settings()

# Tasks
@tasks.loop(seconds=60)
async def check_reminders():
    
    global reminders
    now = datetime.datetime.now()
    due_reminders = []
    remaining_reminders = []
    
    for reminder in reminders:
        reminder_time = datetime.datetime.fromisoformat(reminder['time'])
        if reminder_time <= now:
            due_reminders.append(reminder)
        else:
            remaining_reminders.append(reminder)
    
    reminders = remaining_reminders
    save_reminders()
    
    for reminder in due_reminders:
        try:
            channel = bot.get_channel(reminder['channel_id'])
            if channel:
                await channel.send(f"<@{reminder['user_id']}>, here's your reminder: {reminder['content']}")
            else:
                user = await bot.fetch_user(reminder['user_id'])
                await user.send(f"Here's your reminder: {reminder['content']}")
        except Exception as e:
            print(f"Error sending reminder: {e}")  

@tasks.loop(seconds=60)
async def check_polls():
    
    now = datetime.datetime.now().isoformat()
    expired_poll_ids = []
    
    for poll_id, poll in polls.items():
        if poll['end_time'] <= now:
            expired_poll_ids.append(poll_id)
            try:
                channel = bot.get_channel(poll['channel_id'])
                if channel:
                    # Tally results
                    results = []
                    for option in poll['options']:
                        results.append({
                            'text': option['text'],
                            'votes': len(option['votes'])
                        })
                    
                    results.sort(key=lambda x: x['votes'], reverse=True)
                    
                    result_message = f"**Poll Results: {poll['question']}**\n\n"
                    for i, result in enumerate(results):
                        result_message += f"{i+1}. {result['text']}: {result['votes']} votes\n"
                    
                    await channel.send(result_message)
            except Exception as e:
                print(f"Error ending poll: {e}")
    
    # Remove expired polls
    for poll_id in expired_poll_ids:
        polls.pop(poll_id, None)
    
    if expired_poll_ids:
        save_polls()




token = os.getenv("TOKEN")
@bot.event
async def on_ready():
    print(f"Helping Anna at your service!!! and logged in as {bot.user}")
    load_data()
   
    # Start background tasks
    check_reminders.start()
    check_polls.start()
    

@bot.event
async def on_member_join(member):
    """Called when a member joins the server."""
    guild_id = str(member.guild.id)
    
    if guild_id in settings['servers'] and 'welcome_channel' in settings['servers'][guild_id]:
        channel_id = settings['servers'][guild_id]['welcome_channel']
        welcome_message = settings['servers'][guild_id].get('welcome_message', 'Welcome to the server, {user}!')
        
        # Replace placeholders
        welcome_message = welcome_message.replace('{user}', member.mention)
        welcome_message = welcome_message.replace('{username}', member.name)
        welcome_message = welcome_message.replace('{server}', member.guild.name)
        
        channel = member.guild.get_channel(channel_id)
        if channel:
            await channel.send(f"{member.mention}"+welcome_message)  

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
     
    await bot.process_commands(message)
    
    
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        # Remove the mention from the message
        content = re.sub(r'<@!?(\d+)>', '', message.content).strip()
        
        if not content:
            await message.reply("What happend Maa?")
            return
        
        # Show typing indicator
        async with message.channel.typing():
            try:
                # Generate response using Gemini
                response = ggclient.models.generate_content(model="gemini-2.0-flash",contents=content)
                response_text = response.text
                
                # Split long responses
                if len(response_text) <= 2000:
                    await message.reply(response_text)
                else:
                    # Split into chunks of ~1900 characters
                    chunks = [response_text[i:i+1900] for i in range(0, len(response_text), 1900)]
                    for chunk in chunks:
                        await message.reply(chunk)
            except Exception as e:
                print(f"Error generating response: {e}")
                await message.reply("Sorry, I encountered an error processing your request maa. Please try again later.")


@bot.event
async def on_reaction_add(reaction, user):
    """Called when a reaction is added to a message."""
    if user.bot:
        return
    
    # Check if this is a poll
    message_id = str(reaction.message.id)
    for poll_id, poll in polls.items():
        if poll['message_id'] == message_id:
            emoji = str(reaction.emoji)
            
            # Find the option with this emoji
            for option in poll['options']:
                if option['emoji'] == emoji:
                    # Remove other votes from this user
                    for opt in poll['options']:
                        if user.id in opt['votes']:
                            opt['votes'].remove(user.id)
                    
                    # Add user's vote
                    if user.id not in option['votes']:
                        option['votes'].append(user.id)
                    print(f"vote added to the poll {message_id} by {user.id}")
                    save_polls()
                    break
            
            break

@bot.event
async def on_reaction_remove(reaction, user):
    """Called when a reaction is removed from a message."""
    if user.bot:
        return
    
    # Check if this is a poll
    message_id = str(reaction.message.id)
    for poll_id, poll in polls.items():
        if poll['message_id'] == message_id:
            emoji = str(reaction.emoji)
            
            # Find the option with this emoji
            for option in poll['options']:
                if option['emoji'] == emoji and user.id in option['votes']:
                    option['votes'].remove(user.id)
                    print(f"vote deleted from the poll {message_id} by {user.id}")
                    save_polls()
                    break
            
            break

@bot.command(name='summarize')
async def summarize(ctx, message_id=None):
    """
    Summarize a message or provided text.
    Usage: !summarize <message_id> or reply to a message with !summarize
    """
    text_to_summarize = None
    
    if message_id:
       
        try:
            target_message = await ctx.channel.fetch_message(int(message_id))
            text_to_summarize = target_message.content
        except:
            text_to_summarize = " ".join(ctx.message.content.split()[1:])
    elif ctx.message.reference:
        # If replying to a message
        try:
            replied_to = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            text_to_summarize = replied_to.content
        except:
            await ctx.reply("Could not retrieve the message to summarize.")
            return
    else:
        await ctx.reply("Please either reply to a message to summarize or provide text/message ID.")
        return
    
    if not text_to_summarize or len(text_to_summarize) < 100:
        await ctx.reply("The text is too short to summarize. Please provide a longer text.")
        return
    
    async with ctx.typing():
        try:
            prompt = f"Summarize the following text in a concise way: {text_to_summarize}"
            
            response = ggclient.models.generate_content(model="gemini-2.0-flash",contents=prompt)
            summary = response.text
            
            await ctx.reply(f"**Summary:** {summary}")
        except Exception as e:
            print(f"Error generating summary: {e}")
            await ctx.reply("There was an error generating the summary. Please try again later.")

@bot.command(name="remind")
async def remind(ctx,time_arg, *, content=None):
    """
    Set a reminder.
    Usage: !remind <time> <message>
    Time format: 1h, 30m, 1d, 1w, or YYYY-MM-DD HH:MM
    Example: !remind 1h Do your homework
    """
    if not content:
        parts = time_arg.split()
        if len(parts)>=2 and re.match(r'^\d{4}-\d{2}-\d{2}$', parts[0]):
            datestr = parts[0]
            timestr = parts[1]
            if re.match(r'^\d{2}:\d{2}$', timestr):
                time_arg = f"{datestr} {timestr}"
                content = ' '.join(parts[2:])
            else:
                await ctx.reply("For absolute dates, please use the format RAAAA: `!remind YYYY-MM-DD HH:MM <reminder message>`")
                return
        else:
            await ctx.reply("Pls use the format RAAA: `!remind <time> <reminder message>`")
            return
        # Parse time
    reminder_time = parse_time(time_arg)
    
    if not reminder_time:
        await ctx.reply("Invalid time format. Use `!remind 1h <message>` or `!remind 2023-12-31 23:59 <message>`")
        return
    
    if reminder_time <= datetime.datetime.now():
        await ctx.reply("The reminder time must be in the future.")
        return
    # Creating reminder in format id, userid, channel id, content and time in iso format YYYY-MM-DD
    reminder = {
        'id': str(int(datetime.datetime.now().timestamp())),
        'user_id': ctx.author.id,
        'channel_id': ctx.channel.id,
        'content': content,
        'time': reminder_time.isoformat(),
        'created_at': datetime.datetime.now().isoformat()
    }
    
    reminders.append(reminder)
    save_reminders()
    
    await ctx.reply(f"Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M')}: {content} . sit back and Relax maa")
 


@bot.command(name="reminders")
async def reminders(ctx):
    """
    List all your active reminders.
    Usage: !reminders
    """
    usr_reminders = [i for i in reminders if i["user_id"] == ctx.author.id] #list comprehension technique
    usr_reminders.sort(key=lambda x: x["time"])

    if not usr_reminders:
        await ctx.reply("You have no active reminders maa. use !Remind to create one.")
        return
    
    response = "**Your reminders:**\n\n"
    
    for i, reminder in enumerate(usr_reminders):
        reminder_time = datetime.datetime.fromisoformat(reminder['time'])
        timestamp = int(reminder_time.timestamp())
        response += f"{i+1}. <t:{timestamp}:F> - {reminder['content']}\n"
    
    await ctx.reply(response)

@bot.command(name="delreminder")
async def delreminder(ctx,index: int):
    """
    Delete a specific reminder by its index.
    Usage: !delreminder <index>
    Example: !delreminder 1
    """
    if index <= 0:
        await ctx.reply("Please specify a valid reminder number.")
        return
    
    usr_reminders = [r for r in reminders if r['user_id'] == ctx.author.id]
    usr_reminders.sort(key=lambda x: x['time'])
    
    if not usr_reminders or index > len(usr_reminders):
        await ctx.reply("Invalid reminder number. Use `!reminders` to see your list of reminders.")
        return
    
    reminder_to_delete = usr_reminders[index-1]
    reminders.remove(reminder_to_delete)
    save_reminders()
    
    await ctx.reply(f"Deleted reminder: {reminder_to_delete['content']}")

@bot.command(name="delallreminders")
async def delallreminders(ctx):
    """
    Delete all your reminders.
    Usage: !delallreminders
    """
    
    usr_reminders = [r for r in reminders if r['user_id'] == ctx.author.id]
    usr_reminders.sort(key=lambda x: x['time'])
    
    if not usr_reminders:
        await ctx.reply("Invalid reminders. Use `!reminders` to see your list of reminders.")
        return
    for i in usr_reminders:
        reminders.remove(i)
    save_reminders()
    
    await ctx.reply(f"All reminders deleted")

@bot.command(name='poll')
async def create_poll(ctx, *, args=None):
    """
    Create a poll.
    Usage: !poll "Question?" "Option 1" "Option 2" "Option 3" 30m
    """
    if not args:
        await ctx.reply('Please use the format: `!poll "Question?" "Option 1" "Option 2" [more options] [duration]`')
        return
    
    # Parse the poll command
    try:
        # Extract all quoted strings
        matches = re.findall(r'"([^"]+)"', args)
        
        if len(matches) < 3:  # Need at least a question and 2 options
            await ctx.reply('Please provide a question and at least 2 options in quotes.')
            return
        
        question = matches[0]
        options = matches[1:]
        
        if len(options) > 10:
            await ctx.reply('Polls can have a maximum of 10 options.')
            return
        
        # Check for duration at the end
        duration_match = re.search(r'\s+(\d+[mhdw])$', args)
        if duration_match:
            duration_str = duration_match.group(1)
            end_time = parse_time(duration_str)
        else:
            # Default: 1 day
            end_time = datetime.datetime.now() + datetime.timedelta(days=1)
        
        # Create poll message
        emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        poll_message = f"**Poll: {question}**\n\n"
        
        options_data = []
        for i, option in enumerate(options):
            emoji = emoji_list[i]
            poll_message += f"{emoji} {option}\n"
            options_data.append({
                'text': option,
                'emoji': emoji,
                'votes': []
            })
        
        poll_message += f"\nPoll ends at: {end_time.strftime('%Y-%m-%d %H:%M')}"
        
        # Send poll message
        sent_message = await ctx.send(poll_message)
        
        # Add reactions
        for i in range(len(options)):
            await sent_message.add_reaction(emoji_list[i])
        
        # Store poll data
        poll_id = str(int(datetime.datetime.now().timestamp()))
        polls[poll_id] = {
            'id': poll_id,
            'message_id': str(sent_message.id),
            'channel_id': ctx.channel.id,
            'author_id': ctx.author.id,
            'question': question,
            'options': options_data,
            'end_time': end_time.isoformat()
        }
        
        save_polls()
    
    except Exception as e:
        print(f"Error creating poll: {e}")
        await ctx.reply('Error creating poll. Please use the format: `!poll "Question?" "Option 1" "Option 2" [more options] [duration]`')

@bot.command(name='setwelcome')
@commands.has_permissions(administrator=True)
async def set_welcome(ctx, *, message):
    """
    Set a custom welcome message for new members.
    Usage: !setwelcome <message>
    Example: !setwelcome Welcome to the server, {user}!
    """
    guild_id = str(ctx.guild.id)
    
    if guild_id not in settings['servers']:
        settings['servers'][guild_id] = {}
    
    settings['servers'][guild_id]['welcome_channel'] = ctx.channel.id
    settings['servers'][guild_id]['welcome_message'] = message
    
    save_settings()
    
    await ctx.reply(f"Welcome message set to: \"{message}\"")




def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

async def play_next(ctx):
    
    queue = get_queue(ctx.guild.id)
    if queue:
        next_track = queue.pop(0)
        player = await YTDLSource.from_url(next_track, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'Now playing: **{player.title}**')
    else:
        await ctx.send("Queue is empty. Add more songs with `!play`.")

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query: str = None):
    """
    Play a song from YouTube or add it to the queue.
    Usage: !play <song name or URL>
    Example: !play https://www.youtube.com/watch?v=dQw4w9WgXcQ
    """
    if not query:
        await ctx.send("Please provide a song name or URL.")
        return

    if not ctx.author.voice:
        await ctx.reply("You need to be in a voice channel to play music!")
        return

    # Ensure the bot is connected
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
            queue = get_queue(ctx.guild.id)

            if ctx.voice_client.is_playing():
                queue.append(query)
                await ctx.send(f"Added to queue: **{player.title}**")
            else:
                ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                await ctx.send(f'Now playing: **{player.title}**')
        except Exception as e:
            await ctx.send(f"Error: {e}")

@bot.command(name='skip')
async def skip(ctx):
    """
    Skip the current song.
    Usage: !skip
    """
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped the current song.")
        await play_next(ctx)
    else:
        await ctx.send("Nothing is playing right now.")

@bot.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    """
    Show the current music queue.
    Usage: !queue
    """
    queue = get_queue(ctx.guild.id)
    if not queue:
        await ctx.send("The queue is empty.")
        return

    queue_message = "**Current Queue:**\n"
    for i, track in enumerate(queue, 1):
        queue_message += f"{i}. {track}\n"

    await ctx.send(queue_message)

@bot.command(name='stop')
async def stop(ctx):
    """
    Stop the music and clear the queue.
    Usage: !stop
    """
    if ctx.voice_client:
        ctx.voice_client.stop()
        queues[ctx.guild.id] = []  # Clear the queue
        await ctx.send("Stopped the music and cleared the queue.")

@bot.command(name='join')
async def join(ctx):
    """
    Join the voice channel.
    Usage: !join
    """
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    await ctx.author.voice.channel.connect()

@bot.command(name='leave')
async def leave(ctx):
    """
    Leave the voice channel.
    Usage: !leave
    """
    if ctx.voice_client:
        queues[ctx.guild.id] = []  # Clear the queue
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")

bot.run(token) 