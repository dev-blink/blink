import discord # noqa F401
from discord.ext import commands,menus # noqa F401


class BotHelp(commands.HelpCommand):
    colour = 16099001

    def get_ending_note(self):
        return f'Use {self.clean_prefix}{self.invoked_with} <command> for more info on a command.'

    def get_command_signature(self,command):
        return f"**{command.qualified_name} {command.signature}**"

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title='Commands', colour=self.colour)
        desc = []
        for cog, cmds in mapping.items():
            name = 'Other' if cog is None else cog.qualified_name
            filtered = await self.filter_commands(cmds, sort=True)
            if filtered:
                value = ' | '.join(c.name for c in cmds)
                value = f'**{name}** {value}'
                desc.append(value)
        embed.description = "\n\n".join(desc)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f'{cog.qualified_name} Commands', colour=self.colour)
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(title=group.qualified_name, colour=self.colour)
        if group.help:
            embed.description = group.help

        if isinstance(group, commands.Group):
            filtered = await self.filter_commands(group.commands, sort=True)
            for command in filtered:
                embed.add_field(name=self.get_command_signature(command), value=command.short_doc or '...', inline=False)

        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)

    async def send_command_help(self,command):
        embed = discord.Embed(title=f"**{command.name}**",colour=self.colour)
        embed.description = f"{self.get_command_signature(command)} {command.short_doc or '...'}"
        embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=embed)


def setup(bot):
    bot.help_command=BotHelp()
