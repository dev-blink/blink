# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import json
from random import Random as RAND
import discord
from discord.errors import InvalidArgument
from discord.ext import commands
from math import floor as f
import functools
import asyncio
from aiohttp import ClientSession
import time
from asyncpg.pool import Pool
from collections import OrderedDict
from typing import Callable, List
import re


urlregex = re.compile(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+")


class Timer:
    """Context manager that will store time since created since initialised"""
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        pass

    @property
    def time(self):
        return time.perf_counter() - self.start


class DBCache():
    def __init__(self, db: Pool, identifier: str, statement: str, values: tuple):
        self.db = db # Pooled database connection
        self.identifier = identifier # The unique ID of the cache
        self.statement = statement # SQL Query to update cache
        self.values = values # Values to use to query
        self._value = None # Internal value
        self._current = False # If data is current

    def __repr__(self):
        return f"<In memory DB cache - {self.statement}, {self.values}>"

    async def _set_value(self):
        self._value = await self.db.fetchrow(self.statement, *self.values)
        self._current = True

    async def __aenter__(self):
        if not self._current: # Update when accessed from a context manager
            await self.update()
        return self

    async def __aexit__(*args):
        return

    @property
    def value(self):
        return self._value

    def invalidate(self):
        self._current = False

    async def update(self):
        self.invalidate()
        await self._set_value()

    async def bot_invalidate(self, bot):
        """Tell other clusters that this cache has been modified"""
        await bot.invalidate_cache(self.identifier)


def fancytext(name, term, checks: List[Callable]):
    """"""
    eng = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
           'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    conversion = [
        ["𝔞", "𝔟", "𝔠", "𝔡", "𝔢", "𝔣", "𝔤", "𝔥", "𝔦", "𝔧", "𝔨", "𝔩", "𝔪", "𝔫", "𝔬",
            "𝔭", "𝔮", "𝔯", "𝔰", "𝔱", "𝔲", "𝔳", "𝔴", "𝔵", "𝔶", "𝔷"],  # ascii + 119997
        ['𝖆', '𝖇', '𝖈', '𝖉', '𝖊', '𝖋', '𝖌', '𝖍', '𝖎', '𝖏', '𝖐', '𝖑', '𝖒', '𝖓', '𝖔',
            '𝖕', '𝖖', '𝖗', '𝖘', '𝖙', '𝖚', '𝖛', '𝖜', '𝖝', '𝖞', '𝖟'],  # ascii + 120101
        ['𝓪', '𝓫', '𝓬', '𝓭', '𝓮', '𝓯', '𝓰', '𝓱', '𝓲', '𝓳', '𝓴', '𝓵', '𝓶', '𝓷', '𝓸',
            '𝓹', '𝓺', '𝓻', '𝓼', '𝓽', '𝓾', '𝓿', '𝔀', '𝔁', '𝔂', '𝔃'],  # ascii + 119945
        ['𝒶', '𝒷', '𝒸', '𝒹', '𝑒', '𝒻', '𝑔', '𝒽', '𝒾', '𝒿', '𝓀', '𝓁', '𝓂', '𝓃', '𝑜', '𝓅',
            '𝓆', '𝓇', '𝓈', '𝓉', '𝓊', '𝓋', '𝓌', '𝓍', '𝓎', '𝓏']  # ascii + 119893 or 119789
    ]

    for func in checks: # Run the checks before doing expensive computation
        if func(name, term):
            return True

    for alphabet in conversion: # Support fancy text generator by replacing a-z with 'fancytext'
        check = term
        for x in range(0, 26):
            check = check.replace(eng[x], alphabet[x])
        for func in checks:
            if func(name, term):
                return True
    return False


async def searchrole(roles: list, term: str) -> discord.Role:
    """Custom role search for discord.py"""
    loop = asyncio.get_event_loop()

    checks = [
        (lambda name, term: name == term),
        (lambda name, term: name.startswith(term)),
        (lambda name, term: term in name)
    ]

    for r in roles: # These must be run in executor because they are expensive to compute and would block the event loop
        if await loop.run_in_executor(None, functools.partial(fancytext, r.name.lower(), term.lower(), checks)):
            return r


