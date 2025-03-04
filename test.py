import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from google import genai
import re
import json
import datetime
from typing import List, Dict, Any, Optional, Union
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


def save_reminders():
    """Save reminders to file."""
    with open(Reminders_file, 'w') as f:
        json.dump(reminders, f, indent=2)
    
def load_data():
    global reminders
    if os.path.exists(Reminders_file):
        with open(Reminders_file, 'r') as f:
            reminders = json.load(f)
    else:
        reminders=[]
        save_reminders()

    




token = os.getenv("TOKEN")
@bot.event
async def on_ready():
    print(f"Helping Anna at your service!!! and logged in as {bot.user}")
    load_data()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

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
bot.run(token)  
