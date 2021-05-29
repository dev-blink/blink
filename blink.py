# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


from random import Random as RAND
from discord.ext import commands
from math import floor as f
import functools
import asyncio
from aiohttp import ClientSession
import time
from asyncpg.pool import Pool
from collections import OrderedDict


class Timer:
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
        self.db = db
        self.identifier = identifier
        self.statement = statement
        self.values = values
        self._value = None
        self._current = False

    def __repr__(self):
        return f"<In memory DB cache - {self.statement}, {self.values}>"

    async def _set_value(self):
        self._value = await self.db.fetchrow(self.statement, *self.values)
        self._current = True

    async def __aenter__(self):
        if not self._current:
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

    async def bot_invalidate(self,bot):
        await bot.invalidate_cache(self.identifier)


def fancytext(name,term,scope:str):
    eng = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    conversion = [
        ["𝔞", "𝔟", "𝔠", "𝔡", "𝔢", "𝔣", "𝔤", "𝔥", "𝔦", "𝔧", "𝔨", "𝔩", "𝔪", "𝔫", "𝔬", "𝔭", "𝔮", "𝔯", "𝔰", "𝔱", "𝔲", "𝔳", "𝔴", "𝔵", "𝔶", "𝔷"], # ascii + 119997
        ['𝖆', '𝖇', '𝖈', '𝖉', '𝖊', '𝖋', '𝖌', '𝖍', '𝖎', '𝖏', '𝖐', '𝖑', '𝖒', '𝖓', '𝖔', '𝖕', '𝖖', '𝖗', '𝖘', '𝖙', '𝖚', '𝖛', '𝖜', '𝖝', '𝖞', '𝖟'], # ascii + 120101
        ['𝓪', '𝓫', '𝓬', '𝓭', '𝓮', '𝓯', '𝓰', '𝓱', '𝓲', '𝓳', '𝓴', '𝓵', '𝓶', '𝓷', '𝓸', '𝓹', '𝓺', '𝓻', '𝓼', '𝓽', '𝓾', '𝓿', '𝔀', '𝔁', '𝔂', '𝔃'], # ascii + 119945
        ['𝒶', '𝒷', '𝒸', '𝒹', '𝑒', '𝒻', '𝑔', '𝒽', '𝒾', '𝒿', '𝓀', '𝓁', '𝓂', '𝓃', '𝑜', '𝓅', '𝓆', '𝓇', '𝓈', '𝓉', '𝓊', '𝓋', '𝓌', '𝓍', '𝓎', '𝓏'] # ascii + 119893 or 119789
    ]
    if scope == "eq":
        if name == term:
            return True
    elif scope == "sw":
        if name.startswith(term):
            return True
    elif scope == "in":
        if term in name:
            return True

    for alphabet in conversion:
        check = term
        for x in range(0,26):
            check = check.replace(eng[x],alphabet[x])
        if scope == "eq":
            if name == check:
                return True
        elif scope == "sw":
            if name.startswith(check):
                return True
        elif scope == "in":
            if check in name:
                return True
    return False


async def searchrole(roles:list,term:str):
    """Custom role search for discord.py"""
    loop = asyncio.get_event_loop()

    for r in roles:
        if await loop.run_in_executor(None,functools.partial(fancytext,r.name.lower(),term.lower(),"eq")):
            return r
    for r in roles:
        if await loop.run_in_executor(None,functools.partial(fancytext,r.name.lower(),term.lower(),"sw")):
            return r
    for r in roles:
        if await loop.run_in_executor(None,functools.partial(fancytext,r.name.lower(),term.lower(),"in")):
            return r


def ordinal(n:int):
    """Turns an int into its ordinal (1 -> 1st)"""
    return f"{n}{'tsnrhtdd'[(f(n/10)%10!=1)*(n%10<4)*n%10::4]}" # noqa: E226,E228


class Config():
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
    seconds=int(seconds)
    days, seconds=divmod(seconds, 86400)
    hours, seconds=divmod(seconds, 3600)
    minutes, seconds=divmod(seconds, 60)
    if days > 0:
        return '%dd %dh %dm %ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh %dm %ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm %ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds,)


def prand(spice:float,uid:int,start:int,stop:int,inverse:bool=False):
    """Baised random"""
    b=uid * spice
    rng=RAND(x=(b))
    return rng.randint(start,stop)


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
    def __init__(self,bot:commands.Bot,identifier:str):
        self.bot = bot
        self.identifier = identifier
        bot._cogs.register(self,self.identifier)

    def cog_unload(self):
        self.bot._cogs.unregister(self.identifier)
        if hasattr(self,"session") and isinstance(self.session,ClientSession):
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
