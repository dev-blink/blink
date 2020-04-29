import discord
from discord.ext import commands
from discord.utils import find
import os
import sys, traceback
import blink
import datetime

STARTUPTIME = datetime.datetime.utcnow()

def get_prefix(bot, message):
    prefixes = [';','b;','B;']

    # Non Guild prefix
    if not message.guild:
        #? in dms
        return '?'
    if bot.user.name == "blink beta":
        return '?'

    if message.guild.id in [336642139381301249,264445053596991498]:
        prefixes = ["b;","B;"]
    #Guild prefix - mention or prefixes
    return commands.when_mentioned_or(*prefixes)(bot, message)

loading_extensions = ["cogs.member","cogs.dev","cogs.info","cogs.error","cogs.mod","cogs.server","cogs.fun","cogs.help","cogs.roles","cogs.advancedinfo","cogs.stats","cogs.media","cogs.DBL","cogs.music","cogs.media"]
loading_extensions.append("jishaku")

INITIALIZED = False
print("Initializing AutoShardedBot and global vars.")
activity = discord.Game(name="Bot is starting, please wait.")
bot = commands.AutoShardedBot(command_prefix=get_prefix, description="Blink! | General use bot built on discord.py",activity=activity,status=discord.Status.dnd)
bot.load_extension("cogs.PRELOAD")
bot.startingcogs = loading_extensions
bot.colour = 0xf5a6b9
loadexceptions = ""
def load_extensions():
    print("Initializing Extensions")
    for extension in loading_extensions:
        try:
            bot.load_extension(extension)
            print("Loaded: " + extension)
        except Exception as e:
            print("unable to load: " + extension + " Exception was raised: " + str(e))
            global loadexceptions
            loadexceptions = loadexceptions + f"Unable to load: {extension} Exception was raised: {e}"
    print("Finished loading cogs\n")





@bot.event
async def on_ready():
    global INITIALIZED
    if not INITIALIZED:
        await init()
        INITIALIZED = True


async def init():
    print(f'\nLogged in as: {bot.user.name} - {bot.user.id}\nDiscord.py Version: {discord.__version__}')
    bot.statsserver = bot.get_guild(blink.Config.statsserver())
    game = discord.Streaming(name='; (b;)', url='https://www.twitch.tv/#')
    await bot.change_presence(status=discord.Status.online,activity=game)
    bot.boottime = STARTUPTIME
    bot.unload_extension("cogs.PRELOAD")
    load_extensions()
    print(f'Successfully logged in and booted.')
    print("Server Count: " + str(len(bot.guilds)) + "\nShard Count: " + str(bot.shard_count))
    boottime = datetime.datetime.utcnow() - STARTUPTIME
    members = len(list(bot.get_all_members()))
    print(f"STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)")
    startupid = blink.Config.startup(bot.user.name)
    if startupid:
        if not loadexceptions == "":
            x = f"\n***ERRORS OCCURED ON STARTUP:***\n{loadexceptions}"
        else:
            x=""
        spacer = "-"*79
        boot = f"{spacer}\n**BOT STARTUP:** {bot.user} started at {datetime.datetime.utcnow().isoformat()}\n```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)\nGUILDS:{len(bot.guilds)}\nSHARDS:{bot.shard_count}```\n`d.py version: {discord.__version__}`{x}"
        await bot.get_channel(startupid).send(boot)
        bot.bootlog = boot
    else:
        bot.bootlog = "Unavailable on beta"



bot.run(open("TOKEN","r").read(), bot=True, reconnect=True)