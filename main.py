import sys

sys.path.append("./bot")
sys.path.append("./core")

import discord
from discord import Intents
from discord.ext import commands

import os
from dotenv import load_dotenv

load_dotenv()

PSG = 1420441126950932620
BT = 1444541318775701620
guild_ids = [BT]
# guild_ids = [1444541318775701620]

intents = Intents().all()

client = commands.Bot(command_prefix="!", intents=intents)


@client.event
async def setup_hook():
    """
    import rem
    import anonmgs
    import choose
    import knockoff_ypt
    """
    import bot.main

    await client.add_cog(bot.main.Chess(client))
    """
    await client.add_cog(rem.ReminderMod(client))
    await client.add_cog(anonmgs.AnonMessages(client))
    await client.add_cog(choose.Choose(client))
    await client.add_cog(knockoff_ypt.StudyTimer(client))
    """
    for g in guild_ids:
        obj = discord.Object(id=g)
        client.tree.copy_global_to(guild=obj)
        await client.tree.sync(guild=obj)


@client.event
async def on_ready():
    print(f"logged in as: {client.user}")


client.run(os.getenv("token"))
