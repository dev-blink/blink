import discord
from discord.ext import commands, tasks
import blink
import datetime
import asyncpg
import logging
import asyncio
import aiohttp
import os


SHARD_COUNT = 3
SHARD_IDS = [0,1,2]
print(f"Starting with {SHARD_COUNT} shards ({SHARD_IDS[0]}-{SHARD_IDS[-1]})\n")

beta=False
logger=logging.getLogger('discord')
logger.setLevel(0)
handler=logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
STARTUPTIME=datetime.datetime.utcnow()


def get_prefix(bot, message):
    prefixes=[';','b;','B;']

    if beta:
        return "beta;"
    if not message.guild:
        return prefixes
    if message.guild.id in [336642139381301249,264445053596991498,265828729970753537]:
        prefixes=["b;","B;"]

    return commands.when_mentioned_or(*prefixes)(bot, message)


loading_extensions=["cogs.help","cogs.member","cogs.dev","cogs.info","cogs.error","cogs.mod","cogs.server","cogs.fun","cogs.roles","cogs.advancedinfo","cogs.stats","cogs.media","cogs.DBL","cogs.logging","cogs.sql","cogs.nsfw","cogs.music"]
loading_extensions.append("jishaku")
INIT_SHARDS = []
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "False"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"

bot=commands.AutoShardedBot(command_prefix=get_prefix, description="Blink!",help_command=None,shard_count=SHARD_COUNT,shard_ids=SHARD_IDS,case_insensitive=True)
bot.load_extension("cogs.pre-error")
bot.startingcogs=loading_extensions
bot.colour=0xf5a6b9
loadexceptions=""
bot.INITIALIZED=False


def load_extensions():
    for extension in loading_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print("unable to load: " + extension + " Exception was raised: " + str(e))
            global loadexceptions
            loadexceptions=loadexceptions + f"Unable to load: {extension} Exception was raised: {e}\n"


@bot.event
async def on_ready():
    if bot.INITIALIZED:
        return
    bot.INITIALIZED=True
    while len(INIT_SHARDS) != len(SHARD_IDS):
        await asyncio.sleep(1)
    await __init()


@bot.event
async def on_shard_ready(id):
    global INIT_SHARDS
    if id in INIT_SHARDS:
        return
    print(f"Started shard {id}")
    INIT_SHARDS.append(id)


async def __init():
    print("\nInitializing")
    cn={"user":"blink","password":"local","database":"main","host":"localhost"}
    bot.DB=await asyncpg.create_pool(**cn)
    bot.session = aiohttp.ClientSession()
    bot.statsserver=bot.get_guild(blink.Config.statsserver())
    await bot.change_presence(status=discord.Status.online,activity=discord.Streaming(name='; (b;)', url='https://www.twitch.tv/#'))
    bot.boottime=STARTUPTIME
    bot.unload_extension("cogs.pre-error")
    load_extensions()
    boottime=datetime.datetime.utcnow() - STARTUPTIME
    members=len(list(bot.get_all_members()))
    startupid=blink.Config.startup(bot.user.name)
    if not loadexceptions == "":
        x=f"\n***ERRORS OCCURED ON STARTUP:***\n{loadexceptions}"
    else:
        x=""
    boot=f"{'-' * 79}\n**BOT STARTUP:** {bot.user} started at {datetime.datetime.utcnow().isoformat()}\n```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)\nGUILDS:{len(bot.guilds)}\nSHARDS:{bot.shard_count}```\n`d.py version: {discord.__version__}`{x}"
    if startupid:
        if not beta:
            await bot.get_channel(startupid).send(boot)
    bot.bootlog=boot
    print("Bot Ready")
    update.start()


@tasks.loop(minutes=5)
async def update():
    for id in SHARD_IDS:
        await bot.change_presence(shard_id=id,status=discord.Status.online,activity=discord.Streaming(name=f'b;help [{id}]', url='https://www.twitch.tv/#'))


bot.run(open("TOKEN","r").read(), bot=True, reconnect=True)
