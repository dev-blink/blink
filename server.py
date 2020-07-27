from autobahn.asyncio import websocket
import json
import uuid
import platform
import asyncio
from async_timeout import timeout
import config

tokens = config.gatewayauth
loop = asyncio.get_event_loop()


class Message:
    def __init__(self,op:int,data:dict):
        self.op = op
        self.data = data


class Intent:
    def __init__(self,intent:str,data:dict):
        self.op = 3
        self.intent = intent.upper()
        self.data = {
            "intent":self.intent,
        }
        self.data.update(data)


class ServerProtocol(websocket.WebSocketServerProtocol):
    def __init__(self):
        super().__init__()
        self.sequence = 0
        self.authenticated = False
        self.open=False
        self.ops = [0,1,2,3,4,5]
        self.beating=False
        self.handlers={
            0:self.invalid_opcode,
            2:self.registerHeartbeat,
            1:self.identify,
            3:self.event,
            4:self.invalid_opcode,
            5:self.broadcast,
        }

    async def broadcast(self,payload):
        if payload.get("intent") is None:
            return await self.close(code=4001,error="No intent provided")
        if payload.get("content") is None:
            return await self.close(code=4001,error="No content provided")
        await self.factory.broadcast(client=self.sessionID,event=Intent(intent=payload["intent"],data=payload["content"]))

    async def identify(self,payload):

        if payload.get("authorization") is None:
            return await self.close(code=4004,error="No client authorization")
        if payload["authorization"] not in tokens:
            return await self.close(code=4004,error="Client authorization invalid")

        if payload.get("identifier") is None:
            return await self.close(code=4004,error="No client identifier")
        self.name = payload["identifier"]

        self.authenticated=True
        self.factory.register(self)

    async def event(self,payload):
        if payload.get("intent") is None:
            return await self.close(code=4001,error="No intent for event payload")
        print(f"EVENT intent='{payload['intent']}'")

    async def ack(self,op):
        await self.send(4,{"recieved":op})

    async def decode(self,payload:bytes):
        try:
            payload = json.loads(payload.decode(encoding="utf-8"))
        except json.decoder.JSONDecodeError:
            return await self.close(code=4001,error="Payload could not be interpreted as JSON")
        if payload.get("op") is None:
            return await self.close(code=4001,error="Payload did not contain an opcode")
        try:
            payload["op"] = int(payload["op"])
        except ValueError:
            return await self.close(code=4002,error="Payload opcode was not an integer")
        if payload.get("op") not in self.ops:
            return await self.close(code=4002,error="Payload opcode was invalid")
        if payload.get("data") is None:
            return await self.close(code=4001,error="No payload data")
        return Message(op=payload["op"],data=payload["data"])

    async def invalid_opcode(self,payload):
        await self.close(code=4003,error="Payload opcode was incorrect")

    async def send(self,op,payload):
        self.sequence +=1
        data = {
            "op":op,
            "seq":self.sequence,
            "data":payload
        }
        raw = bytes(json.dumps(data),encoding="utf-8")
        self.sendMessage(raw)

    async def close(self,code:int,error:str):
        self.authenticated=False
        self.open=False
        self.sendClose(code=code,reason=error)

    async def onConnect(self,request):
        print(f"\n[GATEWAY]Client connection from [{request.peer}]")

    async def onOpen(self):
        self.open=True
        self.sessionID = str(uuid.uuid4())
        self.heartbeatInterval = 30
        hello = {
            "id":self.sessionID,
            "host":platform.node(),
            "heartbeat":self.heartbeatInterval,
        }
        await self.send(0,hello)
        await loop.create_task(self.heartbeat())

    async def onMessage(self,payload,isBinary):
        payload = await self.decode(payload)
        if payload is None:
            return
        if not self.authenticated and payload.op !=1:
            return await self.close(code=4005,error="Not authenticated")
        await self.handlers[payload.op](payload.data)
        if self.open:
            await self.ack(payload.op)

    async def onClose(self,isClean,code,reason):
        self.open=False
        self.factory.unregister(self)
        print(f"[GATEWAY]Connection closed {'cleanly' if isClean else 'uncleanly'} with code : {code} reason : [{reason}]")

    async def dispatch(self,client:str,event:Intent):
        if client == self.sessionID:
            return
        await self.send(op=event.op,payload=event.data)

    async def registerHeartbeat(self,payload):
        self.beating=True

    async def heartbeat(self):
        try:
            while self.open:
                if not await self.heartbeatCheck():
                    return
        except asyncio.TimeoutError:
            if self.open:
                await self.close(code=4006,error="No heartbeat recieved")

    async def heartbeatCheck(self):
        async with timeout(self.heartbeatInterval):
            while self.open:
                await asyncio.sleep(1)
                if not self.open:
                    return False
                if self.beating:
                    self.beating=False
                    return True


class Factory(websocket.WebSocketServerFactory):
    def __init__(self):
        super().__init__()
        self.clients = []
        self.protocol = ServerProtocol

    def register(self, client):
        if client not in self.clients:
            print(f"[FACTORY]Registered client {client.name} ({client.sessionID})")
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print(f"\n[FACTORY]Unregistered client {client.name} ({client.sessionID})")
            self.clients.remove(client)

    async def broadcast(self, client:str,event:Intent):
        for c in self.clients:
            await c.dispatch(client,event)


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