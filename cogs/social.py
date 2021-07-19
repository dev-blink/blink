# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import discord
import aiohttp
from discord.ext import commands
import blink
import humanize
import datetime
import uuid
import asyncio
import re
import blinksecrets as secrets
from async_timeout import timeout
import config
# CREATE TABLE social (id bigint PRIMARY KEY, hugs TEXT ARRAY, kisses TEXT ARRAY, relation bigint, ship TEXT, blocked bigint ARRAY)
# CREATE TABLE ships (id TEXT PRIMARY KEY,captain bigint, partner bigint,name TEXT,customtext TEXT,colour bigint,icon TEXT,timestamp bigint)
URLREGEX = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")


async def api(route, method):
    try:
        async with timeout(5):
            async with aiohttp.ClientSession() as cs:
                async with cs.request(method=method, url=f"{config.api}{route}", headers={"Authorization": secrets.api}) as res:
                    if res.status == 200:
                        return (await res.json()).get("url")
                    else:
                        return f"https://dummyimage.com/1024x256/000000/f5a6b9.png&text=contact+support+-+{res.status}"
    except asyncio.TimeoutError:
        return "https://dummyimage.com/1024x256/000000/f5a6b9.png&text=contact+support+-+TIMEOUT"


class _Users(discord.AllowedMentions):
    def __init__(self):
        super().__init__(everyone=False, users=True, roles=False)


class ShipStats:
    def __init__(self, hugs: int, kisses: int, xp: str, age: str):
        self.hugs = hugs
        self.kisses = kisses
        self.xp = xp
        self.age = age


class Ship:
    def __init__(self, uuid: str, db, bot):
        self.id = uuid
        self.db = db
        self.bot = bot
        self.cache = self.bot.cache_or_create(
            f"social-ship-{self.id}", "SELECT * FROM ships WHERE id = $1", (self.id,))

    async def gen_thumbnail(self):
        return await api(f"/social/images/ship/{self.colour:06}", "GET")

    async def __aenter__(self):
        async with self.cache as cache:
            if cache.value:
                self.exists = True
                self.res = cache.value
                self.format()
            else:
                self.exists = False
        return self

    async def __aexit__(self, error, error_type, traceback):
        pass

    def format(self):
        self.captain = self.res.get('captain')
        self.partner = self.res.get('partner')
        self.name = self.res.get('name')
        self.description = self.res.get('customtext')
        self.colour = self.res.get('colour')
        self.icon = self.res.get('icon')
        self.created = datetime.datetime.fromtimestamp(
            self.res.get('timestamp'))

    async def create(self, captain: int, partner: int, name: str, description: str = "No description", colour: int = 16099001, icon: str = "https://cdn.blinkbot.me/assets/ship.png"):
        await self.db.execute("INSERT INTO ships VALUES ($1,$2,$3,$4,$5,$6,$7,$8)", self.id, captain, partner, name, description, colour, icon, int(datetime.datetime.utcnow().timestamp()))
        await self.cache.bot_invalidate(self.bot)
        async with self.cache as cache:
            self.res = cache.value
        self.format()

    async def gen_stats(self) -> ShipStats:
        async with User(self.captain, self.db, self.bot) as captain:
            captain_hugs = (await captain.decompile(scope="hugs", recipient=self.partner))[1]
            captain_kisses = (await captain.decompile(scope="kisses", recipient=self.partner))[1]

            if captain_hugs is None:
                captain_hugs = 0
            if captain_kisses is None:
                captain_kisses = 0

        async with User(self.partner, self.db, self.bot) as partner:
            partner_hugs = (await partner.decompile(scope="hugs", recipient=self.captain))[1]
            partner_kisses = (await partner.decompile(scope="kisses", recipient=self.captain))[1]

            if partner_hugs is None:
                partner_hugs = 0
            if partner_kisses is None:
                partner_kisses = 0

        total_hugs = partner_hugs + captain_hugs
        total_kisses = partner_kisses + captain_kisses

        timestamp = datetime.datetime.utcnow().timestamp().__int__() - \
            self.created.timestamp()
        days = datetime.timedelta(seconds=timestamp).days
        age = humanize.naturaldelta(timestamp)
        xp = humanize.intword(int((days ** 2) * 50) +
                              (total_hugs + total_kisses) * 37)

        return ShipStats(hugs=total_hugs, kisses=total_kisses, xp=xp, age=age)

    async def to_embed(self):
        stats = await self.gen_stats()
        embed = discord.Embed(colour=self.colour, description=self.description)
        embed.add_field(name="**Captain**", value=f"<@{self.captain}>")
        embed.add_field(name="**Partner**", value=f"<@{self.partner}>")
        embed.add_field(name="**XP**", value=f"{stats.xp} XP")
        embed.add_field(
            name="**Counters**", value=f"{stats.hugs} Hug{'s' if stats.hugs != 1 else ''} | {stats.kisses} Kiss{'es' if stats.kisses != 1 else ''}", inline=False)
        embed.add_field(name="**Ship Age**", value=stats.age, inline=False)
        embed.set_author(name=self.name, icon_url=self.icon)
        embed.set_thumbnail(url=await self.gen_thumbnail())
        return embed

    async def modify(self, scope, data):
        await self.db.execute(f"UPDATE ships SET {scope}=$1 WHERE id=$2", data, self.id)
        await self.cache.bot_invalidate(self.bot)

    async def sink(self):
        await self.db.execute("DELETE FROM ships WHERE id=$1", self.id)
        await self.cache.bot_invalidate(self.bot)


