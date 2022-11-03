from datetime import datetime

import pytz
from discord import File, Interaction, Locale, User
from discord.ui import Button, Select

import asset
import config
from apps.genshin.genshin_app import GenshinApp
from apps.text_map.text_map_app import text_map
from apps.text_map.utils import get_month_name, get_user_locale
from UI_base_models import BaseView
from utility.utils import default_embed, get_user_timezone


class View(BaseView):
    def __init__(
        self,
        author: User,
        member: User,
        genshin_app: GenshinApp,
        locale: Locale,
        user_locale: str,
        current_month: int,
    ):
        super().__init__(timeout=config.mid_timeout)
        self.author = author
        self.member = member
        self.genshin_app = genshin_app
        self.locale = locale
        self.user_locale = user_locale
        self.add_item(MonthSelect(text_map.get(424, locale, user_locale), user_locale or locale, current_month))
        self.add_item(Primo(text_map.get(70, locale, user_locale)))
        self.add_item(Mora(text_map.get(72, locale, user_locale)))
        self.add_item(InfoButton())

class InfoButton(Button):
    def __init__(self):
        super().__init__(emoji=asset.info_emoji)
        
    async def callback(self, i: Interaction):
        await i.response.send_message(embed=default_embed(message=text_map.get(398, self.view.locale, self.view.user_locale)), ephemeral=True)

class MonthSelect(Select):
    def __init__(self, placeholder: str, locale: Locale | str, current_month: int):
        super().__init__(placeholder=placeholder)
        self.add_option(label=get_month_name(current_month, locale), value="0")
        self.add_option(label=get_month_name(current_month-1, locale), value="-1")
        self.add_option(label=get_month_name(current_month-2, locale), value="-2")
    
    async def callback(self, i: Interaction):
        self.view: View
        user_locale = await get_user_locale(i.user.id, i.client.db)
        embed = default_embed()
        embed.set_author(
            name=text_map.get(644, i.locale, user_locale),
            icon_url="https://i.imgur.com/V76M9Wa.gif",
        )
        await i.response.edit_message(embed=embed, attachments=[])
        user_locale = await get_user_locale(i.user.id, i.client.db)
        user_timezone = await get_user_timezone(i.user.id, i.client.db)
        month = datetime.now(pytz.timezone(user_timezone)).month + int(self.values[0])
        month = month + 12 if month < 1 else month
        result, success = await self.view.genshin_app.get_diary(i.user.id, month, i.locale)
        if not success:
            await i.followup.send(embed=result)
        else:
            view = View(i.user, i.user, self.view.genshin_app, i.locale, user_locale, datetime.now(pytz.timezone(user_timezone)).month)
            view.message = await i.edit_original_response(
                embed=result["embed"], view=view, attachments=[File(result["fp"], "diary.jpeg")]
            )
    

class Primo(Button):
    def __init__(self, label: str):
        super().__init__(label=label, emoji="<:PRIMO:1010048703312171099>")

    async def callback(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        self.view: View
        result, _ = await self.view.genshin_app.get_diary_logs(
            self.view.member.id, True, i.locale
        )
        await i.followup.send(embed=result, ephemeral=True)


class Mora(Button):
    def __init__(self, label: str):
        super().__init__(label=label, emoji="<:MORA:1010048704901828638>")

    async def callback(self, i: Interaction):
        await i.response.defer(ephemeral=True)
        self.view: View
        result, _ = await self.view.genshin_app.get_diary_logs(
            self.view.member.id, False, i.locale
        )
        await i.followup.send(embed=result, ephemeral=True)
