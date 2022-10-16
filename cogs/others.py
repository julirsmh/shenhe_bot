from apps.text_map.text_map_app import text_map
from apps.text_map.utils import get_user_locale
from data.update.change_log import change_log
from data.update.change_log_en import change_log_en
from discord import Interaction, app_commands
from discord.app_commands import locale_str as _
from discord.app_commands import Choice
from discord.ext import commands
from UI_elements.others import ChangeLog, SettingsMenu, ManageAccounts
from utility.paginator import GeneralPaginator
from utility.utils import default_embed
import pytz


class OthersCog(commands.Cog, name="others"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="version", description=_("View shenhe's change logs", hash=503)
    )
    async def version(self, i: Interaction):
        embeds = []
        user_locale = await get_user_locale(i.user.id, self.bot.db)
        seria = self.bot.get_user(410036441129943050)
        if seria is None:
            seria = await self.bot.fetch_user(410036441129943050)
        locale = user_locale or i.locale
        if str(locale) == "zh-TW" or str(locale) == "zh-CN":
            display_change_log = change_log
        else:
            display_change_log = change_log_en
        for version, log in display_change_log.items():
            if self.bot.debug:
                log = f"`{log}`"
            embed = default_embed(version, log)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_footer(
                text=text_map.get(504, i.locale, user_locale), icon_url=seria.avatar
            )
            embeds.append(embed)
        if i.channel.id != 965964989875757156:
            view = ChangeLog.View(self.bot.db, embeds, i.locale, user_locale)
            await i.response.send_message(embed=embeds[0], view=view)
            view.message = await i.original_response()
        else:
            await i.response.send_message(embed=embeds[0])

    @app_commands.command(
        name="settings",
        description=_("View and change your user settings in Shenhe", hash=534),
    )
    async def settings(self, i: Interaction):
        user_locale = await get_user_locale(i.user.id, i.client.db)
        view = SettingsMenu.View(user_locale or i.locale)
        view.author = i.user
        embed = default_embed(message=text_map.get(534, i.locale, user_locale))
        embed.set_author(
            name=f"⚙️ {text_map.get(539, i.locale, user_locale)}",
            icon_url=i.user.display_avatar.url,
        )
        await i.response.send_message(embed=embed, view=view)
        view.message = await i.original_response()

    @app_commands.command(
        name="accounts", description=_("Manage your accounts in Shenhe", hash=544)
    )
    async def accounts_command(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        await ManageAccounts.return_accounts(i)

    @app_commands.command(
        name="v5", description=_("View the Shenhe v5 change log", hash=608)
    )
    async def version_five(self, i: Interaction):
        embeds = []
        images = [
            "https://i.imgur.com/Le1AyPz.png",
            "https://i.imgur.com/4jCFh5v.png",
            "https://i.imgur.com/9mwDGsp.png",
            "https://i.imgur.com/seuqAnc.png",
            "https://i.imgur.com/G4SrF4r.png",
            "https://i.imgur.com/cgV10Jw.png",
            "https://i.imgur.com/XDlxJOE.png",
        ]
        locale = await get_user_locale(i.user.id, i.client.db) or i.locale
        count = 0
        for hash in range(609, 622 + 1):
            if hash % 2 == 0:
                continue
            period = "。" if str(locale) == "zh-TW" or str(locale) == "zh-CN" else "."
            desc_text = text_map.get(hash + 1, locale).split(period)
            desc = ""
            for words in desc_text[:-1]:
                desc += f"{words}{period}\n\n"
            embed = default_embed(text_map.get(hash, locale), desc)
            embed.set_image(url=images[count])
            embeds.append(embed)
            count += 1
        await GeneralPaginator(i, embeds, i.client.db).start()

    @app_commands.command(
        name="timezone", description=_("View the timezone list", hash=134)
    )
    @app_commands.rename(timezone=_("timezone", hash=186))
    async def view_timezone_list(self, i: Interaction, timezone: str):
        await i.response.send_message(content=timezone, ephemeral=True)

    @view_timezone_list.autocomplete("timezone")
    async def timezone_autocomplete(self, i: Interaction, current: str):
        choices = []
        timezone_list = pytz.all_timezones
        for timezone in timezone_list:
            if current.lower() in timezone.lower():
                choices.append(Choice(name=timezone, value=timezone))
        return choices[:25]

    @app_commands.command(
        name="credits",
        description=_("Meet the awesome people that helped me!", hash=297),
    )
    async def view_credits(self, i: Interaction):
        locale = await get_user_locale(i.user.id, i.client.db) or i.locale
        embed = default_embed(text_map.get(475, locale) + " 🎉")
        kakaka = self.bot.get_user(425140480334888980) or await self.bot.fetch_user(
            425140480334888980
        )
        ginn = self.bot.get_user(489647643342143491) or await self.bot.fetch_user(
            489647643342143491
        )
        fox_fox = self.bot.get_user(274853284764975104) or await self.bot.fetch_user(
            274853284764975104
        )
        tedd = self.bot.get_user(272394461646946304) or await self.bot.fetch_user(
            272394461646946304
        )
        dinnerbone_3rd = self.bot.get_user(
            808396055879090267
        ) or await self.bot.fetch_user(808396055879090267)
        xiaokuai = self.bot.get_user(780643463946698813) or await self.bot.fetch_user(780643463946698813)
        embed.add_field(
            name=text_map.get(298, locale),
            value=f"{kakaka.mention} - 🇯🇵\n"
            f"{tedd.mention} - 🇯🇵\n"
            f"{ginn.mention} - 🇺🇸\n"
            f"{fox_fox.mention} - 🇺🇸\n"
            f"{dinnerbone_3rd.mention} - 🇨🇳\n"
            f"{xiaokuai.mention} - 🇨🇳",
            inline=False,
        )
        gaurav = self.bot.get_user(327390030689730561) or await self.bot.fetch_user(
            327390030689730561
        )
        kt = self.bot.get_user(153087013447401472) or await self.bot.fetch_user(
            153087013447401472
        )
        algoinde = self.bot.get_user(142949518680391680) or await self.bot.fetch_user(
            142949518680391680
        )
        m_307 = self.bot.get_user(301178730196238339) or await self.bot.fetch_user(301178730196238339)
        embed.add_field(
            name=text_map.get(466, locale),
            value=f"{gaurav.mention}\n"
            f"{kt.mention}\n"
            f"{algoinde.mention}\n"
            f"{m_307.mention}",
            inline=False,
        )
        embed.add_field(
            name=text_map.get(479, locale),
            value=text_map.get(497, locale),
            inline=False,
        )
        await i.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OthersCog(bot))