class Action:
    def __init__(self, success: bool, reason: str = None, count: int = None):
        self.success = success
        self.count = count
        self.reason = reason

    def translate(self):
        translations = {
            "userblocked": "You have blocked this user.",
            "blocked": "You have been blocked by this user.",
            "usertaken": "You have a ship.",
            "taken": "That user has a ship.",
        }
        return translations[self.reason]


class ElegibilityReason:
    def __init__(self, elegible: bool, reason: str = None):
        self.elegible = elegible
        self.reason = reason


class User:
    def __init__(self, id: int, db, bot):
        self.user = id
        self.db = db
        self.bot = bot
        self.cache = self.bot.cache_or_create(
            f"social-user-{self.user}", "SELECT * FROM social WHERE id = $1", (self.user,))

    def format(self):
        self.hugs = self.res.get("hugs")
        self.kisses = self.res.get("kisses")
        self.relation = self.res.get("relation")
        self.ship = self.res.get("ship")
        self.blocked = self.res.get("blocked")

    async def __aenter__(self):
        async with self.cache as cache:
            if not cache.value:
                await self.setup()
                await cache.update()
            self.res = cache.value
            self.format()

        self.taken = (True if self.relation != 0 else False)
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, error, error_type, traceback):
        await self.session.close()

    async def setup(self):
        # id, hugs, kisses, relationship, ship, blocked
        await self.db.execute("INSERT INTO social VALUES ($1,$2,$3,$4,$5,$6)", self.user, [], [], 0, "nul", [])
        await self.cache.bot_invalidate(self.bot)

    async def elegible(self, scope: str, recipient) -> ElegibilityReason:
        if self.relation == recipient.user:
            return ElegibilityReason(True)
        res = recipient

        if recipient.user in self.blocked:
            return ElegibilityReason(False, reason="userblocked")
        if self.user in res.blocked:
            return ElegibilityReason(False, reason="blocked")

        if scope == "hug":
            return ElegibilityReason(True)
        elif scope == "kiss" or "ship":
            if self.taken:
                return ElegibilityReason(False, "usertaken")
            if res.taken:
                return ElegibilityReason(False, "taken")
            return ElegibilityReason(True)

    async def block(self, recipient):
        blocked = self.blocked
        if recipient in blocked:
            return "User already blocked."
        blocked.append(recipient)
        await self.db.execute("UPDATE social SET blocked = $1 WHERE id=$2", blocked, self.user)
        await self.cache.bot_invalidate(self.bot)
        return "Success"

    async def unblock(self, recipient):
        blocked = self.blocked
        if recipient not in blocked:
            return "User not blocked."
        blocked.remove(recipient)
        await self.db.execute("UPDATE social SET blocked = $1 WHERE id=$2", blocked, self.user)
        await self.cache.bot_invalidate(self.bot)
        return "Success"

    async def decompile(self, scope: str, recipient: int):
        action = self.res.get(scope)
        if action == []:
            entry = id = count = index = None
        for entry in action:
            id, count = tuple(entry.split(":"))
            if int(id) == recipient:
                index = action.index(entry)
                break
            else:
                entry = id = count = index = None
        if count:
            count = int(count)
        if id:
            id = int(id)
        return entry, count, index, action

    async def hug(self, recipient: int) -> Action:
        async with User(recipient, self.db, self.bot) as recp:
            check = await self.elegible(scope="hug", recipient=recp)
            if not check.elegible:
                return Action(success=False, reason=check.reason)
            rentry, rcount, rindex, rhugs = await recp.decompile(scope="hugs", recipient=self.user)
            if rcount is None:
                rcount = 0

        entry, count, index, hugs = await self.decompile(scope="hugs", recipient=recipient)

        if index is None:
            await self.db.execute("UPDATE social SET hugs=$1 WHERE id=$2", hugs + [f"{recipient}:1"], self.user)
            await self.cache.bot_invalidate(self.bot)
            count = 1
        else:
            count = int(count) + 1
            hugs.pop(index)
            hugs.append(f"{recipient}:{count}")
            await self.db.execute("UPDATE social SET hugs=$1 WHERE id=$2", hugs, self.user)
            await self.cache.bot_invalidate(self.bot)
        return Action(success=True, count=count + rcount)

    async def kiss(self, recipient: int) -> Action:
        async with User(recipient, self.db, self.bot) as recp:
            check = await self.elegible(scope="kiss", recipient=recp)
            if not check.elegible:
                return Action(success=False, reason=check.reason)
            rentry, rcount, rindex, rhugs = await recp.decompile(scope="kisses", recipient=self.user)
            if rcount is None:
                rcount = 0

        entry, count, index, kisses = await self.decompile(scope="kisses", recipient=recipient)

        if index is None:
            await self.db.execute("UPDATE social SET kisses=$1 WHERE id=$2", kisses + [f"{recipient}:1"], self.user)
            await self.cache.bot_invalidate(self.bot)
            count = 1
        else:
            count = int(count) + 1
            kisses.pop(index)
            kisses.append(f"{recipient}:{count}")
            await self.db.execute("UPDATE social SET kisses=$1 WHERE id=$2", kisses, self.user)
            await self.cache.bot_invalidate(self.bot)
        return Action(success=True, count=count + rcount)

    async def set_ship(self, id: str, relation: int):
        await self.db.execute("UPDATE social SET ship = $1 WHERE id=$2", id, self.user)
        await self.db.execute("UPDATE social SET relation =$1 WHERE id=$2", relation, self.user)
        await self.cache.bot_invalidate(self.bot)

    async def sink_ship(self):
        await self.db.execute("UPDATE social SET ship =$1 WHERE id =$2", "nul", self.user)
        await self.db.execute("UPDATE social SET relation =$1 WHERE id=$2", 0, self.user)
        await self.cache.bot_invalidate(self.bot)


