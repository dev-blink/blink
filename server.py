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
from blink import CacheDict

tokens = config.gatewayauth # list of tokens that clients are allowed to authenticate with
loop = asyncio.get_event_loop()


async def _panic(message: str, cluster: str):
    """Send a push notification on an unclean disconnect"""
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
    """Custom class to abstract websocket messages"""
    def __init__(self, op: int, data: dict):
        self.op = op
        self.data = data


class Intent(Message):
    """Class to abstract sending events to clusters"""
    def __init__(self, intent: str, data: dict):
        super().__init__(op=3, data=data)
        self.intent = intent.upper()
        self.data['intent'] = self.intent


class ServerProtocol(websocket.WebSocketServerProtocol):
    """Main class that handles a single cluster connection"""
    def __init__(self):
        super().__init__()
        self.sequence = 0
        self.authenticated = False
        self.open = False
        self.ops = [0, 1, 2, 3, 4, 5, 6, 7] # List of valid opcodes
        self.beating = False
        self.handlers = {
            0: self.invalid_opcode,
            1: self.identify,
            2: self.registerHeartbeat,
            3: self.event,
            4: self.invalid_opcode,
            5: self.broadcast,
            6: self.dedupe,
            7: self.panicked,
        }

    async def broadcast(self, payload):
        """Send a message to all other clusters connected"""
        if payload.get("intent") is None:
            return await self.close(code=4001, error="No intent provided")
        if payload.get("content") is None:
            return await self.close(code=4001, error="No content provided")
        await self.factory.broadcast(client=self.sessionID, event=Intent(intent=payload["intent"], data=payload["content"]))

    async def identify(self, payload):
        """Handle clusters initial connection"""
        if payload.get("authorization") is None:
            return await self.close(code=4004, error="No client authorization")
        if payload["authorization"] not in tokens:
            return await self.close(code=4004, error="Client authorization invalid")

        if payload.get("identifier") is None:
            return await self.close(code=4004, error="No client identifier")
        if payload["identifier"] != self.identifier:
            return await self.close(code=4004, error="Identifier does not match")
        self.name = payload["identifier"] # For factory

        self.authenticated = True
        self.factory.register(self)

    async def dedupe(self, payload):
        """Handle a deduplication request"""
        if payload.get("scope") is None:
            return await self.close(code=4001, error="No scope provided")
        if payload.get("content") is None:
            return await self.close(code=4001, error="No content provided")
        if payload.get("req") is None:
            return await self.close(code=4001, error="No request id provided")
        dupe = self.factory.dedupe(payload["scope"], payload["content"])
        return await self.send(6, {"duplicate": dupe, "req": payload["req"]})

    async def event(self, payload): # Skeleton code, event opcode is not used
        """Handles a cluster sending an event"""
        if payload.get("intent") is None:
            return await self.close(code=4001, error="No intent for event payload")
        print(f"EVENT intent='{payload['intent']}'")

    async def panicked(self, payload):
        """A cluster has panicked, save its log and close it"""
        t = datetime.datetime.utcnow()
        with open(f"Cluster {self.identifier} crash at {t.year}-{t.month}-{t.day} {t.hour:02}{t.minute:02}.log", "w+") as f:
            f.write(f"{payload.get('error')}\n{payload.get('traceback')}")
        await self.close(4999, "Client exception thrown")
        await _panic(f"Cluster {self.identifier} Has crashed {payload.get('error')}", self.identifier)

    async def ack(self, op):
        """After every packet is recieved, an 'ack' is sent"""
        await self.send(4, {"recieved": op})

    async def decode(self, payload: bytes):
        """Deserialise a payload into a Message object"""
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
        """
        Fallback function for unknown opcodes
        Called by the handler not the deserialiser
        """
        await self.close(code=4003, error="Payload opcode was not acceptable")

    async def send(self, op, payload):
        """Send data to the clusters websocket and serialise it"""
        self.sequence += 1
        data = {
            "op": op,
            "seq": self.sequence,
            "data": payload
        }
        raw = bytes(json.dumps(data), encoding="utf-8")
        self.sendMessage(raw)

    async def close(self, code: int, error: str):
        """Close the websocket cleanly"""
        self.authenticated = False
        self.open = False
        self.sendClose(code=code, reason=error)

    async def onConnect(self, request):
        print(f"\n[GATEWAY]Client connection from [{request.peer}]")

    async def onOpen(self):
        """Send the hello payload after a cluster connects"""
        cluster = await self.factory.getCluster(self)
        if not cluster:
            return # Abandon hello because cluster pool is full
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
        """Handle a raw message from a cluster"""
        payload = await self.decode(payload)
        if payload is None:
            return
        if not self.authenticated and payload.op != 1:
            # Clusters should not send any payload before they have identified
            return await self.close(code=4005, error="Not authenticated")
        await self.handlers[payload.op](payload.data) # Call handler for opcode sent
        if self.open:
            try:
                await self.ack(payload.op) # Ack payload
            except Disconnected:
                pass

    async def onClose(self, isClean, code, reason):
        """Panic if a cluster didnt close properly"""
        self.open = False
        self.factory.unregister(self)
        print(
            f"[GATEWAY]Connection closed {'cleanly' if isClean else 'uncleanly'} with code : {code} reason : [{reason}]")
        if code not in (1000, 4007) or not isClean:
            await _panic(f"Cluster {self.identifier} Has closed uncleanly with reason {code} - {reason}", self.identifier)

    async def dispatch(self, client: str, event: Intent):
        """
        Used for broadcast, sends a message to the cluster
        Will not send if the current cluster broadcasted it
        """
        if client == self.sessionID:
            return
        await self.send(op=event.op, payload=event.data)

    async def registerHeartbeat(self, payload):
        """Acknowledge a heartbeat"""
        self.beating = True

    async def heartbeat(self):
        """Continually check if a heartbeat has been recieved"""
        try:
            while self.open:
                if not await self.heartbeatCheck():
                    return # Socket was closed
        except asyncio.TimeoutError:
            if self.open:
                await self.close(code=4006, error="No heartbeat recieved")

    async def heartbeatCheck(self):
        """Check if a heartbeat has been reciebed in the last interval"""
        async with timeout(self.heartbeatInterval + 5):
            while self.open:
                await asyncio.sleep(1)
                if not self.open:
                    return False
                if self.beating:
                    self.beating = False
                    return True


