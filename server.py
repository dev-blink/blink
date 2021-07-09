# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


# TODO: rewrite this in rust
from autobahn.asyncio import websocket
from autobahn.exception import Disconnected
import json
import uuid
import platform
import asyncio
from async_timeout import timeout
import serverconfig as config
from string import ascii_uppercase as alphabet
import datetime
import aiohttp

tokens = config.gatewayauth
loop = asyncio.get_event_loop()


async def _panic(message: str, cluster: str):
    data = {
        "app_key": config.panic_app_key,
        "app_secret": config.panic_app_secret,
        "access_token": config.panic_access_token,
        "content": message,
        "target_type": "user",


    }
    async with aiohttp.ClientSession() as cs:
        async with cs.post("https://api.pushed.co/1/push", data=data, headers={"content-type": "application/x-www-form-urlencoded"}) as response:
            print(
                f"[GATEWAY]PANIC REPORT SENT FOR CLUSTER {cluster} AT {datetime.datetime.utcnow()} UTC NOTIFICATIONS SERVICE RESPONSED WITH HTTP {response.status}")


class Message:
    def __init__(self, op: int, data: dict):
        self.op = op
        self.data = data


class Intent:
    def __init__(self, intent: str, data: dict):
        self.op = 3
        self.intent = intent.upper()
        self.data = {
            "intent": self.intent,
        }
        self.data.update(data)


