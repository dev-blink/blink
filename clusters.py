# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import collections
import discord # noqa F401
from discord.ext.commands import AutoShardedBot
from string import ascii_uppercase as alphabet
import blink
import websockets
import asyncio
import json
import secrets
import uuid
import sys
import time


class Cluster(object):
    def __init__(self, gateway):
        self.active=False
        self._post = asyncio.Event()
        self.gateway = gateway

    def __str__(self):
        shards = self.shards["this"]
        series = self.shards["series"]
        return f"Cluster {self.identifier} ({series[0]}/{series[1]}), Shards ({shards[0]}-{shards[-1]})"

    def __repr__(self):
        return f"<Identifier={self.identifier}, shards={self.shards}, active={self.active}>"

    async def crash(self,error,traceback):
        await self.ws.panic(error,traceback)
        await self.quit()

    @property
    def latency(self):
        try:
            return round(self.ws.latency() * 10**6, 5)
        except OverflowError:
            return float('inf')

    def reg_bot(self,bot:AutoShardedBot):
        self.bot = bot
        self.ws.bot = bot
        self.ws.bot_dispatch = bot.cluster_event

    async def wait_identifier(self):
        await self.ws._ready.wait()
        self.identifier = self.ws.identifier
        return self.identifier

    async def wait_until_ready(self):
        if self.ws._total_clusters == 1:
            return
        await self.ws._online.wait()

    async def quit(self):
        await self.ws.quit()
        self.active=False

    async def dispatch(self,data:dict):
        await self.ws.dispatch(data)

    async def dedupe(self,scope:str,hash:str):
        return await self.ws.dedupe({"scope":scope,"content":hash},str(uuid.uuid4()))

    def start(self,loop):
        self.ws = ClusterSocket(loop,self,self.gateway)
        self.ws.start()
        self.active = True
        loop.create_task(self.loop())

    @property
    def guilds(self):
        return self.ws.query()["guilds"]

    @property
    def users(self):
        return self.ws.query()["users"]

    @property
    def music(self):
        return self.ws.query()["music"]

    async def loop(self):
        await self.wait_identifier()
        await self._post.wait()
        while self.active:
            self.update()
            await self.ws.post_stats() if self.ws.connected else None
            await asyncio.sleep(5)

    @property
    def shards(self):
        index = alphabet.index(self.identifier)
        if index >= self.ws._total_clusters:
            raise RuntimeError("Cluster out of total cluster range")
        shards = (index + 1) * self.ws._per_cluster
        shards = list(range(shards))[-self.ws._per_cluster:]
        return {
            "total":self.ws._total_shards,
            "this": shards,
            "series": (index + 1,self.ws._total_clusters),
            "count": self.ws._per_cluster,
        }

    def update(self):
        try:
            music = len(self.bot.wavelink.players)
        except Exception:
            music = 0
        stats = {
            "guilds":len(self.bot.guilds),
            "users":sum(g.member_count for g in self.bot.guilds),
            "music":music,
        }
        self.ws.update(stats)

    async def log_startup(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.startup()
        if embed:
            embed = embed.to_dict()
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)

    async def log_errors(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.errors()
        if embed:
            embed = embed.to_dict()
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)

    async def log_warns(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.warns()
        if embed:
            embed = embed.to_dict()
        return await self.bot.http.send_message(channel,content,tts=tts,embed=embed,nonce=nonce)

    async def wait_cluster(self):
        await self.ws.wait_for_identify()


class ClusterSocket():
    def __init__(self,loop,cluster, gateway):
        self.cluster = cluster
        self.beating = False
        self._loop = loop
        self.wait = {}
        self.guilds=0
        self.users=0
        self.music = 0
        self.dupes = {}
        self.active = False
        self.connected = False
        self._ready = asyncio.Event()
        self._online = asyncio.Event()
        self.identify_hold = asyncio.Event()
        self.identify_hold_after = asyncio.Event()
        self.gateway = gateway
        self.sequence = 0
        self._latencies_sent = collections.deque([], 50)
        self._latencies_recieved = blink.CacheDict(50)

    async def quit(self, code=1000, reason="Goodbye <3"):
        await self.ws.close(code=code,reason=reason)
        self.active=False
        self.beating=False

    async def panic(self,error,traceback):
        payload = {
            "op":7,
            "data":{
                "error":str(error),
                "traceback":traceback,
            }
        }
        await self.send(payload)
        await self.quit(code=4999, reason=f"Client threw unhandled internal exception {error.__class__.__qualname__}")

    async def send(self, payload):
        self._latencies_sent.append((time.perf_counter_ns(), self.sequence + 1))
        await self.ws.send(json.dumps(payload))

    def start(self):
        self._loop.create_task(self.loop())
        self.active=True

    def update(self,stats:dict):
        self.guilds = stats["guilds"]
        self.users = stats["users"]
        self.music = stats["music"]

    async def dispatch(self,data):
        payload = {
            "op":5,
            "data":{
                "intent":"DISPATCH",
                "content":data,
            }
        }
        await self.send(payload)

    async def loop(self):
        while self.active:
            self.ws = await websockets.connect(self.gateway)
            self.connected = True
            try:
                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        if hasattr(self.cluster,'bot'):
                            self.cluster.bot.logger.debug(f"Cluster recived WS message {data}")
                        self.sequence = data["seq"]
                        if data["op"] == 0:
                            await self.identify(data)
                        if data["op"] == 3:
                            await self.intent(data["data"])
                        if data["op"] == 4:
                            self._latencies_recieved[data["seq"]] = time.perf_counter_ns()
                        if data["op"] == 6:
                            await self.reg_dupe(data["data"])
                    except Exception as e:
                        await self.bot.warn(f"Exception in cluster recieve {type(e)} {e}")
            except websockets.ConnectionClosed as e:
                if e.code == 4007:
                    print("Cluster pool overpopulated, exiting without reconnect")
                    await asyncio.sleep(5)
                    sys.exit(2)
                self.beating=False

    async def identify(self,payload):
        self.hello(payload["data"])
        identify = {
            "op":1,
            "data":{
                "identifier":self.identifier,
                "authorization":secrets.websocket,
            }
        }
        self._ready.set()
        await self.ws.send(json.dumps(identify))
        self._loop.create_task(self.heartbeat(payload["data"]["heartbeat"]))

    def hello(self,data):
        self.identifier = data["cluster"]
        self._total_clusters = data["total"]
        self._per_cluster = data["shard"]
        self._total_shards = data["total"] * data["shard"]

        self.before = alphabet[alphabet.index(self.identifier) - 1]
        self.after = alphabet[alphabet.index(self.identifier) + 1]

    async def heartbeat(self,timeout):
        self.beating = True
        while self.beating:
            await self.ws.send(json.dumps({"op":2,"data":{}}))
            for x in range(timeout - 3):
                await asyncio.sleep(1)
                if self.active is False:
                    return

    def latency(self):
        """socket latency in nanoseconds"""
        latencies = 0

        def latency_iter():
            for (sent, key) in self._latencies_sent:
                recv = self._latencies_recieved.get(key)
                if recv:
                    nonlocal latencies
                    latencies += 1
                    yield recv - sent

        try:
            return sum(latency_iter()) / latencies
        except ZeroDivisionError:
            return float('inf')

    async def post_stats(self):
        payload = {
            "op":5,
            "data":{
                "intent":"STATS",
                "content":{
                    "identifier":self.identifier,
                    "guilds":self.guilds,
                    "users":self.users,
                    "music":self.music,
                }
            }
        }
        await self.send(payload)

    async def intent(self,data):
        if data.get("intent") == "STATS":
            self.load_data(data["identifier"],data["guilds"],data["users"],data["music"])
        if data.get("intent") == "DISPATCH":
            await self.bot_dispatch(data)
        if data.get("intent") == "IDENTIFIED":
            if data.get("identifier") == self.before:
                self.identify_hold.set()
            elif data.get("identifier") == self.after:
                self.identify_hold_after.set()

    def load_data(self,identifier,guilds,users,music):
        self.wait[identifier] = (guilds,users,music)
        if len(self.wait) == self._total_clusters - 1:
            if not self._online.is_set():
                self._online.set()

    def query(self):
        if not self._online.is_set():
            guilds=0
            users=0
            music=-1
        else:
            guilds = self.guilds
            users = self.users
            music = self.music
            for cluster in self.wait:
                guilds += self.wait[cluster][0]
                users += self.wait[cluster][1]
                music += self.wait[cluster][2]
        return {
            "guilds":guilds,
            "users":users,
            "music":music,
        }

    async def reg_dupe(self,payload):
        self.dupes[payload["req"]] = payload["duplicate"]

    async def dedupe(self,payload:dict,req:str):
        payload["req"] = req
        await self.ws.send(json.dumps({"op":6,"data":payload}))
        while True:
            await asyncio.sleep(0)
            if self.dupes.get(req) is None:
                continue
            else:
                res = self.dupes[req]
                del self.dupes[req]
                return res

    async def wait_for_identify(self):
        await self.identify_hold.wait()

    async def post_identify(self):
        payload = {
            "op":5,
            "data":{
                "intent":"IDENTIFIED",
                "content":{
                    "identifier":self.identifier
                }
            }
        }
        await self.send(payload)
        if alphabet.index(self.identifier) + 1 == self._total_clusters:
            return
        self._loop.create_task(self.post_identify_loop(payload))

    async def post_identify_loop(self,payload):
        while not self.identify_hold_after.is_set():
            await asyncio.sleep(5)
            await self.send(payload)
