from discord.utils import find
from random import Random as RAND
from discord.ext import commands
import math


async def searchrole(roles:list,term:str):
    """Custom role search for discord.py"""
    role=find(lambda r: r.name.lower() == term.lower(), roles)
    if not role:
        role=find(lambda r: r.name.lower().startswith(term.lower()), roles)
    if not role:
        role=find(lambda r: term.lower() in r.name.lower(), roles)
    return role


def ordinal(n:int):
    """Turns an int into its ordinal (1 -> 1st)"""
    return f"{n}{'tsnrhtdd'[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4]}" # noqa: E226,E228


class Config():
    @classmethod
    @property
    def newguilds(self):
        return int(702201857606549646)

    @classmethod
    @property
    def errors(self):
        return int(702201821615358004)

    @classmethod
    @property
    def startup(self):
        return 702705386557276271

    @classmethod
    @property
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
