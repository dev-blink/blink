import discord # noqa F401
from discord.ext import commands
from string import ascii_uppercase as alphabet
import blink
import websockets
import config
import asyncio
import json
import secrets


TOTAL_CLUSTERS = config.clusters
PER_CLUSTER = config.shards
TOTAL_SHARDS = TOTAL_CLUSTERS * PER_CLUSTER


class Cluster(object):
    def __init__(self,bot:commands.AutoShardedBot,cluster:str):
        self.bot = bot
        self.name = cluster.capitalize()

    async def quit(self):
        await self.ws.quit()
        self.active=False

    async def dispatch(self,data:dict):
        await self.ws.dispatch(data)

    def start(self):
        self.ws = ClusterSocket(f"Cluster-{self.name}",self.bot)
        self.ws.start()
        self.bot.loop.create_task(self.loop())
        self.active=True

    @property
    def guilds(self):
        return self.ws.query()[0]

    @property
    def users(self):
        return self.ws.query()[1]

    def __str__(self):
        shards = self.shards["this"]
        return f"Cluster {self.name}, Shards ({shards[0]}-{shards[-1]})"

    async def loop(self):
        while self.active:
            await asyncio.sleep(5)
            self.update()
            await self.ws.post_stats()

    @property
    def shards(self):
        index = alphabet.index(self.name[0])
        if index >= TOTAL_CLUSTERS:
            raise RuntimeError("Cluster out of total cluster range")
        shards = (index + 1) * PER_CLUSTER
        shards = list(range(shards))[-PER_CLUSTER:]
        return {
            "total":TOTAL_SHARDS,
            "this": shards,
        }

    def update(self):
        stats = {
            "guilds":len(self.bot.guilds),
            "users":len(self.bot.users)
        }
        self.ws.update(stats)

    async def log_startup(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.startup
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)

    async def log_guilds(self,content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.newguilds
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)

    async def log_errors(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.errors
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)

    async def log_warns(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.warns
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)


class ClusterSocket():
    def __init__(self,identifier,bot):
        self.identifier=identifier
        self.beating = False
        self._loop = bot.loop
        self.wait = {}
        self.bot_dispatch = bot.cluster_event

    async def quit(self):
        await self.ws.close(code=1000,reason="Goodbye.")
        self.active=False
        self.beating=False

    def start(self):
        self._loop.create_task(self.loop())
        self.active=True

    def update(self,stats:dict):
        self.guilds = stats["guilds"]
        self.users = stats["users"]

    async def dispatch(self,data):
        payload = {
            "op":5,
            "data":{
                "intent":"DISPATCH",
                "content":data,
            }
        }
        await self.ws.send(json.dumps(payload))

    async def loop(self):
        while self.active:
            self.ws = await websockets.connect(config.gateway)
            try:
                async for message in self.ws:
                    data = json.loads(message)
                    if data["op"] == 0:
                        await self.identify(data)
                    if data["op"] == 3:
                        await self.intent(data["data"])
            except websockets.ConnectionClosed:
                pass
                self.beating=False

    async def identify(self,payload):
        identify = {
            "op":1,
            "data":{
                "identifier":self.identifier,
                "authorization":secrets.websocket,
            }
        }
        await self.ws.send(json.dumps(identify))
        self._loop.create_task(self.heartbeat(payload["data"]["heartbeat"]))

    async def heartbeat(self,timeout):
        self.beating = True
        while self.beating:
            await self.ws.send(json.dumps({"op":2,"data":{}}))
            for x in range(timeout - 3):
                await asyncio.sleep(1)
                if self.active is False:
                    return

    async def post_stats(self):
        payload = {
            "op":5,
            "data":{
                "intent":"STATS",
                "content":{
                    "identifier":self.identifier,
                    "guilds":self.guilds,
                    "users":self.users,
                }
            }
        }
        await self.ws.send(json.dumps(payload))

    async def intent(self,data):
        if data.get("intent") == "STATS":
            self.load_data(data["identifier"],data["guilds"],data["users"])
        if data.get("intent") == "DISPATCH":
            await self.bot_dispatch(data)

    def load_data(self,identifier,guilds,users):
        self.wait[identifier] = (guilds,users)

    def query(self):
        if len(self.wait) != TOTAL_CLUSTERS - 1:
            return (0,0)
        else:
            guilds = self.guilds
            users = self.users
            for cluster in self.wait:
                guilds += self.wait[cluster][0]
                users += self.wait[cluster][1]
            return (guilds,users)
