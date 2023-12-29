# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <blink@aaix.dev>, 29 Dec 2023


from discord.ext import commands
import blink


class PRELOAD(blink.Cog):
    """Ignore all errors before loading"""
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        pass


async def setup(bot):
    await bot.add_cog(PRELOAD(bot,"preload"))
