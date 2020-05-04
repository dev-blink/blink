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
    n="%d%s" % (n,"tsnrhtdd"[(math.floor(n/10)%10!=1)*(n%10<4)*n%10::4])  # noqa: E226,E228
    return n


class Config():
    @classmethod
    def statsserver(self):
        return int(702200971781996606)

    @classmethod
    def newguilds(self):
        return int(702201857606549646)

    @classmethod
    def errors(self):
        return int(702201821615358004)

    @classmethod
    def startup(self,name:str):
        if "beta" in name:
            return None
        else:
            return 702705386557276271

    @classmethod
    def DBLtoken(self):
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5MjczODkxNzIzNjk5ODE1NCIsImJvdCI6dHJ1ZSwiaWF0IjoxNTg3ODIzNjQ4fQ.qVqkmGa5inwLuosfNydxreptiF_UuIslfXTOxTkoFbI"

    @classmethod
    def avatar_ids(self):
        return [706661641978249257,
        706661651948109834,
        706661660634644581,
        706661668029071381,
        706661683044679680,
        706661690980433952,
        706661700081942640,
        706661710022574081,
        706661719585325076,
        706661727705497612,
        706661735968276511,
        706661744415735889,
        706661755526316073,
        706661764191748158,
        706661779710935130,
        706661792830717962,
        706661804918571060,
        706661830403162152,
        706661841601822731,
        706661857762476033]


def prettydelta(seconds):
    seconds=int(seconds)
    days, seconds=divmod(seconds, 86400)
    hours, seconds=divmod(seconds, 3600)
    minutes, seconds=divmod(seconds, 60)
    if days > 0:
        return '%dd %dh%dm%ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh%dm%ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm%ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds,)


def prand(spice:float,uid:int,start:int,stop:int,inverse:bool=False):
    """Baised random"""
    if uid in [171197717559771136,692738917236998154]:
        if inverse:
            return start
        else:
            return stop
    else:
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
