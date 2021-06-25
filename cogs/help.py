# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


import discord
from discord.ext import commands, menus


class HelpMenu(menus.Menu):
    def __init__(self, modules):
        self.modules = modules
        super().__init__(timeout=60)

    async def send_initial_message(self, ctx, channel):
        self.modulenumber = 0
        return await channel.send(embed=self.modules[self.modulenumber])

    @menus.button('\U00002b05')
    async def previous(self, payload):
        if self.modulenumber == 0:
            self.modulenumber = len(self.modules) - 1
        else:
            self.modulenumber -= 1
        await self.message.edit(embed=self.modules[self.modulenumber])

    @menus.button('\U000027a1')
    async def next(self, payload):
        if self.modulenumber == len(self.modules) - 1:
            self.modulenumber = 0
        else:
            self.modulenumber += 1
        await self.message.edit(embed=self.modules[self.modulenumber])

    @menus.button('\U000023f9')
    async def cancel(self, payload):
        await self.message.edit(content="Message cancelled.")
        self.stop()


class BotHelp(commands.HelpCommand):
    def __init__(self, colour):
        super().__init__(verify_checks=False)
        self.colour = colour

    def get_ending_note(self):
        return f'Use {self.clean_prefix}{self.invoked_with} <command/module> for more info on a command or module.'

    def get_command_signature(self, command):
        return f"**{command.qualified_name} {command.signature}**"

    async def send_bot_help(self, mapping):
        modules = []
        cogs = []
        for cog, cmds in mapping.items():
            if not cog:
                continue
            filtered = await self.filter_commands(cmds, sort=True)
            if filtered:
                embed = discord.Embed(
                    title=f"Module {cog.qualified_name}", description=cog.description or discord.Embed.Empty, colour=self.colour)
                for c in filtered:
                    embed.add_field(
                        name=f"**{c.name}**", value=c.help or "No description", inline=False)
                embed.set_footer(text=self.get_ending_note())
                modules.append(embed)
                cogs.append(f"--{cog.qualified_name} [{len(cmds)}]")
        cogs = "\n".join(cogs)
        modules.insert(0, discord.Embed(title="React to this message with the controls below to view all modules",
                       description=f"Use help <module> for help on a module\nUse help <command> for more detail on a command\n\n**Modules active**: \n{cogs}", colour=self.colour))
        menu = HelpMenu(modules)
        await menu.start(self.get_destination())

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f'{cog.qualified_name} Commands', colour=self.colour)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(
                command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, colour=self.colour)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature(
                    command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"**{command.name}** {'('+', '.join(command.aliases) + ')' if command.aliases else ''}", colour=self.colour)
        embed.description = f"{self.get_command_signature(command)} {command.short_doc or ' ...'}"
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    def get_destination(self):
        return self.context


def setup(bot):
    bot.help_command = BotHelp(bot.colour)
