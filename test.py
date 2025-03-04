import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from google import genai
import re
import json
import datetime
from typing import List, Dict, Any, Optional, Union
import wavelink

load_dotenv()
# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents)
ggclient = genai.Client(api_key=os.getenv("GEMNI"))

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
    # Connect to Wavelink node for music
    try:
        node = wavelink.Node(uri=os.getenv('LAVALINK_URI', 'http://localhost:2333'), 
                            password=os.getenv('LAVALINK_PASSWORD', 'youshallnotpass'))
        await wavelink.Pool.connect(client=bot, nodes=[node])
        print("Connected to Lavalink node!")
    except Exception as e:
        print(f"Failed to connect to Lavalink: {e}")
        print("Music features may not work. Make sure Lavalink is running.")
    
    # Sync commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

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
    #To list out all the reminders 
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
    """Set a custom welcome message for new members."""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in settings['servers']:
        settings['servers'][guild_id] = {}
    
    settings['servers'][guild_id]['welcome_channel'] = ctx.channel.id
    settings['servers'][guild_id]['welcome_message'] = message
    
    save_settings()
    
    await ctx.reply(f"Welcome message set to: \"{message}\"")

bot.run(token) 