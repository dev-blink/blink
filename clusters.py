# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021

from typing import Callable
from collections import deque
import discord  # noqa F401
from discord.ext.commands import AutoShardedBot
from string import ascii_uppercase as alphabet
from async_timeout import timeout as TimeoutManager

import blink
import websockets
import asyncio
import json
import blinksecrets as secrets
import sys
import time


def _request_tag_generator():
    i = 0
    while True:
        yield i
        i += 1


class Cluster:
    def __init__(self, gateway):
        self.active = False # If this cluster is active and ready to operate
        self._post = asyncio.Event() # Wait for internal bot cache to be ready before posting statistics
        self.gateway = gateway

    def __str__(self):
        shards = self.shards["this"]
        series = self.shards["series"]
        return f"Cluster {self.identifier} ({series[0]}/{series[1]}), Shards ({shards[0]}-{shards[-1]})"

    def __repr__(self):
        return f"<Identifier={self.identifier}, shards={self.shards}, active={self.active}>"

    async def crash(self, error, traceback):
        """Crash handler"""
        await self.ws.panic(error, traceback)
        await self.quit()

    @property
    def latency(self):
        """Time between heartbeats being sent and being acked in ms"""
        return round(self.ws.latency() * 1000, 2)

    def reg_bot(self, bot: AutoShardedBot):
        """Register the bot object to this cluster after getting an identifier from the controller"""
        self.bot = bot
        self.ws.bot = bot
        self.ws.bot_dispatch = bot.cluster_event # the coroutine for handling events sent from the controller

    async def wait_identifier(self):
        """Wait for the controller to assign an identifier"""
        await self.ws._ready.wait()
        self.identifier = self.ws.identifier
        self.index = alphabet.index(self.identifier)
        return self.identifier

    async def wait_until_ready(self):
        """Wait until all clusters are online and ready to post stats"""
        if self.ws._total_clusters == 1:
            return
        await self.ws._online.wait()

    async def quit(self):
        """Quit safely"""
        await self.ws.quit()
        self.active = False

    async def dispatch(self, data: dict):
        """Public access to send a message"""
        await self.ws.dispatch(data)

    async def dedupe(self, scope: str, hash: str):
        """Stop duplicate actions being completed by multiple clusters"""
        return await self.ws.dedupe({"scope": scope, "content": hash})

    def start(self, loop):
        """Start the internal loop in the asyncio event loop"""
        self.ws = ClusterSocket(loop, self, self.gateway)
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
        """Main loop to push the websocket"""
        await self.wait_identifier()
        await self._post.wait()
        while self.active:
            self.update()
            await self.ws.post_stats() if self.ws.connected else None
            await asyncio.sleep(5)

    @property
    def shards(self):
        """Returns a dictionary of shard information worked out from information given by the controller"""
        index = self.index
        if index >= self.ws._total_clusters:
            raise RuntimeError("Cluster out of total cluster range")
        shards = (index + 1) * self.ws._per_cluster
        shards = list(range(shards))[-self.ws._per_cluster:]
        return {
            "total": self.ws._total_shards,
            "this": shards,
            "series": (index + 1, self.ws._total_clusters),
            "count": self.ws._per_cluster,
        }

    def update(self):
        """Sync stored stats with the bot stats"""
        try:
            music = len(self.bot.wavelink.players)
        except AttributeError:
            music = 0
        stats = {
            "guilds": len(self.bot.guilds),
            "users": sum(g.member_count for g in self.bot.guilds),
            "music": music,
        }
        self.ws.update(stats)

    # Proxy functions to immitate abc.Messageable.send, can send messages without channels being cached
    async def log_startup(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.startup()
        return await self.bot.get_partial_messageable(channel).send(content, tts=tts, embed=embed, nonce=nonce)

    async def log_errors(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.errors()
        return await self.bot.get_partial_messageable(channel).send(content, tts=tts, embed=embed, nonce=nonce)

    async def log_warns(self, content=None, tts=False, embed=None, nonce=None):
        channel = blink.Config.warns()
        return await self.bot.get_partial_messageable(channel).send(content, tts=tts, embed=embed, nonce=nonce)

    async def wait_cluster(self):
        await self.ws.wait_for_identify()


class ClusterSocket():
    def __init__(self, loop, cluster, gateway):
        self.cluster = cluster
        self.beating = False
        self._loop = loop
        self.stats_wait = {}
        self.guilds = 0
        self.users = 0
        self.music = 0
        self.active = False
        self.connected = False
        self._ready = asyncio.Event()
        self._online = asyncio.Event()
        self.identify_hold = asyncio.Event()
        self.identify_hold_after = asyncio.Event()
        self.gateway = gateway
        self.sequence = 0
        self.heartbeat_last_sent = None
        self.request_tags = _request_tag_generator()
        self.latencies = deque([], maxlen=50)
        self.wait_events = {}
        self.wait_checks = {}
        self.wait_responses = {}

    async def quit(self, code=1000, reason="Goodbye <3"):
        """Stop the websocket"""
        self.active = False
        self.beating = False
        await self.ws.close(code=code, reason=reason)

    async def panic(self, error, traceback):
        """Send a panic message to the controller"""
        payload = {
            "op": 7,
            "data": {
                "error": str(error),
                "traceback": traceback,
            }
        }
        await self.send(payload)
        await self.quit(code=4999, reason=f"Client threw unhandled internal exception {error.__class__.__qualname__}")

    async def send(self, payload):
        """Send a dict over the websocket"""
        await self.ws.send(json.dumps(payload))

    def start(self):
        """Start internal ws poll"""
        self._loop.create_task(self.loop())
        self.active = True

    def register_waiter(self, id, check):
        self.wait_events[id] = asyncio.Event()
        self.wait_checks[id] = check
        self.wait_responses[id] = None

    def unregister_waiter(self,id):
        del self.wait_events[id]
        del self.wait_checks[id]
        del self.wait_responses[id]

    async def wait_for(self, check: Callable, timeout: int = 30) -> dict:
        """Wait for a payload that when passed to the check will return true"""
        id = next(self.request_tags)
        self.register_waiter(id, check)
        try:
            async with TimeoutManager(timeout):
                await self.wait_events[id].wait()
        except asyncio.TimeoutError:
            # Catch and reraise to cleanup and prevent leaks
            self.unregister_waiter(id)
            raise
        # Only wait in the timeout to prevent a timeout being raised during logic
        payload = self.wait_responses[id]
        self.unregister_waiter(id)
        return payload

    async def check_waiters(self, payload: dict):
        """Check if a payload is being waited on"""
        for id, check in self.wait_checks.items():
            if check(payload):
                self.wait_responses[id] = payload
                self.wait_events[id].set()
                self.bot.logger.info(f"check id {id} passed with payload {payload}")
            else:
                self.bot.logger.debug(f"check id {id} failed with payload {payload}")

    def update(self, stats: dict):
        """Pass stats to the socket handler"""
        self.guilds = stats["guilds"]
        self.users = stats["users"]
        self.music = stats["music"]

    async def dispatch(self, data):
        payload = {
            "op": 5,
            "data": {
                "intent": "DISPATCH",
                "content": data,
            }
        }
        await self.send(payload)

    async def loop(self):
        while self.active:
            try:
                self.ws = await websockets.connect(self.gateway)
            except OSError:
                if hasattr(self, "bot"):
                    await self.bot.stop(False)
                    raise
                else:
                    raise
            self.connected = True
            try:
                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        if hasattr(self.cluster, 'bot'):
                            self.cluster.bot.logger.debug(
                                f"Cluster recived WS message {data}")
                        self.sequence = data["seq"]
                        if data["op"] == 0:
                            await self.identify(data)
                        if data["op"] == 3:
                            await self.intent(data["data"])
                        await self.check_waiters(data)
                    except Exception as e:
                        await self.bot.warn(f"Exception in cluster recieve {type(e)} {e}", False)
            except websockets.ConnectionClosed as e:
                if e.code == 4007: # Too many clusters, we arent needed
                    print("Cluster pool overpopulated, exiting without reconnect")
                    await asyncio.sleep(5)
                    sys.exit(2)
                elif e.code == 4999: # We crashed
                    return
                elif e.code in range(4001,4005 + 1): # 4001-4005
                    raise
                self.beating = False

    async def identify(self, payload):
        self.hello(payload["data"])
        identify = {
            "op": 1,
            "data": {
                "identifier": self.identifier,
                "authorization": secrets.websocket,
            }
        }
        self._ready.set()
        await self.send(identify)
        self._loop.create_task(self.heartbeat(payload["data"]["heartbeat"]))

    def hello(self, data):
        self.identifier = data["cluster"]
        self._total_clusters = data["total"]
        self._per_cluster = data["shard"]
        self._total_shards = data["total"] * data["shard"]

        self.before = alphabet[alphabet.index(self.identifier) - 1]
        self.after = alphabet[alphabet.index(self.identifier) + 1]

    async def heartbeat(self, timeout):
        self.beating = True
        while self.beating:
            if not self.active:
                return
            await self.send({"op": 2, "data": {}})
            self.heartbeat_last_sent = time.perf_counter()
            self._loop.create_task(self.calculate_heartbeat_interval())
            await asyncio.sleep(timeout)

    async def calculate_heartbeat_interval(self):
        await self.wait_for(lambda p: (p["op"] == 4 and p["data"]["received"] == 2))
        duration = time.perf_counter() - self.heartbeat_last_sent
        self.latencies.appendleft(duration)

    def latency(self):
        num_latencies = len(self.latencies)
        if num_latencies > 0:
            return sum(self.latencies) / num_latencies
        else:
            return float('inf')

    async def post_stats(self):
        payload = {
            "op": 5,
            "data": {
                "intent": "STATS",
                "content": {
                    "identifier": self.identifier,
                    "guilds": self.guilds,
                    "users": self.users,
                    "music": self.music,
                }
            }
        }
        await self.send(payload)

    async def intent(self, data): # could use handlers
        if data.get("intent") == "STATS":
            self.load_data(data["identifier"], data["guilds"],
                           data["users"], data["music"])
        if data.get("intent") == "DISPATCH":
            await self.bot_dispatch(data)
        if data.get("intent") == "IDENTIFIED":
            if data.get("identifier") == self.before:
                self.identify_hold.set()
            elif data.get("identifier") == self.after:
                self.identify_hold_after.set()

    def load_data(self, identifier, guilds, users, music):
        self.stats_wait[identifier] = (guilds, users, music)
        if len(self.stats_wait) == self._total_clusters - 1:
            if not self._online.is_set():
                self._online.set()

    def query(self):
        if not self._online.is_set():
            guilds = 0
            users = 0
            music = -1
        else:
            guilds = self.guilds
            users = self.users
            music = self.music
            for cluster in self.stats_wait:
                guilds += self.stats_wait[cluster][0]
                users += self.stats_wait[cluster][1]
                music += self.stats_wait[cluster][2]
        return {
            "guilds": guilds,
            "users": users,
            "music": music,
        }

    async def dedupe(self, payload: dict):
        request_tag = next(self.request_tags)
        payload["req"] = request_tag
        await self.send({"op": 6, "data": payload})
        response = await self.wait_for(lambda p: (p["op"] == 6 and p["data"]["req"] == request_tag))
        return response["data"]["duplicate"]

    async def wait_for_identify(self):
        await self.identify_hold.wait()

    async def post_identify(self):
        payload = {
            "op": 5,
            "data": {
                "intent": "IDENTIFIED",
                "content": {
                    "identifier": self.identifier
                }
            }
        }
        await self.send(payload)
        if alphabet.index(self.identifier) + 1 == self._total_clusters:
            return
        self._loop.create_task(self.post_identify_loop(payload))

    async def post_identify_loop(self, payload):
        while not self.identify_hold_after.is_set():
            await asyncio.sleep(5)
            await self.send(payload)
