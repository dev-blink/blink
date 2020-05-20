import discord
from discord.ext import commands
import blink
import datetime
import asyncpg
import logging
import asyncio
import aiohttp
import os


logger=logging.getLogger('discord')
logger.setLevel(0)
handler=logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
STARTUPTIME=datetime.datetime.utcnow()


def get_prefix(bot, message):
    prefixes=[';','b;','B;']

    if not message.guild:
        return '?'

    if bot.user.name == "blink beta":
        prefixes= ['beta;']

    if message.guild.id in [336642139381301249,264445053596991498,265828729970753537] and not bot.user.name == "blink beta":
        prefixes=["b;","B;"]

    return commands.when_mentioned_or(*prefixes)(bot, message)


print("Initializing AutoShardedBot and global vars.")
loading_extensions=["cogs.help","cogs.member","cogs.dev","cogs.info","cogs.error","cogs.mod","cogs.server","cogs.fun","cogs.roles","cogs.advancedinfo","cogs.stats","cogs.media","cogs.DBL","cogs.logging","cogs.sql","cogs.nsfw","cogs.music"]
loading_extensions.append("jishaku")
SHARD_COUNT = 1
SHARD_IDS = [0]
INIT_SHARDS = []
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "False"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"

bot=commands.AutoShardedBot(command_prefix=get_prefix, description="Blink!",activity=discord.Game(name="Bot is starting, please wait."),status=discord.Status.dnd,help_command=None,shard_count=SHARD_COUNT,shard_ids=SHARD_IDS,case_insensitive=True)
bot.load_extension("cogs.PRELOAD")
print("LOADED PRELOAD ERROR HANDLER")
bot.startingcogs=loading_extensions
bot.colour=0xf5a6b9
loadexceptions=""
bot.INITIALIZED=False


def load_extensions():
    print("Initializing Extensions")
    for extension in loading_extensions:
        try:
            bot.load_extension(extension)
            print("Loaded: " + extension)
        except Exception as e:
            print("unable to load: " + extension + " Exception was raised: " + str(e))
            global loadexceptions
            loadexceptions=loadexceptions + f"Unable to load: {extension} Exception was raised: {e}\n"
    print("Finished loading cogs\n")


@bot.event
async def on_ready():
    if bot.INITIALIZED:
        return
    while len(INIT_SHARDS) != len(SHARD_IDS):
        await asyncio.sleep(0.1)
    asyncio.create_task(__init())
    bot.INITIALIZED=True


@bot.event
async def on_shard_ready(id):
    global INIT_SHARDS
    if id in INIT_SHARDS:
        return
    print(f"SHARD READY {id}")
    INIT_SHARDS.append(id)


async def __init():
    print("\nINIT DATABASE")
    cn={"user":"blink","password":"local","database":"main","host":"localhost"}
    bot.DB=await asyncpg.create_pool(**cn)
    print("DATABASE INITIALIZED")
    print("\nINIT HTTP SESSION")
    bot.session = aiohttp.ClientSession()
    print("HTTP INITIALIZED\n")
    print(f'\nLogged in as: {bot.user.name} - {bot.user.id}\nDiscord.py Version: {discord.__version__}')
    bot.statsserver=bot.get_guild(blink.Config.statsserver())
    if not bot.user.name == "blink beta":
        game=discord.Streaming(name='; (b;)', url='https://www.twitch.tv/#')
    else:
        game=discord.Game(name="beta bot")
    await bot.change_presence(status=discord.Status.online,activity=game)
    bot.boottime=STARTUPTIME
    bot.unload_extension("cogs.PRELOAD")
    load_extensions()
    print(f'Successfully logged in and booted.')
    print("Server Count: " + str(len(bot.guilds)) + "\nShard Count: " + str(bot.shard_count))
    boottime=datetime.datetime.utcnow() - STARTUPTIME
    members=len(list(bot.get_all_members()))
    print(f"STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)")
    startupid=blink.Config.startup(bot.user.name)
    if not loadexceptions == "":
        x=f"\n***ERRORS OCCURED ON STARTUP:***\n{loadexceptions}"
    else:
        x=""
    boot=f"{'-' * 79}\n**BOT STARTUP:** {bot.user} started at {datetime.datetime.utcnow().isoformat()}\n```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)\nGUILDS:{len(bot.guilds)}\nSHARDS:{bot.shard_count}```\n`d.py version: {discord.__version__}`{x}"
    if startupid:
        await bot.get_channel(startupid).send(boot)
    bot.bootlog=boot


bot.run(open("TOKEN","r").read(), bot=True, reconnect=True)