class ServerProtocol(websocket.WebSocketServerProtocol):
    def __init__(self):
        super().__init__()
        self.sequence = 0
        self.authenticated = False
        self.open = False
        self.ops = [0, 1, 2, 3, 4, 5, 6, 7]
        self.beating = False
        self.handlers = {
            0: self.invalid_opcode,
            2: self.registerHeartbeat,
            1: self.identify,
            3: self.event,
            4: self.invalid_opcode,
            5: self.broadcast,
            6: self.dedupe,
            7: self.panicked,
        }

    async def broadcast(self, payload):
        if payload.get("intent") is None:
            return await self.close(code=4001, error="No intent provided")
        if payload.get("content") is None:
            return await self.close(code=4001, error="No content provided")
        await self.factory.broadcast(client=self.sessionID, event=Intent(intent=payload["intent"], data=payload["content"]))

    async def identify(self, payload):

        if payload.get("authorization") is None:
            return await self.close(code=4004, error="No client authorization")
        if payload["authorization"] not in tokens:
            return await self.close(code=4004, error="Client authorization invalid")

        if payload.get("identifier") is None:
            return await self.close(code=4004, error="No client identifier")
        self.name = payload["identifier"]

        self.authenticated = True
        self.factory.register(self)

    async def dedupe(self, payload):
        if payload.get("scope") is None:
            return await self.close(code=4001, error="No scope provided")
        if payload.get("content") is None:
            return await self.close(code=4001, error="No content provided")
        if payload.get("req") is None:
            return await self.close(code=4001, error="No request id provided")
        dupe = self.factory.dedupe(payload["scope"], payload["content"])
        return await self.send(6, {"duplicate": dupe, "req": payload["req"]})

    async def event(self, payload):
        if payload.get("intent") is None:
            return await self.close(code=4001, error="No intent for event payload")
        print(f"EVENT intent='{payload['intent']}'")

    async def panicked(self, payload):
        with open(f"Cluster {self.identifier} crash.log", "w+") as f:
            f.write(f"{payload.get('error')}\n{payload.get('traceback')}")
        await self.close(4999, "Client exception thrown")
        await _panic(f"Cluster {self.identifier} Has crashed {payload.get('error')}", self.identifier)

    async def ack(self, op):
        await self.send(4, {"recieved": op})

    async def decode(self, payload: bytes):
        try:
            payload = json.loads(payload.decode(encoding="utf-8"))
        except json.decoder.JSONDecodeError:
            return await self.close(code=4001, error="Payload could not be interpreted as JSON")
        if payload.get("op") is None:
            return await self.close(code=4001, error="Payload did not contain an opcode")
        try:
            payload["op"] = int(payload["op"])
        except ValueError:
            return await self.close(code=4002, error="Payload opcode was not an integer")
        if payload.get("op") not in self.ops:
            return await self.close(code=4002, error="Payload opcode was invalid")
        if payload.get("data") is None:
            return await self.close(code=4001, error="No payload data")
        return Message(op=payload["op"], data=payload["data"])

    async def invalid_opcode(self, payload):
        await self.close(code=4003, error="Payload opcode was not acceptable")

    async def send(self, op, payload):
        self.sequence += 1
        data = {
            "op": op,
            "seq": self.sequence,
            "data": payload
        }
        raw = bytes(json.dumps(data), encoding="utf-8")
        self.sendMessage(raw)

    async def close(self, code: int, error: str):
        self.authenticated = False
        self.open = False
        self.sendClose(code=code, reason=error)

    async def onConnect(self, request):
        print(f"\n[GATEWAY]Client connection from [{request.peer}]")

    async def onOpen(self):
        cluster = await self.factory.getCluster(self)
        if not cluster:
            return
        self.identifier = cluster
        self.open = True
        self.sessionID = str(uuid.uuid4())
        self.heartbeatInterval = 30
        hello = {
            "id": self.sessionID,
            "host": platform.node(),
            "heartbeat": self.heartbeatInterval,
            "cluster": cluster,
            "total": config.clusters,
            "shard": config.shards,
        }
        await self.send(0, hello)
        await loop.create_task(self.heartbeat())

    async def onMessage(self, payload, isBinary):
        payload = await self.decode(payload)
        if payload is None:
            return
        if not self.authenticated and payload.op != 1:
            return await self.close(code=4005, error="Not authenticated")
        await self.handlers[payload.op](payload.data)
        if self.open:
            try:
                await self.ack(payload.op)
            except Disconnected:
                pass

    async def onClose(self, isClean, code, reason):
        self.open = False
        self.factory.unregister(self)
        print(
            f"[GATEWAY]Connection closed {'cleanly' if isClean else 'uncleanly'} with code : {code} reason : [{reason}]")
        if code not in (1000, 4007) or not isClean:
            await _panic(f"Cluster {self.identifier} Has closed uncleanly with reason {code} - {reason}", self.identifier)

    async def dispatch(self, client: str, event: Intent):
        if client == self.sessionID:
            return
        await self.send(op=event.op, payload=event.data)

    async def registerHeartbeat(self, payload):
        self.beating = True

    async def heartbeat(self):
        try:
            while self.open:
                if not await self.heartbeatCheck():
                    return
        except asyncio.TimeoutError:
            if self.open:
                await self.close(code=4006, error="No heartbeat recieved")

    async def heartbeatCheck(self):
        async with timeout(self.heartbeatInterval):
            while self.open:
                await asyncio.sleep(1)
                if not self.open:
                    return False
                if self.beating:
                    self.beating = False
                    return True


class Factory(websocket.WebSocketServerFactory):
    def __init__(self):
        super().__init__()
        self.clients = []
        self.registered_dupes = {}
        self.protocol = ServerProtocol

    def register(self, client):
        if client not in self.clients:
            print(
                f"[FACTORY]Registered client {client.name} ({client.sessionID})")
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print(
                f"\n[FACTORY]Unregistered client {client.name} ({client.sessionID})")
            self.clients.remove(client)

    async def broadcast(self, client: str, event: Intent):
        for c in self.clients:
            await c.dispatch(client, event)

    def dedupe(self, scope, hash):
        if not self.registered_dupes.get(scope):
            self.registered_dupes[scope] = {}
        if self.registered_dupes[scope].get(hash) is None:
            self.registered_dupes[scope][hash] = True
            return False
        return True

    async def getCluster(self, client):
        if len(self.clients) == config.clusters:
            await client.close(4007, "Too many clusters")
            return
        return [i for i in alphabet[:config.clusters] if i not in [client.identifier for client in self.clients]][0]


loop = asyncio.get_event_loop()
coro = loop.create_server(Factory(), '0.0.0.0', 9000)
server = loop.run_until_complete(coro)

try:
    print("Running")
    loop.run_forever()
except KeyboardInterrupt:
    print("Exiting on CTRL+C")
finally:
    server.close()
    loop.close()
