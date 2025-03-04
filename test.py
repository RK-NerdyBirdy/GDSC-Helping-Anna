import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from google import genai
import re
load_dotenv()
# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.reactions = True

bot = commands.Bot(command_prefix='$', intents=intents)
ggclient = genai.Client(api_key=os.getenv("GEMNI"))


token = os.getenv("TOKEN")
@bot.event
async def on_ready():
    print(f"Helping Anna at your service!!! and logged in as {bot.user}")
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
     # Process commands first
    await bot.process_commands(message)
    
    # Check if the bot is mentioned
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        # Remove the mention from the message
        content = re.sub(r'<@!?(\d+)>', '', message.content).strip()
        
        if not content:
            await message.reply("How can I help you today?")
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
                await message.reply("Sorry, I encountered an error processing your request. Please try again later.")
    
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


bot.run(token)  
