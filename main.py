from typing import Optional
import discord
from discord.ext import commands
import discord.ui
import os
import aiohttp
import io
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("API_KEY")
Developer = int(os.getenv("DEVElOPER"))
Test_guild_id = int(os.getenv("TEST_GUILD"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.tree.command(name="generate_qr", description="Generates a QR code with your user ID")
async def generate_qr(interaction: discord.Interaction):
    await interaction.response.defer()  # 処理に時間がかかる可能性があるため、応答を遅延させます

    user_id = interaction.user.id  # ユーザーIDを取得

    async with aiohttp.ClientSession() as session:
        async with session.post(f'http://150.59.20.116:8000/qr_gen/{user_id}') as response:
            if response.status == 200:
                img_data = await response.read()
                file = discord.File(io.BytesIO(img_data), filename="qr_code.png")
                await interaction.followup.send(f"Here's your QR code for user ID {user_id}:", file=file)
            else:
                await interaction.followup.send("Failed to generate QR code.")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

bot.run(TOKEN)