__all__ = ['TutorialPaginator']


from discord import Interaction, SelectOption, User, ButtonStyle
from discord.ui import View, Select, button, Button
from typing import Optional, List, Union


class _view(View):
    def __init__(self, author: User, pages: List[SelectOption], embeded: bool):
        super().__init__()
        self.author = author
        self.pages = pages
        self.embeded = embeded
        self.current_page = 0

    async def interaction_check(self, interaction: Interaction) -> bool:
        return (interaction.user.id == self.author.id)

    async def update_children(self, interaction: Interaction):
        self.next.disabled = (self.current_page + 1 == len(self.pages))
        self.previous.disabled = (self.current_page <= 0)

        kwargs = {'content': self.pages[self.current_page]} if not (
            self.embeded) else {'embed': self.pages[self.current_page]}
        kwargs['view'] = self

        await interaction.response.edit_message(**kwargs)

    @button(label="上一頁", style=ButtonStyle.blurple, row=1)
    async def previous(self, interaction: Interaction, button: Button):
        self.current_page -= 1

        await self.update_children(interaction)

    @button(label="下一頁", style=ButtonStyle.blurple, row=1)
    async def next(self, interaction: Interaction, button: Button):
        self.current_page += 1
        if self.current_page == 1:
            role = interaction.guild.get_role(978626192301236297) # step 1 夢工廠
            await interaction.user.add_roles(role)
        elif self.current_page == 4:
            role = interaction.guild.get_role(978626843517288468) # step 2 抽獎台, 身份台
            await interaction.user.add_roles(role)
        elif self.current_page == 5:
            role = interaction.guild.get_role(978629867916636220) # step 3 委託台
            await interaction.user.add_roles(role)
        elif self.current_page == 6:
            role = interaction.guild.get_role(978673403290615828) # step 4 活動台
            await interaction.user.add_roles(role)
        elif self.current_page == 11:
            role = interaction.guild.get_role(978532779098796042) # 旅行者
            await interaction.user.add_roles(role)
        await self.update_children(interaction)


class TutorialPaginator:
    def __init__(self, interaction: Interaction, pages: list, custom_children: Optional[List[Union[Button, Select]]] = []):
        self.custom_children = custom_children
        self.interaction = interaction
        self.pages = pages

    async def start(self, embeded: Optional[bool] = False, quick_navigation: bool = True) -> None:
        if not (self.pages):
            raise ValueError("Missing pages")

        view = _view(self.interaction.user, self.pages, embeded)

        view.previous.disabled = True if (view.current_page <= 0) else False
        view.next.disabled = True if (
            view.current_page + 1 >= len(self.pages)) else False

        if (len(self.custom_children) > 0):
            for child in self.custom_children:
                view.add_item(child)

        kwargs = {'content': self.pages[view.current_page]} if not (
            embeded) else {'embed': self.pages[view.current_page]}
        kwargs['view'] = view

        await self.interaction.response.send_message(**kwargs, ephemeral=True)