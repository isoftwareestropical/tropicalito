import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Configura el bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Token del bot
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("⚠️ TOKEN not found. Make sure to set it as an environment variable.")

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands with Discord.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

async def main():
    async with bot:
        # Load cogs dynamically
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                await bot.load_extension(f"cogs.{filename[:-3]}")
        await bot.start(TOKEN)

# Run the bot
asyncio.run(main())