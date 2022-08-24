import asyncio
import importlib
import sys

from discord import Forbidden, Interaction, app_commands, HTTPException
from discord.app_commands import locale_str as _
from discord.ext import commands
import sentry_sdk
from UI_elements.others import Roles
from utility.utils import default_embed, error_embed, log


class AdminCog(commands.Cog, name="admin"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_seria():
        async def predicate(i: Interaction) -> bool:
            if i.user.id != 410036441129943050:
                await i.response.send_message(
                    embed=error_embed(message="你不是小雪本人").set_author(
                        name="生物驗證失敗", icon_url=i.user.avatar
                    ),
                    ephemeral=True,
                )
            return i.user.id == 410036441129943050

        return app_commands.check(predicate)

    @is_seria()
    @app_commands.command(name="reload", description=_("Admin usage only", hash=496))
    @app_commands.rename(module_name="名稱")
    async def realod(self, i: Interaction, module_name: str):
        try:
            importlib.reload(sys.modules[module_name])
        except KeyError:
            return await i.response.send_message(
                embed=error_embed(message=module_name).set_author(
                    name="查無 module", icon_url=i.user.avatar
                ),
                ephemeral=True,
            )
        else:
            return await i.response.send_message(
                embed=default_embed(message=module_name).set_author(
                    name="重整成功", icon_url=i.user.avatar
                ),
                ephemeral=True,
            )

    @is_seria()
    @app_commands.command(name="roles", description=_("Admin usage only", hash=496))
    async def roles(self, i: Interaction):
        role = i.guild.get_role(1006906916678684752)
        embed = default_embed("身份組 Roles", f"{role.mention}: {len(role.members)}")
        await i.response.defer(ephemeral=True)
        await i.channel.send(embed=embed, view=Roles.View())

    @is_seria()
    @app_commands.command(name="sync", description=_("Admin usage only", hash=496))
    async def roles(self, i: Interaction):
        await i.response.defer()
        await self.bot.tree.sync()
        await i.followup.send("sync done")
        
    @is_seria()
    @app_commands.command(name='annouce', description=_("Admin usage only", hash=496))
    async def annouce(self, i: Interaction, message: str):
        await i.response.defer()
        total = 0
        count = 0
        sent = []
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.id not in sent and member.id != self.bot.user.id:
                    total += 1
                    try:
                        await member.send(message.replace('%n','\n'))
                        sent.append(member.id)
                        await asyncio.sleep(2.0)
                    except (Forbidden, HTTPException):
                        continue
                    except Exception as e:
                        log.warning(f"[EXCEPTION][{i.user.id}][View Error]: [retcode]{e.retcode} [original]{e.original} [error message]{e.msg}")
                        sentry_sdk.capture_exception(e)
                        continue
                    count += 1
        await i.followup.send(f'complete: {count}/{total}')
                    
    @is_seria()
    @app_commands.command(name='status', description=_("Admin usage only", hash=496))
    async def status(self, i: Interaction):
        await i.response.defer()
        embed = default_embed()
        embed.add_field(name='Latency', value=f'{round(self.bot.latency*1000)} ms')
        embed.add_field(name='Servers', value=f'Connected to {len(self.bot.guilds)} servers')
        count = 0
        for guild in self.bot.guilds:
            count += len(guild.members)
        embed.add_field(name='Users', value=f'{count} users')
        await i.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
