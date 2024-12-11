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
API_HOME = os.getenv("API_HOME")
Developer = int(os.getenv("DEVElOPER"))
Test_guild_id = int(os.getenv("TEST_GUILD"))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.tree.command(name="generate_qr", description="Generates a QR code with your user ID and sends it via DM")
@discord.app_commands.describe(name="Your name to include in the QR code")
async def generate_qr(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)  # 処理に時間がかかる可能性があるため、応答を遅延させる

    user_id = interaction.user.id  # ユーザーIDを取得

    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_HOME}/{user_id}?name={name}') as response:
            if response.status == 200:
                img_data = await response.read()
                file = discord.File(io.BytesIO(img_data), filename="qr_code.png")
                
                try:
                    # DMで送信
                    await interaction.user.send(f"Here's your QR code for user ID {user_id}:", file=file)
                    await interaction.followup.send("QR code has been sent to your DM.", ephemeral=True)
                except discord.errors.Forbidden:
                    # DMを送信できない場合（ユーザーがDMを許可していない場合など）
                    await interaction.followup.send("I couldn't send you a DM. Please check your privacy settings and try again.", ephemeral=True)
                    # await interaction.response.send_message("I couldn't send you a DM. Please check your privacy settings and try again.", ephemeral=True)
            else:
                await interaction.followup.send("Failed to generate QR code.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

bot.run(TOKEN)