class Social(blink.Cog):

    async def gen_kiss(self):
        return await api("/social/images/kiss/", "GET")

    async def gen_hug(self):
        return await api("/social/images/hug/", "GET")

    @commands.group(name="blocked", invoke_without_command=True)
    async def blocked(self, ctx):
        """Manage users blocked from using social commands on you"""
        embed = discord.Embed(title="Social Blocking", colour=self.bot.colour)
        embed.description = f"Usage:\n{ctx.prefix}blocked list : show blocked users\n{ctx.prefix}blocked add : show block a user\n{ctx.prefix}blocked remove : unblock a user"
        await ctx.send(embed=embed)

    @blocked.command(name="add")
    async def block(self, ctx, recipient: discord.User):
        """Block a user from using social commands on you"""
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            return await ctx.send(await user.block(recipient.id))

    @blocked.command(name="remove", aliases=["delete"])
    async def unblock(self, ctx, recipient: discord.User):
        """Unblock a user from using social commands on you"""
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            return await ctx.send(await user.unblock(recipient.id))

    @blocked.command(name="list", aliases=["show"])
    @commands.bot_has_permissions(embed_links=True)
    async def show_blocked(self, ctx):
        """Show your blocked users"""
        format = []
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            blocked = user.blocked
        for user in blocked:
            name = self.bot.get_user(user)
            if name is None:
                format.append(f"unknown#0000 ({user})")
            else:
                format.append(f"{name} ({user})")
        embed = discord.Embed(colour=self.bot.colour, description="\n".join(
            format), title="Blocked users")
        if embed.description == "":
            embed.description = "No one here."
        return await ctx.send(embed=embed)

    @commands.command(name="hug")
    @commands.bot_has_permissions(embed_links=True)
    async def hug(self, ctx, *, member: discord.Member):
        """Hug someone"""
        if member == ctx.author:
            return await ctx.send("You cant do that :(")
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            res = await user.hug(member.id)
        if res.success:
            embed = discord.Embed(
                title=f"{ctx.author.display_name} hugs {member.display_name}", colour=self.bot.colour)
            embed.set_image(url=await self.gen_hug())
            embed.set_footer(
                text=f"That's their {blink.ordinal(res.count)} hug!")
        else:
            embed = discord.Embed(
                title=f":x: {res.translate()}", colour=discord.Colour.red())
        return await ctx.send(embed=embed)

    @commands.command(name="kiss")
    @commands.bot_has_permissions(embed_links=True)
    async def kiss(self, ctx, *, member: discord.Member):
        """Kiss someone"""
        if member == ctx.author:
            return await ctx.send("You cant do that :(")
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            res = await user.kiss(member.id)
        if res.success:
            embed = discord.Embed(
                title=f"{ctx.author.display_name} kisses {member.display_name}", colour=self.bot.colour)
            embed.set_image(url=await self.gen_kiss())
            embed.set_footer(
                text=f"That's their {blink.ordinal(res.count)} kiss!")
        else:
            embed = discord.Embed(
                title=f":x: {res.translate()}", colour=discord.Colour.red())
        return await ctx.send(embed=embed)

    @commands.group(name="ship", invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ship(self, ctx, *, member: discord.Member = None):
        """Show and manage your ship"""
        if member and (member == ctx.author or member.bot):
            return await ctx.send("No...")
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            id = user.ship
            if id == "nul":
                if not member:
                    return await ctx.send("You do not have a ship.")
                else:
                    async with User(member.id, self.bot.DB, self.bot) as memb:
                        check = await user.elegible(scope="ship", recipient=memb)
                    if not check.elegible:
                        return await ctx.send(embed=discord.Embed(title=f":x: {Action(success=False,reason=check.reason).translate()}", colour=discord.Colour.red()))
                    if await self._new_ship(ctx.author.id, memb.user, ctx) is False:
                        return await ctx.send(f"<@{ctx.author.id}> Your ship has not been created, either due to a time-out or the partner denied.")
                    return
            if member:
                return await ctx.send("You already have a ship.")
        async with Ship(id, self.bot.DB, self.bot) as ship:
            return await ctx.send(embed=await ship.to_embed())

    @ship.command(name="help")
    @commands.bot_has_permissions(embed_links=True)
    async def ship_help(self, ctx):
        """Show ship help"""
        return await ctx.send_help(ctx.command.parent)

    @ship.command(name="name", aliases=["title"])
    async def ship_rename(self, ctx, *, name: str):
        """Rename your ship"""
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            id = user.ship
        async with Ship(id, self.bot.DB, self.bot) as ship:
            if not ship.exists:
                return await ctx.send("You do not have a ship")
            await ship.modify(scope="name", data=name)
        return await ctx.send(f"Your ship is now called `{name}`!")

    @ship.command(name="description", aliases=["desc", "text"])
    async def ship_change_description(self, ctx, *, text: str):
        """Change your ship's description"""
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            id = user.ship
        async with Ship(id, self.bot.DB, self.bot) as ship:
            if not ship.exists:
                return await ctx.send("You do not have a ship")
            await ship.modify(scope="customtext", data=text)
        return await ctx.send(f"Your ship description is `{text}`!")

    @ship.command(name="colour", aliases=["color"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ship_recolour(self, ctx, colour: discord.Colour):
        """Change your ship's colour"""
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            id = user.ship
        async with Ship(id, self.bot.DB, self.bot) as ship:
            if not ship.exists:
                return await ctx.send("You do not have a ship")
            await ship.modify(scope="colour", data=colour.value)
        return await ctx.send(embed=discord.Embed(colour=colour, title="This is now your ship's colour", description="**There may be a delay viewing your ship after updating the colour**"))

    @ship.command(name="icon", aliases=["img", "image", "picture"])
    async def ship_change_icon(self, ctx, *, icon: str = None):
        """Change your ship's icon"""

        if not icon:
            if ctx.message.attachments:
                if ctx.message.attachments[0].height:
                    icon = ctx.message.attachments[0].url

        if not icon:
            async with User(ctx.author.id, self.bot.DB, self.bot) as user:
                id = user.ship
            async with Ship(id, self.bot.DB, self.bot) as ship:
                if not ship.exists:
                    return await ctx.send("You do not have a ship")
                return await ctx.send(embed=discord.Embed(title="This is your ship's icon", colour=self.bot.colour).set_image(url=ship.icon))

        if not URLREGEX.match(icon):
            return await ctx.send("That doesnt look like a url to me... \nex (https://example.com/image.png)")
        async with User(ctx.author.id, self.bot.DB, self.bot) as user:
            id = user.ship
        async with Ship(id, self.bot.DB, self.bot) as ship:
            if not ship.exists:
                return await ctx.send("You do not have a ship")
            await ship.modify(scope="icon", data=icon)
        return await ctx.send(embed=discord.Embed(title="This is now your ship's icon", colour=self.bot.colour).set_image(url=icon))

    @ship.command(name="debug", hidden=True)
    @commands.is_owner()
    async def ship_debug(self, ctx, *, member: discord.User = None):
        if not member:
            member = ctx.author
        async with User(member.id, self.bot.DB, self.bot) as user:
            async with Ship(user.ship, self.bot.DB, self.bot) as ship:
                embed = discord.Embed(title=ship.id, colour=self.bot.colour)
                if ship.exists:
                    embed.description = f"Captain : {ship.captain}\nPartner : {ship.partner}\nName : {ship.name}\nDescription : {ship.description}\nColour : {ship.colour}\nIcon : [Link]({ship.icon} \"{ship.icon}\")\nCreated : {ship.created}"
                else:
                    embed.description = "Doesn't exist"
                return await ctx.send(embed=embed)

    @ship.command(name="sink", aliases=["stop", "delete", "cancel"])
    async def ship_sink(self, ctx):
        """Delete your ship"""

        def check(reaction, user):
            if str(reaction.emoji) not in ["\U00002714", "\U0000274c"]:
                return False
            return user == ctx.author

        async with User(ctx.author.id, self.bot.DB, self.bot) as c:
            async with Ship(c.ship, self.bot.DB, self.bot) as ship:
                if not ship.exists:
                    return await ctx.send("You do not have a ship.")
                m = await ctx.send("Are you sure?")
                await m.add_reaction("\U00002714")
                await m.add_reaction("\U0000274c")

                try:
                    reaction = (await self.bot.wait_for('reaction_add', timeout=10, check=check))[0]
                except asyncio.TimeoutError:
                    return await ctx.send(f"{ctx.author.mention} Timed out waiting for response. Sinking cancelled.")
                else:
                    if str(reaction.emoji) != "\U00002714":
                        return await ctx.send("Cancelled")
                await ship.sink()
            await c.sink_ship()

            async with User(c.relation, self.bot.DB, self.bot) as p:
                await p.sink_ship()
            return await ctx.send("Your ship has sunk.")

    async def _new_ship(self, captain: int, partner: int, ctx: commands.Context):
        try:
            def is_captain(m):
                return m.author.id == captain

            def is_partner(m):
                return m.author.id == partner

            await ctx.send(f"<@{partner}> would you like to create a ship with <@{captain}> ? (type yes or no)", allowed_mentions=_Users())
            message = await self.bot.wait_for('message', check=is_partner, timeout=60)
            if not any(m in message.content.lower() for m in ['yes', 'yea', 'ok', 'yeah', 'sure']):
                return

            await ctx.send(f"<@{captain}> what should the ship be called?", allowed_mentions=_Users())
            message = await self.bot.wait_for('message', check=is_captain, timeout=60)

            name = message.content or "no name"

            await ctx.send(f"<@{captain}> what should the ship description be?", allowed_mentions=_Users())
            message = await self.bot.wait_for('message', check=is_captain, timeout=60)

            description = message.content or "no description"

            await ctx.send(f"<@{captain}> what should the ship icon be? (a link to an image is needed)", allowed_mentions=_Users())
            message = await self.bot.wait_for('message', check=is_captain, timeout=60)

            if not message.content:
                if message.attachments:
                    if message.attachments[0].height:
                        icon = message.attachments[0].url
            elif URLREGEX.match(message.content):
                icon = message.content
            else:
                await ctx.send("That doesnt look like a valid url, resorting to default \n ex (https://example.com/image.png)")
                icon = "https://cdn.blinkbot.me/assets/ship.png"

            await ctx.send(f"<@{captain}> what should the ship colour be? (send **just** a hex code)", allowed_mentions=_Users())
            message = await self.bot.wait_for('message', check=is_captain, timeout=60)
            colour = 16099001
            if message.content:
                content = "#" + \
                    message.content if not message.content.startswith(
                        ("#", "0x")) else message.content
                if len(content) == 6:
                    try:
                        colour = (await commands.converter.ColourConverter().convert(None, content)).value
                    except commands.BadArgument:
                        await ctx.send("unable to determine a colour, using default colour")

            else:
                await ctx.send("unable to determine a colour, using default colour")

        except asyncio.TimeoutError:
            return False

        id = str(uuid.uuid4())
        async with Ship(id, self.bot.DB, self.bot) as ship:
            await ship.create(captain=captain, partner=partner, name=name, description=description, colour=colour, icon=icon)

        async with User(captain, self.bot.DB, self.bot) as c:
            await c.set_ship(id=id, relation=partner)

        async with User(partner, self.bot.DB, self.bot) as p:
            await p.set_ship(id=id, relation=captain)
        return await ctx.send(embed=await ship.to_embed())


def setup(bot):
    bot.add_cog(Social(bot, "social"))
