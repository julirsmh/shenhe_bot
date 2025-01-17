from UI_base_models import BaseView
import config

__all__ = ["GeneralPaginator"]


from io import BytesIO
from typing import List, Optional, Union

import aiosqlite
from apps.text_map.text_map_app import text_map
from apps.text_map.utils import get_user_locale
from discord import ButtonStyle, Embed, File, Interaction, User
from discord.ui import Button, Select, button

from utility.utils import error_embed


class _view(BaseView):
    def __init__(
        self,
        author: User,
        embeds: List[Embed],
        db: aiosqlite.Connection,
        check: bool = True,
        files: List[BytesIO] = [],
    ):
        super().__init__(timeout=config.mid_timeout)
        self.author = author
        self.embeds = embeds
        self.check = check
        self.db = db
        self.files = files

        self.current_page = 0
        
        # wish paginator things
        self.rarity_filters = []
        self.banner_filters = []

    async def interaction_check(self, i: Interaction) -> bool:
        if not self.check:
            return True
        user_locale = await get_user_locale(i.user.id, self.db)
        if i.user.id != self.author.id:
            await i.response.send_message(
                embed=error_embed().set_author(
                    name=text_map.get(143, i.locale, user_locale),
                    icon_url=i.user.display_avatar.url,
                ),
                ephemeral=True,
            )
        return i.user.id == self.author.id

    async def update_children(self, interaction: Interaction):
        self.next.disabled = self.current_page + 1 == len(self.embeds)
        self.previous.disabled = self.current_page <= 0

        kwargs = {"embed": self.embeds[self.current_page]}
        if len(self.files) > 0:
            fp = self.files[self.current_page]
            fp.seek(0)
            file_name = f"{self.current_page}.jpeg"
            file = File(fp, file_name)
            kwargs["attachments"] = [file]

        kwargs["view"] = self

        await interaction.response.edit_message(**kwargs)

    @button(
        emoji="<:double_left:982588991461281833>",
        style=ButtonStyle.gray,
        row=1,
        custom_id="paginator_double_left",
    )
    async def first(self, interaction: Interaction, button: Button):
        self.current_page = 0

        await self.update_children(interaction)

    @button(
        emoji="<:left:982588994778972171>",
        style=ButtonStyle.blurple,
        row=1,
        custom_id="paginator_left",
    )
    async def previous(self, interaction: Interaction, button: Button):
        self.current_page -= 1

        await self.update_children(interaction)

    @button(
        emoji="<:right:982588993122238524>",
        style=ButtonStyle.blurple,
        row=1,
        custom_id="paginator_right",
    )
    async def next(self, interaction: Interaction, button: Button):
        self.current_page += 1

        await self.update_children(interaction)

    @button(
        emoji="<:double_right:982588990223958047>",
        style=ButtonStyle.gray,
        row=1,
        custom_id="paginator_double_right",
    )
    async def last(self, interaction: Interaction, button: Button):
        self.current_page = len(self.embeds) - 1

        await self.update_children(interaction)


class GeneralPaginator:
    def __init__(
        self,
        interaction: Interaction,
        embeds: List[Embed],
        db: aiosqlite.Connection,
        custom_children: Optional[List[Union[Button, Select]]] = [],
        files: Optional[List[BytesIO]] = [],
    ):
        self.custom_children = custom_children
        self.interaction = interaction
        self.embeds = embeds
        self.db = db
        self.files = files

    async def start(
        self,
        edit: bool = False,
        followup: bool = False,
        check: bool = True,
        ephemeral: bool = False,
        dm: bool = False
    ) -> None:
        if not (self.embeds):
            raise ValueError("Missing embeds")

        view = _view(self.interaction.user, self.embeds, self.db, check, self.files)
        view.previous.disabled = True if (view.current_page <= 0) else False
        view.next.disabled = (
            True if (view.current_page + 1 >= len(self.embeds)) else False
        )

        if len(self.custom_children) > 0:
            for child in self.custom_children:
                view.add_item(child)

        kwargs = {"embed": self.embeds[view.current_page]}
        if len(self.files) > 0:
            fp = self.files[view.current_page]
            fp.seek(0)
            file_name = f"{view.current_page}.jpeg"
            file = File(fp, file_name)
            kwargs["files"] = [file]

        kwargs["view"] = view

        if not edit:
            kwargs["ephemeral"] = ephemeral

        if edit:
            if "files" in kwargs:
                del kwargs["files"]
                fp = self.files[view.current_page]
                fp.seek(0)
                file = File(fp, f"{view.current_page}.jpeg")
                kwargs["attachments"] = [file]

            await self.interaction.edit_original_response(**kwargs)
        elif followup:
            await self.interaction.followup.send(**kwargs)
        elif dm:
            del kwargs["ephemeral"]
            view.message = await self.interaction.user.send(**kwargs)
        else:
            await self.interaction.response.send_message(**kwargs)
        
        if not dm:
            view.message = await self.interaction.original_response()

        await view.wait()
