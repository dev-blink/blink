# External
import discord
from discord.ext import commands, tasks
import asyncpg
import aiohttp
import humanize


# Library
import datetime
import logging
import asyncio
import time
import os
import sys
import traceback
import platform
from io import BytesIO


# Custom
import blink
import clusters
import config
import secrets


# logging
def loggingSetup(cluster):
    if not os.path.exists("logs"):
        os.mkdir("logs")
    logger=logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler=logging.FileHandler(filename=f'logs/{cluster}.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    return logger


printscope = ""


def log(msg:str, scope:str):
    global printscope
    if scope == printscope:
        joiner = ""
    else:
        joiner = "\n"
        printscope = scope
    print(f"{joiner}[{scope.upper()}] {msg}")


# Environment
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"


# Event loop
if platform.platform().startswith("Windows"):
    log("Using Windows Selector loop","loop")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.set_event_loop(asyncio.SelectorEventLoop())


class Ctx(commands.Context):
    def __init__(self,*args,**kwargs):#
        super().__init__(*args,**kwargs)
        if self.guild and hasattr(self.bot,"wavelink"):
            self.player = self.bot.wavelink.players.get(self.guild.id)

    def __repr__(self):
        return f"<Blink context, author={self.author}, guild={self.guild}, >"


class CogStorage:
    def __dir__(self):
        return sorted([a for a in super().__dir__() if not ((a.startswith("__") and a.endswith("__")) or a in ["register","unregister"])])

    def __len__(self):
        return len(dir(self))

    def register(self,obj:object,identifier:str):
        setattr(self,identifier,obj)

    def unregister(self,identifer:str):
        delattr(self,identifer)


class Blink(commands.AutoShardedBot):
    def __init__(self,cluster:clusters.Cluster, logger:logging.Logger):

        # Clustering
        self.cluster = cluster
        shards = self.cluster.shards

        # Sharding
        self._init_shards = set()
        self._shard_ids = shards["this"]

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
            allowed_mentions=discord.AllowedMentions(roles=False,everyone=False,users=False),
            intents=discord.Intents(
                guilds=True,
                voice_states=True,
                messages=True,
                reactions=True,
                presences=False,
                members=True,
            ),
            chunk_guilds_at_startup=True,
        )

        # Globals
        self.colour = 0xf5a6b9
        self._initialized = False
        self.beta=config.beta
        self.boottime=datetime.datetime.utcnow()
        self.created = False
        self.logger = logger

        # Cogs
        self._cogs = CogStorage()
        self.load_extension("cogs.pre-error")
        self.loadexceptions = ""
        self.startingcogs = ["cogs.help","cogs.member","cogs.dev","cogs.info","cogs.error","cogs.mod","cogs.server","cogs.fun","cogs.roles","cogs.advancedinfo","cogs.media","cogs.listing","cogs.sql","cogs.social"]
        self.startingcogs.append("jishaku")
        if not self.beta:
            self.startingcogs.append("cogs.logging")
            self.startingcogs.append("cogs.stats")

        # Global channel cooldown
        self._cooldown = commands.CooldownMapping.from_cooldown(5,5.5,commands.BucketType.channel)
        log(f"Starting - {self.cluster}","boot")

    def __repr__(self):
        return f"<Blink bot, cluster={repr(self.cluster)}, initialized={self._initialized}, since={self.boottime}>"

    def dispatch(self, event, *args,**kwargs):
        if self._initialized or "ready" in event:
            super().dispatch(event, *args,**kwargs)

    async def before_identify_hook(self, shard_id, *, initial=False):
        await asyncio.sleep((not initial) * 5)

    async def launch_shards(self):
        gateway = await self.http.get_gateway()

        self._connection.shard_count = self.shard_count
        self._connection.shard_ids = self.shard_ids

        if not self.cluster.identifier == "A":
            await self.cluster.wait_cluster()
        for shard_id in self.shard_ids:
            await self.launch_shard(gateway, shard_id, initial=(shard_id == self.shard_ids[0]))

        await self.cluster.ws.post_identify()
        self._connection.shards_launched.set()

    async def on_ready(self):
        if self._initialized:
            return
        self._initialized=True
        while len(self._init_shards) != len(self._shard_ids):
            await asyncio.sleep(1)
        await self.create()

    async def on_shard_ready(self,id):
        log(f"Shard {id} ready","ready")
        self._init_shards.add(id)

    async def on_message(self,message: discord.Message):
        if message.author.bot:
            return
        ctx = await self.get_context(message,cls=Ctx)
        if ctx.valid:
            bucket = self._cooldown.get_bucket(message)
            limit = bucket.update_rate_limit()
            if not limit:
                await self.invoke(ctx)
            else:
                if message.guild and not message.channel.permissions_for(message.guild.me):
                    return
                try:
                    await message.add_reaction("<:CHANNEL_COOLDOWN:785184949723594782>")
                except discord.HTTPException:
                    return

    def load_extensions(self):
        for extension in self.startingcogs:
            try:
                self.load_extension(extension)
            except Exception as e:
                log(f"Unable to load: {extension} Exception was raised: {e}","boot")
                self.loadexceptions += f"Unable to load: {extension} Exception was raised: {e}\n"

    async def warn(self,message,shouldRaise=True):
        time = datetime.datetime.utcnow()
        message = f"{time.year}/{time.month}/{time.day} {time.hour}:{time.minute} [{self.cluster.identifier}/WARNING] {message}"
        await self.cluster.log_warns(message)
        if shouldRaise:
            raise blink.SilentWarning(message)

    async def create(self):
        before = time.perf_counter()
        self.cluster._post.set()
        log("Waiting on clusters","boot")
        await self.cluster.wait_until_ready()
        log(f"Clusters took {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')} to start","boot")
        self.DB=await asyncpg.create_pool(**{"user":"blink","password":secrets.db,"database":"main","host":"db.blinkbot.me"})
        self.session = aiohttp.ClientSession()
        self.unload_extension("cogs.pre-error")
        self.load_extensions()
        boottime=datetime.datetime.utcnow() - self.boottime
        members=len(list(self.get_all_members()))
        boot=[
            '-' * 79,
            f"**BOT STARTUP:** {self.cluster.identifier} started at {datetime.datetime.utcnow()}",
            f"```STARTUP COMPLETED IN : {boottime} ({round(members / boottime.total_seconds(),2)} members / second)",
            f"GUILDS:{len(self.guilds)}",
            f"SHARDS:{len(self.shards)}```",
        ]
        if not self.loadexceptions == "":
            boot.append("@everyone ***BOOT ERRORS***\n" + self.loadexceptions)

        self.bootlog="\n".join(boot)
        if not self.beta:
            await self.cluster.log_startup(self.bootlog)
        self.created = True
        log(f"Created in {humanize.naturaldelta(time.perf_counter()-before,minimum_unit='microseconds')}","boot")
        log(f"Total start time was {humanize.naturaldelta(datetime.datetime.utcnow()- self.boottime)}","boot")
        self.update_pres.start()

    async def get_prefix(self, message):
        prefixes=[';','b;','B;','blink ']

        if self.beta:
            return ["beta;"]
        if message.guild and message.guild.id in [336642139381301249,264445053596991498,265828729970753537,568567800910839811]:
            prefixes.remove(";")

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
            await self.get_cog(self._cogs.dev.blacklist_update_mappings[payload["scope"]]).flush_blacklist()
        if payload["event"] == "SHUTDOWN":
            await self.cluster.quit()
            await self.logout()
            await self.close()
            await self.loop.close()
            sys.exit(0)
        if payload["event"] == "RELOAD":
            self.reload_extension(payload["cog"])

    async def on_error(self,event_method,*args,**kwargs):
        exc = sys.exc_info()
        tb = traceback.format_exc()
        embed = discord.Embed(colour=discord.Colour.red(),title=f"{exc[0].__qualname__} - {exc[1]}")
        embed.set_author(name=f"Exception in event {event_method}")
        file = None
        async with aiohttp.ClientSession() as cs:
            if len(tb) < 2040:
                file = discord.File(BytesIO(tb.encode("utf-8")), filename="tb.txt")
            else:
                embed.description = f"```{tb}```"
            hook = discord.Webhook(secrets.errorhook,adapter=discord.AsyncWebhookAdapter(cs))
            await hook.send(embed=embed,username=f"CLUSTER {self.cluster.identifier} EVENT ERROR",file=file)


async def launch(loop):
    cluster = clusters.Cluster()
    cluster.start(loop)
    identifier = await cluster.wait_identifier()
    log = loggingSetup(identifier)
    bot = Blink(cluster, log)
    cluster.reg_bot(bot)
    try:
        await bot.start(secrets.token, bot=True, reconnect=False)
    except KeyboardInterrupt:
        await bot.logout()
        await cluster.quit()
        loop.close()
        sys.exit(1)
    except Exception as e:
        await cluster.crash(e, traceback.format_exc())
        print("Fatal client exception - exiting")
        await asyncio.sleep(5)
        loop.close()
        sys.exit(130)

loop = asyncio.get_event_loop()
server = loop.run_until_complete(launch(loop))
