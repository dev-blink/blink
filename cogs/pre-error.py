# Copyright © Aidan Allen - All Rights Reserved
# Unauthorized copying of this project, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Aidan Allen <allenaidan92@icloud.com>, 29 May 2021


from discord.ext import commands
import blink

class PRELOAD(blink.Cog):
    """Ignore all errors before loading"""
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        pass


def setup(bot):
    bot.add_cog(PRELOAD(bot,"preload"))
