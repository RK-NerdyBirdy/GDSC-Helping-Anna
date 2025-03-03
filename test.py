import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv

load_dotenv()
# Bot configuration
intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(command_prefix='!', intents=intents)


token = os.getenv("TOKEN")
@bot.event
async def on_ready():
    print(f"Helping Anna at your service!!! and logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content.startswith('$Hello'):
        await message.channel.send("Hello")

bot.run(token)
