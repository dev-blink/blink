import discord
from discord.ext import commands, tasks
import blink
import datetime
import asyncpg
import logging
import asyncio
import aiohttp
import os
import secrets
import clusters
import config
import time
import humanize
import sys
import traceback


cluster=input("Cluster>")


# Logging
logger=logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler=logging.FileHandler(filename=f'{cluster}.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


# Environment
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"


class Ctx(commands.Context):
    def __init__(self,*args,**kwargs):#
        super().__init__(*args,**kwargs)
        if self.guild and hasattr(self.bot,"wavelink"):
            self.player = self.bot.wavelink.players.get(self.guild.id)

    def __repr__(self):
        return f"<Blink context, author={self.author}, guild={self.guild}, >"


class CogStorage:
    def __dir__(self):
        return sorted([a for a in super().__dir__() if not (a.startswith("__") and a.endswith("__"))])

    def __len__(self):
        return len(dir(self))


class Blink(commands.AutoShardedBot):
    def __init__(self,cluster:str):

        # Clustering
        self.cluster = clusters.Cluster(self,cluster)
        shards = self.cluster.shards

        # Sharding
        self.INIT_SHARDS = []
        self.SHARD_IDS = shards["this"]

        # Main
        super().__init__(
            command_prefix=self.get_prefix,
            help_command=None,
            shard_count=shards["total"],
            shard_ids=shards["this"],
            case_insensitive=True,
            status=discord.Status.dnd,
            activity=discord.Streaming(name='starting up...', url='https://www.twitch.tv/#'),
            owner_ids=[171197717559771136,741225148509847642,],
            allowed_mentions=discord.AllowedMentions(roles=False,everyone=False),
        )

        # Globals
        self.colour = 0xf5a6b9
        self.INITIALIZED = False
        self.beta=config.beta
        self.boottime=datetime.datetime.utcnow()

        # Cogs
        self._cogs = CogStorage()
        self.load_extension("cogs.pre-error")
        self.loadexceptions = ""
        self.startingcogs = ["cogs.help","cogs.member","cogs.dev","cogs.info","cogs.error","cogs.mod","cogs.server","cogs.fun","cogs.roles","cogs.advancedinfo","cogs.media","cogs.listing","cogs.sql","cogs.music","cogs.social"]
        self.startingcogs.append("jishaku")
        if not self.beta:
            self.startingcogs.append("cogs.logging")
            self.startingcogs.append("cogs.stats")

        print(f"Starting - {self.cluster}\n")

    def __repr__(self):
        return f"<Blink bot, cluster={repr(self.cluster)}, initialized={self.INITIALIZED}, since={self.boottime}>"

    async def on_ready(self):
        if self.INITIALIZED:
            return
        self.INITIALIZED=True
        while len(self.INIT_SHARDS) != len(self.SHARD_IDS):
            await asyncio.sleep(1)
        await self.create()

    async def on_shard_ready(self,id):
        if id in self.INIT_SHARDS:
            return
        print(f"Shard {id} ready")
        self.INIT_SHARDS.append(id)

    async def on_message(self,message):
        if message.author.bot:
            return
        ctx = await self.get_context(message,cls=Ctx)
        await self.invoke(ctx)

    def load_extensions(self):
        for extension in self.startingcogs:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f"Unable to load: {extension} Exception was raised: {e}")
                self.loadexceptions += f"Unable to load: {extension} Exception was raised: {e}\n"

    async def warn(self,message,shouldRaise=True):
        time = datetime.datetime.utcnow()
        message = f"{time.year}/{time.month}/{time.day} {time.hour}:{time.minute} [{self.cluster.name}/WARNING] {message}"
        await self.cluster.log_warns(message)
        if shouldRaise:
            raise blink.SilentWarning(message)

    async def create(self):
        before = time.perf_counter()
        self.cluster.start()
        await self.cluster.wait_until_ready()
        print(f"\nClusters took {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')} to start")
        self.DB=await asyncpg.create_pool(**{"user":"blink","password":secrets.db,"database":"main","host":"db.blinkbot.me"})
        self.session = aiohttp.ClientSession()
        self.unload_extension("cogs.pre-error")
        self.load_extensions()
        boottime=datetime.datetime.utcnow() - self.boottime
        members=len(list(self.get_all_members()))
        boot=[
            '-' * 79,
            f"**BOT STARTUP:** {self.cluster.name} started at {datetime.datetime.utcnow()}",
            f"```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)",
            f"GUILDS:{len(self.guilds)}",
            f"SHARDS:{len(self.shards)}```",
        ]
        if not self.loadexceptions == "":
            boot.append("@everyone ***BOOT ERRORS***\n" + self.loadexceptions)

        self.bootlog="\n".join(boot)
        if not self.beta:
            await self.cluster.log_startup(self.bootlog)
        print(f"Created in {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')}\nTotal start time was {humanize.naturaldelta(datetime.datetime.utcnow()- self.boottime)}")
        self.update_pres.start()

    async def get_prefix(self, message):
        prefixes=[';','b;','B;','blink ']

        if self.beta:
            return ["beta;"]
        if message.guild and message.guild.id in [336642139381301249,264445053596991498,265828729970753537,568567800910839811]:
            prefixes.remove(";")

        if message.author.id in self.owner_ids:
            prefixes.append('')

        return commands.when_mentioned_or(*prefixes)(self,message)

    @tasks.loop(hours=1)
    async def update_pres(self):
        for id in self.shards:
            try:
                await self.change_presence(shard_id=id,status=discord.Status.online,activity=discord.Streaming(name=f'b;help [{self.cluster.identifier}{id}]', url='https://www.twitch.tv/#'))
            except Exception as e:
                await self.warn(f"Error occured in presence update {type(e)} `{e}`",False)

    async def cluster_event(self,payload):
        if payload is None:
            return
        if payload["event"] == "UPDATE_BLACKLIST":
            await self.get_cog(self.get_cog("Developer").blacklist_update_mappings[payload["scope"]]).flush_blacklist()
        if payload["event"] == "SHUTDOWN":
            await self.cluster.quit()
            await self.logout()
            await self.close()
            await self.loop.close()
            exit()
        if payload["event"] == "RELOAD":
            self.reload_extension(payload["cog"])

    async def on_error(self,event_method,*args,**kwargs):
        exc = sys.exc_info()
        tb = traceback.format_exc()
        embed = discord.Embed(colour=discord.Colour.red(),title=f"{exc[0].__qualname__} - {exc[1]}")
        embed.set_author(name=f"Exception in event {event_method}")
        async with aiohttp.ClientSession() as cs:
            async with cs.post("https://hastebin.com/documents",data=tb) as haste:
                data = await haste.json()
                embed.description = f"[Traceback](https://hastebin.com/{data['key']})"
            hook = discord.Webhook(secrets.errorhook,adapter=discord.AsyncWebhookAdapter(cs))
            await hook.send(embed=embed,username=f"CLUSTER {self.cluster.identifier} EVENT ERROR")


BOT = Blink(cluster)
BOT.run(secrets.token, bot=True, reconnect=True)
