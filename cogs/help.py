# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <blink@aaix.dev>, 29 Dec 2023


import discord
from discord.ext import commands, menus


class HelpMenu(menus.Menu):
    def __init__(self, modules):
        self.modules = modules # array of embeds
        super().__init__(timeout=60)

    async def send_initial_message(self, ctx, channel):
        self.modulenumber = 0 # index of circular list of modules
        return await channel.send(embed=self.modules[self.modulenumber])

    @menus.button('\U00002b05') # back emoji
    async def previous(self, payload):
        if self.modulenumber == 0:
            self.modulenumber = len(self.modules) - 1 # wrap arround to the back
        else:
            self.modulenumber -= 1
        await self.message.edit(embed=self.modules[self.modulenumber])

    @menus.button('\U000027a1') # forwards emoji
    async def next(self, payload):
        if self.modulenumber == len(self.modules) - 1:
            self.modulenumber = 0 # wrap arround to the front
        else:
            self.modulenumber += 1
        await self.message.edit(embed=self.modules[self.modulenumber])

    @menus.button('\U000023f9') # stop emoji
    async def cancel(self, payload):
        await self.message.edit(content="Message cancelled.")
        self.stop()


class BotHelp(commands.HelpCommand):
    """Help command subclass"""
    def __init__(self, colour):
        super().__init__(verify_checks=False)
        self.colour = colour

    def get_ending_note(self):
        """String for the footer"""
        return f'Use {self.context.clean_prefix}{self.invoked_with} <command/module> for more info on a command or module.'

    def get_command_signature(self, command):
        """Returns the command name along with the arguments"""
        return f"**{command.qualified_name} {command.signature}**"

    async def send_bot_help(self, mapping):
        """
        Iterate over modules and create an individual mapping for them
        then display them in a list with a reaction menu
        """
        modules = [] # array of embeds
        cogs = [] # name of module and number of commands in that module
        for cog, cmds in mapping.items():
            if not cog:
                continue
            filtered = await self.filter_commands(cmds, sort=True) # remove hidden commands
            if filtered:
                # craft embed
                embed = discord.Embed(
                    title=f"Module {cog.qualified_name}", description=cog.description, colour=self.colour)
                for c in filtered:
                    embed.add_field( # add field for each command
                        name=f"**{c.name}**", value=c.help or "No description", inline=False)
                embed.set_footer(text=self.get_ending_note()) # add footer
                modules.append(embed) # add to embeds array
                cogs.append(f"--{cog.qualified_name} [{len(cmds)}]") # add to list for building home page embed
        cogs = "\n".join(cogs)
        # create home page embed from list of cogs
        modules.insert(0, discord.Embed(title="React to this message with the controls below to view all modules",
                       description=f"Use help <module name> (case sensitive) for help on a module\nUse help <command> for more detail on a command\n\n**Modules active**: \n{cogs}", colour=self.colour))
        menu = HelpMenu(modules)
        await menu.start(self.get_destination())

    async def send_cog_help(self, cog):
        """Send help for a paticular cog"""
        embed = discord.Embed(
            title=f'{cog.qualified_name} Commands', colour=self.colour)
        if cog.description:
            embed.description = cog.description
        # walk sub commands
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature( # add field for each command
                command), value=command.short_doc or '...', inline=False) # ... for no description commands

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        """Send help for a grouped tree of commands"""
        # simmilar to send cog help
        embed = discord.Embed(title=group.qualified_name, colour=self.colour)
        if group.help:
            embed.description = group.help
        # walk commands
        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature( # add field for each command
                    command), value=command.short_doc or '...', inline=False) # ... for no description commands
 
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"**{command.name}** {'('+', '.join(command.aliases) + ')' if command.aliases else ''}", colour=self.colour)
        embed.description = f"{self.get_command_signature(command)} {command.short_doc or ' ...'}"
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    def get_destination(self):
        # return the abc.messageable type to send the message to
        return self.context # has to be context to start an embed menu


async def setup(bot):
    bot.help_command = BotHelp(bot.colour)
