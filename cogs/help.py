import discord
from discord.ext import menus
from discord.ext import commands
import blink
class HelpCommand(commands.Cog,name="Help"):
    def __init__(self,bot):
        bot.remove_command("help")
        self.bot = bot
        

    
    @commands.command(name="help",aliases=["h"])
    async def help(self,ctx):
        """Shows this help command"""
        try:
            message = await ctx.author.send(".")
            await message.delete()
            await ctx.message.add_reaction("\U0001f48c")
        except:
            return await ctx.send("I am unable to DM you.")
        modules = []
        for cog in self.bot.cogs:
            embed=discord.Embed(title=cog+' commands.',description=self.bot.cogs[cog].__doc__,colour=0xf5a6b9)
            notempty = False
            for c in self.bot.get_cog(cog).get_commands():
                if not c.hidden or ctx.author.id in self.bot.owner_ids :
                    notempty = True
                    embed.add_field(name=c.name,value=c.help,inline=False)
            if notempty:
                modules.append(embed)
        
        class HelpMenu(menus.Menu, modules=modules):
            def __init__(self):
                super().__init__(timeout=30)
            async def send_initial_message(self, ctx, channel):
                self.modulenumber = 0
                return await ctx.author.send(embed=modules[self.modulenumber])

            @menus.button('\U00002b05')
            async def previous(self, payload):
                if self.modulenumber == 0:
                    self.modulenumber = len(modules) - 1
                else:
                    self.modulenumber -= 1
                await self.message.edit(embed=modules[self.modulenumber])

            @menus.button('\U000027a1')
            async def next(self, payload):
                if self.modulenumber == len(modules) - 1:
                    self.modulenumber = 0
                else:
                    self.modulenumber += 1
                await self.message.edit(embed=modules[self.modulenumber])

            @menus.button('\U000023f9')
            async def cancel(self, payload):
                await self.message.edit(content="Message cancelled.")
                self.stop()
            


        menu = HelpMenu()
        await menu.start(ctx)

def setup(bot):
    bot.add_cog(HelpCommand(bot))