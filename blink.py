from discord.utils import find
from random import Random as RAND
from discord.ext import commands

async def searchrole(roles:list,term:str):
    """Custom role search for discord.py"""
    role = find(lambda r: r.name.lower() == term.lower(), roles)
    if not role:
        role = find(lambda r: r.name.lower().startswith(term.lower()), roles)
    if not role:
        role = find(lambda r: term.lower() in r.name.lower(), roles)
    return role



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



def prettydelta(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%dd%dh%dm%ds' % (days, hours, minutes, seconds)
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
        b = uid * spice
        rng = RAND(x=(b))
        return rng.randint(start,stop)
    

#MUSIC ERRORS
class NoChannelProvided(commands.CommandError):
    """Error raised when no suitable voice channel was supplied."""
    pass


class IncorrectChannelError(commands.CommandError):
    """Error raised when commands are issued outside of the players session channel."""
    pass