class Factory(websocket.WebSocketServerFactory):
    """Factory class to spawn websockets for each cluster"""
    def __init__(self):
        super().__init__()
        self.clients = []
        # This dictionary is not limited in size because it is a 2D dictionary
        # The size limited dictionaries are inside this [scope, size limited dictionary]
        self.registered_dupes = {}
        self.protocol = ServerProtocol # The websocket class to handle each connection

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
        """Send a message to all connected clusters"""
        for c in self.clients:
            await c.dispatch(client, event)

    def dedupe(self, scope, hash):
        """
        Clusters can request that a key be unique across all clusters
        this function will store all keys and return true or false if
        the key is unique or not, keys may not be unique across scopes
        """
        if not self.registered_dupes.get(scope):
            self.registered_dupes[scope] = CacheDict(50_000)
        if self.registered_dupes[scope].get(hash) is None:
            self.registered_dupes[scope][hash] = 1
            return False
        else:
            self.registered_dupes[scope][hash] += 1
            return True

    async def getCluster(self, client):
        """Get an identifier for a cluster"""
        if len(self.clients) == config.clusters:
            await client.close(4007, "Too many clusters")
            return
        # This list comprehension iterates over the alphabet until a letter is found that is not a registered cluster
        # It will return the first letter found
        # The identifiers array is not inline to prevent O(n^2)
        # This code is blocking so we dont have to worry about identifiers being assigned between
        # Therefore the identifiers list will not change and does not need to be recomputed
        identifiers = [client.identifier for client in self.clients]
        return next(i for i in alphabet[:config.clusters] if i not in identifiers)


if __name__ == "__main__":
    # Set up asyncio event loop and run the factory server
    loop = asyncio.get_event_loop()
    coro = loop.create_server(Factory(), '0.0.0.0', 9000)
    server = loop.run_until_complete(coro)

    try:
        print(f"Pool is {config.clusters} clusters with {config.shards} shards each")
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting on CTRL+C")
    finally:
        server.close()
        loop.close()
