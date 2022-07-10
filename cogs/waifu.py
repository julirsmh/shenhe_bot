import ast
import io
import random
from typing import Any, List

import hmtai
import waifuim
from data.waifu.waifu_tags import nsfw_tags, sfw_tags, wallpaper_tags
from debug import DefaultView
from discord import (ButtonStyle, File, Interaction, Member, Message,
                     SelectOption, app_commands)
from discord.app_commands import Choice
from discord.ext import commands, tasks
from discord.ext.commands.cooldowns import BucketType
from discord.ui import Button, Select, button
from utility.paginators.GeneralPaginator import GeneralPaginator
from utility.utils import defaultEmbed, divide_chunks, errEmbed
from waifuim import WaifuAioClient


class WaifuCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.random_nsfw.start()

    def cog_unload(self):
        self.random_nsfw.cancel()

    @tasks.loop(hours=2)
    async def random_nsfw(self):
        sese_id = 965842415913152522 if not self.bot.debug_toggle else 984792329426714677
        sese_channel = self.bot.get_channel(sese_id)
        result = random.choice(list(nsfw_tags.values()))
        url = hmtai.get(random.choice(result['libs']), result['value'])
        async with self.bot.session.get(str(url)) as resp:
            bytes_obj = io.BytesIO(await resp.read())
            file = File(
                bytes_obj, filename='waifu_image.jpg', spoiler=True)
            await sese_channel.send(file=file)
    
    @random_nsfw.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    async def waifu_tags(sese: int, bot: commands.Bot):
        async with bot.session.get('https://api.waifu.im/tags/?full=on') as r:
            tags = await r.json()
        choices = []
        for tag in tags['versatile']:
            choices.append(SelectOption(label=tag['name']))
        if sese == 1:
            for tag in tags['nsfw']:
                choices.append(SelectOption(label=tag['name']))
        return choices

    class TagSelectorView(DefaultView):
        def __init__(self, choices: List, author: Member):
            super().__init__(timeout=None)
            self.add_item(WaifuCog.TagSelector(choices))
            self.tags = []
            self.author = author

        async def interaction_check(self, interaction: Interaction) -> bool:
            if self.author.id != interaction.user.id:
                await interaction.response.send_message(embed=errEmbed(message='輸入 `/waifu` 來自行選擇標籤').set_author(name='這不是你的操控視窗', icon_url=interaction.user.avatar), ephemeral=True)
            return self.author.id == interaction.user.id

    class TagSelector(Select):
        def __init__(self, choices: List) -> None:
            super().__init__(placeholder='選擇你想要查詢的標籤', min_values=1,
                             max_values=len(choices), options=choices)

        async def callback(self, interaction: Interaction) -> Any:
            await interaction.response.defer()
            self.view.tags.append(self.values)
            self.view.stop()

    class ChooseTagView(DefaultView):
        def __init__(self, author: Member, type: str):
            super().__init__(timeout=None)
            self.author = author
            self.tag = None
            options = []
            if type == 'sfw':
                for tag_name, tag_info in sfw_tags.items():
                    options.append(SelectOption(
                        label=tag_name, value=f'{str(tag_info["libs"])}/{tag_info["value"]}', description=tag_info["description"]))
            elif type == 'nsfw':
                for tag_name, tag_info in nsfw_tags.items():
                    options.append(SelectOption(
                        label=tag_name, value=f'{str(tag_info["libs"])}/{tag_info["value"]}', description=tag_info["description"]))
            elif type == 'wallpaper':
                for tag_name, tag_info in wallpaper_tags.items():
                    options.append(SelectOption(
                        label=tag_name, value=f'{str(tag_info["libs"])}/{tag_info["value"]}/{tag_info["nsfw"]}', description=tag_info["description"]))
            divided = list(divide_chunks(options, 25))
            first = 1
            second = len(divided[0])
            for d in divided:
                self.add_item(WaifuCog.ChooseTagSelect(d, f'{first}~{second}'))
                first += 25
                second = first + len(d)

        async def interaction_check(self, interaction: Interaction) -> bool:
            if self.author.id != interaction.user.id:
                await interaction.response.send_message(embed=errEmbed().set_author(name='輸入 /waifu 來尋找你的二次元老婆', icon_url=interaction.user.avatar), ephemeral=True)
            return self.author.id == interaction.user.id

    class ChooseTagSelect(Select):
        def __init__(self, options: list, range: str):
            super().__init__(placeholder=f'選擇標籤 ({range})', options=options)

        async def callback(self, interaction: Interaction) -> Any:
            await interaction.response.defer()
            self.view.tag = self.values[0]
            self.view.stop()

    two_d = app_commands.Group(name='2d', description='二次元')

    @two_d.command(name='sfw', description='正常圖')
    @app_commands.rename(num='張數')
    async def gif(self, i: Interaction, num: int = 1):
        view = WaifuCog.ChooseTagView(i.user, type='sfw')
        await i.response.send_message(view=view)
        await view.wait()
        x = view.tag.split('/')
        libs = ast.literal_eval(x[0])
        tag = x[1]
        lib = random.choice(libs)
        if num == 1:
            await i.edit_original_message(embed=defaultEmbed(f'標籤: {tag}').set_image(url=(hmtai.get(lib, tag))).set_footer(text=f'API: {lib}'), view=None)
        else:
            embeds = []
            for index in range(0, num):
                lib = random.choice(libs)
                embed = defaultEmbed(f'標籤: {tag}')
                embed.set_image(url=(hmtai.get(lib, tag)))
                embed.set_footer(text=f'API: {lib}')
                embeds.append(embed)
            await GeneralPaginator(i, embeds).start(embeded=True, edit_original_message=True)

    class DeleteImageView(DefaultView):
        def __init__(self, message: Message):
            super().__init__(timeout=None)
            self.msg = message

        @button(label='刪除圖片', emoji='🗑️', style=ButtonStyle.red)
        async def deleteImage(self, i: Interaction, button: Button):
            await i.response.defer()
            await self.msg.delete()
            try:
                await i.delete_original_message()
            except:
                pass

    @two_d.command(name='wallpaper', description='桌面背景')
    @app_commands.rename(num='張數')
    @app_commands.describe(num='上限 5 張')
    async def wallpaper(self, i: Interaction, num: int = 1):
        if num > 5:
            return await i.response.send_message(embed=errEmbed().set_author(name='上限為 5 張', icon_url=i.user.avatar), ephemeral=True)
        sese_id = 965842415913152522 if not self.bot.debug_toggle else 984792329426714677
        view = WaifuCog.ChooseTagView(i.user, type='wallpaper')
        await i.response.send_message(view=view)
        await view.wait()
        x = view.tag.split('/')
        libs = ast.literal_eval(x[0])
        tag = x[1]
        lib = random.choice(libs)
        nsfw = x[2]
        url = (hmtai.get(lib, tag))
        if nsfw == 'True' and i.channel.id != sese_id:
            return await i.response.send_message(embed=errEmbed().set_author(name='只能在色色台色色哦', icon_url=i.user.avatar), ephemeral=True)
        if nsfw == 'True':
            if num == 1:
                await i.edit_original_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 尋找及下載圖片中...', '時長取決於小雪家裡網路速度'), view=None)
                async with self.bot.session.get(str(url)) as resp:
                    bytes_obj = io.BytesIO(await resp.read())
                    file = File(
                        bytes_obj, filename='waifu_image.jpg', spoiler=True)
                await i.edit_original_message(embed=None, attachments=[file], view=WaifuCog.DeleteImageView(await i.original_message()))
            else:
                await i.edit_original_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 尋找及下載圖片中...', '時長取決於小雪家裡網路速度'), view=None)
                for index in range(0, num):
                    lib = random.choice(libs)
                    url = (hmtai.get(lib, tag))
                    async with self.bot.session.get(str(url)) as resp:
                        bytes_obj = io.BytesIO(await resp.read())
                        file = File(
                            bytes_obj, filename='waifu_image.jpg', spoiler=True)
                    msg = await i.channel.send(file=file)
                    await i.channel.send(view=WaifuCog.DeleteImageView(msg))
                await i.delete_original_message()
        else:
            if num == 1:
                await i.edit_original_message(embed=defaultEmbed(f'標籤: {tag}').set_image(url=(hmtai.get(lib, tag))).set_footer(text=f'API: {lib}'), view=None)
            else:
                embeds = []
                for index in range(0, num):
                    lib = random.choice(libs)
                    embed = defaultEmbed(f'標籤: {tag}')
                    embed.set_image(url=(hmtai.get(lib, tag)))
                    embed.set_footer(text=f'API: {lib}')
                    embeds.append(embed)
                await GeneralPaginator(i, embeds).start(embeded=True, edit_original_message=True)

    @two_d.command(name='nsfw', description='色圖', nsfw=True)
    @app_commands.rename(num='張數')
    @app_commands.describe(num='上限 5 張')
    async def gif(self, i: Interaction, num: int = 1):
        if num > 5:
            return await i.response.send_message(embed=errEmbed().set_author(name='上限為 5 張', icon_url=i.user.avatar), ephemeral=True)
        sese_id = 965842415913152522 if not self.bot.debug_toggle else 984792329426714677
        if i.channel.id != sese_id:
            return await i.response.send_message(embed=errEmbed().set_author(name='只能在色色台色色哦', icon_url=i.user.avatar), ephemeral=True)
        view = WaifuCog.ChooseTagView(i.user, type='nsfw')
        await i.response.send_message(view=view)
        await view.wait()
        x = view.tag.split('/')
        libs = ast.literal_eval(x[0])
        tag = x[1]
        lib = random.choice(libs)
        url = (hmtai.get(lib, tag))
        if num == 1:
            await i.edit_original_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 尋找及下載圖片中...', '時長取決於小雪家裡網路速度'), view=None)
            async with self.bot.session.get(str(url)) as resp:
                bytes_obj = io.BytesIO(await resp.read())
                file = File(
                    bytes_obj, filename='waifu_image.jpg', spoiler=True)
            await i.edit_original_message(embed=None, attachments=[file], view=WaifuCog.DeleteImageView(await i.original_message()))
        else:
            await i.edit_original_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 尋找及下載圖片中...', '時長取決於小雪家裡網路速度'), view=None)
            for index in range(0, num):
                lib = random.choice(libs)
                url = (hmtai.get(lib, tag))
                async with self.bot.session.get(str(url)) as resp:
                    bytes_obj = io.BytesIO(await resp.read())
                    file = File(
                        bytes_obj, filename='waifu_image.jpg', spoiler=True)
                msg = await i.channel.send(file=file)
                await i.channel.send(view=WaifuCog.DeleteImageView(msg))
            await i.delete_original_message()

    @two_d.command(name='waifu', description='從 waifu API 隨機產生一張二次元老婆的照片')
    @app_commands.rename(sese='色色模式', many='多情模式', tags='標籤選擇')
    @app_commands.choices(sese=[Choice(name='開啟', value=1), Choice(name='關閉', value=0)], many=[Choice(name='開啟', value=1), Choice(name='關閉', value=0)], tags=[Choice(name='開啟', value=1), Choice(name='關閉', value=0)])
    @app_commands.describe(sese='是否要色色', many='產生 30 張老婆的照片 (色色模式開啟時5張', tags='透過標籤找到更符合你的需求的老婆')
    async def waifu(self, i: Interaction, many: int = 0, sese: int = 0, tags: int = 0):
        await i.response.defer()
        async with WaifuAioClient() as wf:
            sese_id = 965842415913152522 if not self.bot.debug_toggle else 984792329426714677
            if i.channel.id != sese_id and sese == 1:
                return await i.followup.send(embed=errEmbed().set_author(name='只能在色色台開啟色色模式哦', icon_url=i.user.avatar), ephemeral=True)
            is_nsfw = 'True' if sese == 1 else 'False'
            if tags == 1:
                view = WaifuCog.TagSelectorView(await WaifuCog.waifu_tags(sese, self.bot), i.user)
                await i.followup.send(view=view)
                await view.wait()
            if many == 0:
                if tags == 1:
                    try:
                        image = await wf.random(is_nsfw=[is_nsfw], selected_tags=view.tags[0])
                    except waifuim.exceptions.APIException:
                        return await i.edit_original_message(embed=errEmbed(message='您所指定的老婆條件要求太高\n請試試別的標籤').set_author(name='找不到老婆', icon_url=i.user.avatar), view=None)
                else:
                    image = await wf.random(is_nsfw=[is_nsfw])
                if sese == 1:
                    async with self.bot.session.get(str(image)) as resp:
                        bytes_obj = io.BytesIO(await resp.read())
                        file = File(
                            bytes_obj, filename='waifu_image.jpg', spoiler=True)
                    if tags == 1:
                        await i.edit_original_message(attachments=[file], view=None)
                    else:
                        await i.followup.send(file=file)
                else:
                    embed = defaultEmbed('您的老婆已送達')
                    embed.set_image(url=image)
                    if tags == 1:
                        await i.edit_original_message(embed=embed, view=None)
                    else:
                        await i.followup.send(embed=embed)

            else:
                if tags == 1:
                    try:
                        images = await wf.random(is_nsfw=[is_nsfw], many=True, selected_tags=view.tags[0])
                    except waifuim.exceptions.APIException:
                        return await i.edit_original_message(embed=errEmbed(message='您所指定的老婆條件要求太高\n請試試別的標籤').set_author(name='找不到老婆', icon_url=i.user.avatar), view=None)
                else:
                    images = await wf.random(is_nsfw=[is_nsfw], many=True)
                if sese == 1:
                    for index in range(0, 5):
                        async with self.bot.session.get(str(images[index])) as resp:
                            bytes_obj = io.BytesIO(await resp.read())
                            file = File(
                                bytes_obj, filename='waifu_image.jpg', spoiler=True)
                        if index == 0:
                            await (await i.original_message()).delete()
                        await i.channel.send(file=file)
                else:
                    embeds = []
                    count = 0
                    for image in images:
                        count += 1
                        embed = defaultEmbed(f'{i.user.display_name} 的後宮')
                        embed.set_image(url=image)
                        embed.set_footer(text=f'第 {count}/30 位老婆')
                        embeds.append(embed)
                    await GeneralPaginator(i, embeds).start(embeded=True, follow_up=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WaifuCog(bot))