def ordinal(n: int):
    """Turns an int into its ordinal (1 -> 1st)"""
    return f"{n}{'tsnrhtdd'[(f(n/10)%10!=1)*(n%10<4)*n%10::4]}"  # noqa: E226,E228
    # (f(n/10)%10!=1)*(n%10<4)*n%10 gives 1->1, 2->2, 3->3, n->0
    # the string 'tsnrhtdd' is then subscripted [x::4]
    # this returns the letter at index x and x+5


class Config(): # Deprecated configuration
    @classmethod
    def newguilds(self):
        return int(702201857606549646)

    @classmethod
    def errors(self):
        return 702201821615358004

    @classmethod
    def startup(self):
        return 702705386557276271

    @classmethod
    def warns(self):
        return 722131357136060507


def prettydelta(seconds):
    """Function to turn seconds into days minutes hours"""
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%dd %dh %dm %ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh %dm %ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm %ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds,)


def prand(spice: float, uid: int, start: int, stop: int, inverse: bool = False):
    """Baised random"""
    b = uid * spice
    rng = RAND(x=(b))
    return rng.randint(start, stop)


# MUSIC ERRORS
class NoChannelProvided(commands.CommandError):
    """Error raised when no suitable voice channel was supplied."""
    pass


class IncorrectChannelError(commands.CommandError):
    """Error raised when commands are issued outside of the players session channel."""
    pass


class SilentWarning(Exception):
    """Error for backing out of tasks with a warning"""
    pass


class Cog(commands.Cog):
    def __init__(self, bot, identifier: str):
        self.bot = bot
        self.identifier = identifier
        bot._cogs.register(self, self.identifier) # Allow easy access during runtime code evaluatino

    def cog_unload(self): # Called when a cog is unloaded
        self.bot._cogs.unregister(self.identifier)
        if hasattr(self, "session") and isinstance(self.session, ClientSession):
            self.bot.loop.create_task(self.session.close())


class CacheDict(OrderedDict):
    'Limit size, evicting the least recently looked-up key when full'
    # from https://docs.python.org/3/library/collections.html#collections.OrderedDict#OrderedDict

    def __init__(self, maxsize=128, *args, **kwds):
        self.maxsize = maxsize
        super().__init__(*args, **kwds)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]


class Ctx(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.guild and hasattr(self.bot, "wavelink"):
            self.player = self.bot.wavelink.players.get(self.guild.id) # Deprecated music player

    def __repr__(self):
        return f"<Blink context, author={self.author}, guild={self.guild}, message={self.message}>"

    @property
    def clean_prefix(self):
        """Returns the prefix used and will parse a id into a username"""
        user = self.guild.me if self.guild else self.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace('\\', r'\\'), self.prefix)

    async def send(self, *args, **kwargs):
        if self.message.reference: # Reference message that the original message referenced when responding
            self.message.reference.fail_if_not_exists = False
            if not kwargs.get("reference"):
                kwargs["reference"] = self.message.reference
                kwargs["mention_author"] = False
        return await super().send(*args, **kwargs)


class CogStorage:
    """Dummy object used as an attribute to store each individual cog"""
    def __dir__(self):
        return sorted([a for a in super().__dir__() if not ((a.startswith("__") and a.endswith("__")) or a in ["register", "unregister"])])

    def __len__(self):
        return len(dir(self))

    def register(self, obj: object, identifier: str):
        setattr(self, identifier, obj)

    def unregister(self, identifer: str):
        delattr(self, identifer)


class ServerCache(DBCache):
    """Subclass of DBCache for guild data, parses json"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exists = False

    async def _set_value(self):
        await super()._set_value()
        if self._value:
            self._value = json.loads(self._value['data'])
            self.exists = True
        else:
            self.exists = False
            self.value = {}

    async def save(self, guild_id: int, bot):
        """Save the dictionary to the database"""
        await bot.DB.execute("UPDATE guilds SET data=$1 WHERE id=$2", json.dumps(self.value), guild_id)
        await self.bot_invalidate(bot)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, other):
        self._value = other


class UrlConverter(commands.Converter):
    """Convertor to parse URLs from a string or text"""
    async def convert(self, ctx, argument):
        if urlregex.match(argument):
            if len(argument) > 1000:
                raise InvalidArgument("Urls must be at most 1000 characters")
            return argument
        else:
            if ctx.message.attachments:
                return ctx.message.attachments[0].url
            raise InvalidArgument("String could not be interpereted as a url")
