import sys

#sys.path.append("./bot")
sys.path.append("./core")

import discord
from discord import Intents
from discord.ext import commands

import os
from dotenv import load_dotenv

load_dotenv()

TEST_SERVER = 1444541318775701620
guild_ids = [TEST_SERVER]

intents = Intents().all()

client = commands.Bot(command_prefix="!", intents=intents)


@client.event
async def setup_hook():

    import bot.client as botmod

    await client.add_cog(botmod.Chess(client))
 
    for g in guild_ids:
        obj = discord.Object(id=g)
        client.tree.copy_global_to(guild=obj)
        await client.tree.sync(guild=obj)


@client.event
async def on_ready():
    print(f"logged in as: {client.user}")


client.run(os.getenv("token"))
