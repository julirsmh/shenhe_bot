import asyncio
import re
from datetime import datetime
from typing import Any, List, Optional
import traceback
import aiohttp
import aiosqlite
import discord
import yaml
from discord import (ButtonStyle, Embed, Emoji, Interaction, Member,
                     SelectOption, app_commands)
from discord.app_commands import Choice
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View, select
from utility.AbyssPaginator import AbyssPaginator
from utility.GeneralPaginator import GeneralPaginator
from utility.GenshinApp import GenshinApp
from utility.utils import (defaultEmbed, errEmbed, getCharacterIcon,
                           getStatEmoji, getWeekdayName)
from utility.utils import get_name

from genshin.models import WikiPageType


class GenshinCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.genshin_app = GenshinApp(self.bot.db)
        self.debug_toggle = self.bot.debug_toggle


# cookie

    class CookieModal(discord.ui.Modal):
        def __init__(self, db: aiosqlite.Connection):
            self.genshin_app = GenshinApp(db)
            super().__init__(title='提交cookie', timeout=None, custom_id='cookie_modal')

        cookie = discord.ui.TextInput(
            label='Cookie',
            placeholder='請貼上從網頁上取得的Cookie, 取得方式請使用指令 /cookie',
            style=discord.TextStyle.long,
            required=True
        )

        async def on_submit(self, i: Interaction):
            result = await self.genshin_app.setCookie(i.user.id, self.cookie.value)
            await i.response.send_message(embed=result, ephemeral=True)

        async def on_error(self, error: Exception, i: Interaction):
            embed = errEmbed(
                '<a:error_animated:982579472060547092> 錯誤', f'```{error}```')
            await i.response.send_message(embed=embed, ephemeral=True)
# Cookie Submission

    @app_commands.command(
        name='cookie',
        description='設定Cookie')
    @app_commands.rename(option='選項')
    @app_commands.choices(option=[
        Choice(name='1. 顯示說明如何取得Cookie', value=0),
        Choice(name='2. 提交已取得的Cookie', value=1)])
    async def slash_cookie(self, i: Interaction, option: int):
        if option == 0:
            embed = defaultEmbed(
                'Cookie設置流程',
                "1.先複製底下的整段程式碼\n"
                "2.電腦或手機使用Chrome開啟Hoyolab並登入帳號 <https://www.hoyolab.com>\n"
                "3.按瀏覽器上面網址的部分, 並確保選取了全部網址\n"
                "4.在網址列先輸入 `java`, 然後貼上程式碼, 確保網址開頭變成 `javascript:`\n"
                "5.按Enter, 網頁會變成顯示你的Cookie, 全選然後複製\n"
                "6.在這裡提交結果, 使用：`/cookie 提交已取得的Cookie`\n"
                "無法理解嗎? 跟著下面的圖示操作吧!")
            embed.set_image(url="https://i.imgur.com/OQ8arx0.gif")
            code_msg = "```script:d=document.cookie; c=d.includes('account_id') || alert('過期或無效的Cookie,請先登出帳號再重新登入!'); c && document.write(d)```"
            await i.response.send_message(embed=embed)
            await i.followup.send(content=code_msg)
        elif option == 1:
            await i.response.send_modal(GenshinCog.CookieModal(self.bot.db))

    @app_commands.command(
        name='check',
        description='查看即時便籤, 例如樹脂、洞天寶錢、探索派遣'
    )
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def check(self, i: Interaction, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        result = await self.genshin_app.getRealTimeNotes(member.id, False)
        result.set_author(name=member, icon_url=member.avatar)
        await i.edit_original_message(embed=result)
# /stats

    @app_commands.command(name='stats', description='查看原神資料, 如活躍時間、神瞳數量、寶箱數量')
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def stats(self, i: Interaction, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        result = await self.genshin_app.getUserStats(member.id)
        result.set_author(name=member, icon_url=member.avatar)
        await i.edit_original_message(embed=result)
# /area

    @app_commands.command(name='area', description='查看區域探索度')
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def area(self, i: Interaction, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        result = await self.genshin_app.getArea(member.id)
        result.set_author(name=member, icon_url=member.avatar)
        await i.edit_original_message(embed=result)
# /claim

    @app_commands.command(name='claim', description='領取hoyolab登入獎勵')
    @app_commands.rename(all='全部人', member='其他人')
    @app_commands.describe(all='是否要幫全部已註冊的使用者領取獎勵', member='查看其他群友的資料')
    @app_commands.choices(all=[
        Choice(name='是', value=1),
        Choice(name='否', value=0)])
    async def claim(self, i: Interaction, all: Optional[int] = 0, member: Optional[Member] = None):
        if all == 1:
            await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 全員簽到中'))
            c: aiosqlite.Cursor = await self.bot.db.cursor()
            await c.execute('SELECT user_id FROM genshin_accounts WHERE ltuid IS NOT NULL')
            users = await c.fetchall()
            count = 0
            for index, tuple in enumerate(users):
                user_id = tuple[0]
                await self.genshin_app.claimDailyReward(user_id)
                count += 1
            await i.edit_original_message(embed=defaultEmbed(f'<a:check_animated:982579879239352370> 全員簽到完成 ({count})'))
        else:
            await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
            member = member or i.user
            result = await self.genshin_app.claimDailyReward(member.id)
            result.set_author(name=member, icon_url=member.avatar)
            await i.edit_original_message(embed=result)
# /diary

    @app_commands.command(name='diary', description='查看旅行者日記')
    @app_commands.rename(month='月份', member='其他人')
    @app_commands.describe(month='要查詢的月份', member='查看其他群友的資料')
    @app_commands.choices(month=[
        app_commands.Choice(name='這個月', value=0),
        app_commands.Choice(name='上個月', value=-1),
        app_commands.Choice(name='上上個月', value=-2)])
    async def diary(self, i: Interaction, month: int, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        month = datetime.now().month + month
        month = month + 12 if month < 1 else month
        result = await self.genshin_app.getDiary(member.id, month)
        result.set_author(name=member, icon_url=member.avatar)
        await i.edit_original_message(embed=result)
# /log

    @app_commands.command(name='log', description='查看最近25筆原石或摩拉收入紀錄')
    @app_commands.choices(data_type=[
        app_commands.Choice(name='原石', value=0),
        app_commands.Choice(name='摩拉', value=1)])
    @app_commands.rename(data_type='類別', member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def log(self, i: Interaction, data_type: int, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        result = await self.genshin_app.getDiaryLog(member.id)
        if type(result) is Embed:
            await i.edit_original_message(embed=result)
            return
        result = result[data_type]
        result.set_author(name=member, icon_url=member.avatar)
        await i.edit_original_message(embed=result)

# /today

    @app_commands.command(name='today', description='查看今日原石與摩拉收入')
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def today(self, i: Interaction, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        result = await self.genshin_app.getToday(member.id)
        result.set_author(name=member, icon_url=member.avatar)
        await i.edit_original_message(embed=result)
# /abyss

    @app_commands.command(name='abyss', description='深淵資料查詢')
    @app_commands.rename(check_type='類別', season='期別', floor='層數', member='其他人')
    @app_commands.describe(check_type='想要查看的資料類別',
                           season='這期還是上期?', floor='欲查閱的層數', member='查看其他群友的資料')
    @app_commands.choices(
        check_type=[Choice(name='總覽', value=0),
                    Choice(name='詳細', value=1)],
        season=[Choice(name='上期紀錄', value=0),
                Choice(name='本期紀錄', value=1)],
        floor=[Choice(name='所有樓層', value=0),
               Choice(name='最後一層', value=1)]
    )
    async def abyss(self, i: Interaction, check_type: int, season: int = 1, floor: int = 0, member: Optional[Member] = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        previous = True if season == 0 else False
        result = await self.genshin_app.getAbyss(member.id, previous)
        if type(result) is not list:
            result.set_author(name=member, icon_url=member.avatar)
        else:
            for embed in result:
                embed.set_author(name=member, icon_url=member.avatar)
        if type(result) == discord.Embed:
            await i.edit_original_message(embed=result)
            return
        if check_type == 0:
            await i.edit_original_message(embed=result[0])
        else:
            if floor == 1:
                await i.edit_original_message(embed=result[-1])
            else:
                await AbyssPaginator(i, result[1:]).start(embeded=True)
# /stuck

    @app_commands.command(name='stuck', description='找不到資料?')
    async def stuck(self, i: Interaction):
        embed = defaultEmbed(
            '註冊了, 但是找不到資料?',
            '請至<https://www.hoyolab.com>登入你的hoyoverse帳號\n'
            '跟著下方圖片中的步驟操作\n\n'
            '文字教學:\n'
            '1. 點選右上角自己的頭像\n'
            '2. 個人主頁\n'
            '3. 右上角「原神」\n'
            '4. 設定齒輪\n'
            '5. 三個選項都打開')
        embed.set_image(url='https://i.imgur.com/w6Q7WwJ.gif')
        await i.response.send_message(embed=embed)

    @app_commands.command(name='remind', description='設置樹脂提醒')
    @app_commands.rename(toggle='開關', resin_threshold='樹脂閥值', max_notif='最大提醒數量')
    @app_commands.describe(toggle='要開啟或關閉樹脂提醒功能', resin_threshold='在超過此樹脂量時, 申鶴會tag你進行提醒', max_notif='申鶴每一小時提醒一次, 超過這個數字就會停止提醒')
    @app_commands.choices(toggle=[Choice(name='開', value=1),
                                  Choice(name='關', value=0)])
    async def resin_remind(self, i: Interaction, toggle: int, resin_threshold: int = 140, max_notif: int = 3):
        result = await self.genshin_app.setResinNotification(i.user.id, toggle, resin_threshold, max_notif)
        await i.response.send_message(embed=result)

# /farm

    def get_farm_image(day: int):
        if day == 0 or day == 3:
            url = "https://i.imgur.com/Jr5tlUs.png"
        elif day == 1 or day == 4:
            url = "https://media.discordapp.net/attachments/823440627127287839/958862746127060992/5ac261bdfc846f45.png"
        elif day == 2 or day == 5:
            url = "https://media.discordapp.net/attachments/823440627127287839/958862745871220796/0b16376c23bfa1ab.png"
        else:
            url = "https://i.imgur.com/MPI5uwW.png"
        return url

    class ChooseDay(View):
        def __init__(self):
            super().__init__(timeout=None)
            for i in range(0, 4):
                self.add_item(GenshinCog.DayButton(i))

    class DayButton(Button):
        def __init__(self, day: int):
            self.day = day
            if day == 0:
                label = '週一、週四'
            elif day == 1:
                label = '週二、週五'
            elif day == 2:
                label = '週三、週六'
            else:
                label = '週日'
                self.day = 6
            super().__init__(label=label, style=ButtonStyle.blurple)

        async def callback(self, i: Interaction) -> Any:
            day_str = f'{getWeekdayName(self.day)}、{getWeekdayName(self.day+3)}' if self.day != 6 else '週日'
            embed = defaultEmbed(f"{day_str}可以刷的副本材料")
            embed.set_image(url=GenshinCog.get_farm_image(self.day))
            await i.response.edit_message(embed=embed)

    @app_commands.command(name='farm', description='查看原神今日可刷素材')
    async def farm(self, interaction: Interaction):
        day = datetime.today().weekday()
        embed = defaultEmbed(
            f"今日 ({getWeekdayName(day)}) 可以刷的副本材料")
        embed.set_image(url=GenshinCog.get_farm_image(day))
        view = GenshinCog.ChooseDay()
        await interaction.response.send_message(embed=embed, view=view)

    class ElementChooseView(View):  # 選擇元素按鈕的view
        def __init__(self, db: aiosqlite.Connection, author: Member, emojis: List):
            super().__init__(timeout=None)
            self.author = author
            for i in range(0, 6):
                self.add_item(GenshinCog.ElementButton(
                    i, db, emojis[i]))

        async def interaction_check(self, interaction: Interaction) -> bool:
            return interaction.user.id == self.author.id

    class ElementButton(Button):  # 元素按鈕
        def __init__(self, index: int, db: aiosqlite.Connection, emoji: Emoji):
            self.index = index
            self.db = db
            super().__init__(style=ButtonStyle.gray, row=index % 2, emoji=emoji)

        async def callback(self, i: Interaction):
            view = GenshinCog.CharactersDropdownView(
                self.index, self.db, i.user)
            embed = defaultEmbed('請選擇角色')
            await i.response.edit_message(embed=embed, view=view)

    class CharactersDropdownView(View):  # 角色配置下拉選單的view
        def __init__(self, index: int, db: aiosqlite.Connection, author: Member):
            super().__init__(timeout=None)
            self.author = author
            self.add_item(GenshinCog.BuildCharactersDropdown(index, db))

        async def interaction_check(self, interaction: Interaction) -> bool:
            return interaction.user.id == self.author.id

    class BuildCharactersDropdown(Select):  # 角色配置下拉選單(依元素分類)
        def __init__(self, index: int, db: aiosqlite.Connection):
            self.genshin_app = GenshinApp(db)
            elemenet_chinese = ['風', '冰', '雷', '岩', '水', '火']
            elements = ['anemo', 'cryo', 'electro', 'geo', 'hydro', 'pyro']
            with open(f'data/builds/{elements[index]}.yaml', 'r', encoding='utf-8') as f:
                self.build_dict = yaml.full_load(f)
            options = []
            for character, value in self.build_dict.items():
                options.append(SelectOption(label=character, value=character))
            super().__init__(
                placeholder=f'{elemenet_chinese[index]}元素角色', min_values=1, max_values=1, options=options)

        async def callback(self, interaction: Interaction):
            result = await self.genshin_app.getBuild(self.build_dict, str(self.values[0]))
            view = GenshinCog.BuildSelectView(len(result), result)
            await interaction.response.edit_message(embed=result[0][0], view=view)

    class BuildSelectView(View):
        def __init__(self, total: int, build_embeds: List):
            super().__init__(timeout=None)
            self.add_item(GenshinCog.BuildSelect(total, build_embeds))

    class BuildSelect(Select):
        def __init__(self, total: int, build_embeds: List):
            options = []
            self.embeds = build_embeds
            for i in range(1, total+1):
                options.append(SelectOption(
                    label=f'配置{i} - {build_embeds[i-1][1]}', value=i))
            super().__init__(
                placeholder=f'選擇配置', min_values=1, max_values=1, options=options)

        async def callback(self, interaction: Interaction) -> Any:
            await interaction.response.edit_message(embed=self.embeds[int(self.values[0])-1][0])

    # /build
    @app_commands.command(name='build', description='查看角色推薦主詞條、畢業面板、不同配置等')
    async def build(self, i: Interaction):
        emojis = []
        ids = [982138235239137290, 982138229140635648, 982138220248711178,
               982138232391237632, 982138233813098556, 982138221569900585]
        for id in ids:
            emojis.append(self.bot.get_emoji(id))
        view = GenshinCog.ElementChooseView(self.bot.db, i.user, emojis)
        await i.response.send_message(embed=defaultEmbed('請選擇想查看角色的元素'), view=view)

# /rate

    class ArtifactStatView(View):
        def __init__(self, browser, art_type: str, author: Member):
            super().__init__(timeout=None)
            self.author = author
            self.add_item(GenshinCog.AritfactMainStat(art_type))
            for i in range(1, 5):
                self.add_item(GenshinCog.ArtifactSubStat(browser, i))
            self.art_type = art_type
            self.main_stat = None
            self.sub_stat = []
            self.sub_stat_label = []

        async def interaction_check(self, interaction: Interaction) -> bool:
            return self.author.id == interaction.user.id

    class AritfactMainStat(Select):
        def __init__(self, art_type: str):
            disabled = False
            placeholder = '選擇主詞條屬性'
            if art_type == 'Flower':
                disabled = True
                options = [SelectOption(label='生命值')]
                placeholder = '主詞條: 生命值'
            elif art_type == 'Feather':
                disabled = True
                options = [SelectOption(label='攻擊力')]
                placeholder = '主詞條: 攻擊力'
            elif art_type == 'Sands':
                options = [
                    SelectOption(label='攻擊力%', value='POWER_PERCENTAGE'),
                    SelectOption(label='充能效率', value='ELEMENTS_CHARGE'),
                    SelectOption(label='生命值%', value='HP_PERCENTAGE'),
                    SelectOption(label='防禦力%', value='DEFENSE_PERCENTAGE'),
                    SelectOption(label='元素精通', value='ELEMENTS_KNOWLEDGE')
                ]
            elif art_type == 'Globlet':
                options = [
                    SelectOption(label='元素傷害加成', value='ELEMENTS_DAMAGE'),
                    SelectOption(label='物理傷害加成', value='PHYSICAL_DAMAGE'),
                    SelectOption(label='攻擊力%', value='POWER_PERCENTAGE'),
                    SelectOption(label='生命值%', value='HP_PERCENTAGE'),
                    SelectOption(label='防禦力%', value='DEFENSE_PERCENTAGE'),
                    SelectOption(label='元素精通', value='ELEMENTS_KNOWLEDGE')
                ]
            elif art_type == 'Circlet':
                options = [
                    SelectOption(label='暴擊傷害', value='CRITICAL_DAMAGE'),
                    SelectOption(label='暴擊率', value='CRITICAL_PERCENTAGE'),
                    SelectOption(label='攻擊力%', value='POWER_PERCENTAGE'),
                    SelectOption(label='生命值%', value='HP_PERCENTAGE'),
                    SelectOption(label='防禦力%', value='DEFENSE_PERCENTAGE'),
                    SelectOption(label='元素精通', value='ELEMENTS_KNOWLEDGE'),
                    SelectOption(label='治療加成', value='HEALING_DAMAGE'),
                ]
            super().__init__(placeholder=placeholder, options=options, disabled=disabled)

        async def callback(self, i: Interaction) -> Any:
            self.view.main_stat = self.values[0]
            await i.response.defer()

    class ArtifactSubStat(Select):
        def __init__(self, browser, index: int):
            self.browser = browser
            options = [
                SelectOption(label='無', value='none'),
                SelectOption(label='暴擊傷害', value='CRITICAL_DAMAGE'),
                SelectOption(label='暴擊率', value='CRITICAL_PERCENTAGE'),
                SelectOption(label='攻擊力%', value='POWER_PERCENTAGE'),
                SelectOption(label='攻擊力', value='POWER_FIXED'),
                SelectOption(label='生命值%', value='HP_PERCENTAGE'),
                SelectOption(label='生命值', value='HP_FIXED'),
                SelectOption(label='防禦力%', value='DEFENSE_PERCENTAGE'),
                SelectOption(label='防禦力', value='DEFENSE_FIXED'),
                SelectOption(label='元素精通', value='ELEMENTS_KNOWLEDGE'),
                SelectOption(label='充能效率', value='ELEMENTS_CHARGE')]
            super().__init__(placeholder=f'選擇第{index}個副詞條', options=options)

        async def callback(self, i: Interaction) -> Any:
            sub_stat_dict = {
                'CRITICAL_DAMAGE': '暴擊傷害',
                'CRITICAL_PERCENTAGE': '暴擊率',
                'POWER_PERCENTAGE': '攻擊力%',
                'POWER_FIXED': '攻擊力',
                'HP_PERCENTAGE': '生命值%',
                'HP_FIXED': '生命值',
                'DEFENSE_PERCENTAGE': '防禦力%',
                'DEFENSE_FIXED': '防禦力',
                'ELEMENTS_KNOWLEDGE': '元素精通',
                'ELEMENTS_CHARGE': '充能效率'
            }
            self.view.sub_stat.append(self.values[0])
            self.view.sub_stat_label.append(sub_stat_dict.get(self.values[0]))
            if (self.view.main_stat is not None or (self.view.art_type == 'Flower' or self.view.art_type == 'Feather')) and len(self.view.sub_stat) == 4:
                modal = GenshinCog.ArtifactSubStatVal(self.view.sub_stat_label)
                await i.response.send_modal(modal)
                await modal.wait()
                await i.edit_original_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 計算評分中'), view=None)
                main_stat = self.view.main_stat
                subs = self.view.sub_stat
                sub_stats = [
                    modal.sub_one_val.value,
                    modal.sub_two_val.value,
                    modal.sub_three_val.value,
                    modal.sub_four_val.value]
                page = await self.browser.newPage()
                await page.setViewport({"width": 1440, "height": 900})
                await page.goto("https://gamewith.net/genshin-impact/article/show/30567", {'waitUntil': 'domcontentloaded'})
                await page.waitForSelector('select.w-gensin-relic-type-selector')
                await page.select('.w-gensin-relic-type-selector', self.view.art_type)
                if main_stat is not None:
                    await page.select('div.w-gensin-main-option-type-selector>select', main_stat)
                await page.select('.w-gensin-level-selector', 'lv-20')
                for s in subs:
                    await page.select(f'.w-gensin-sub-option:nth-child({subs.index(s)+3})>select', s)
                    await page.type(f'.w-gensin-sub-option:nth-child({subs.index(s)+3})>input[type=number]', sub_stats[subs.index(s)])
                score = await (await (await page.querySelector('div.w-gensin-result-score>span')).getProperty("textContent")).jsonValue()
                rate = await (await (await page.querySelector('div.w-gensin-result-rank>span')).getProperty("textContent")).jsonValue()
                await page.close()
                url = ''
                if rate == 'SS':
                    url = 'https://www.expertwm.com/static/images/badges/badge-s+.png'
                elif rate == 'S':
                    url = 'https://www.expertwm.com/static/images/badges/badge-s.png'
                elif rate == 'A':
                    url = 'https://www.expertwm.com/static/images/badges/badge-a.png'
                elif rate == 'B':
                    url = 'https://www.expertwm.com/static/images/badges/badge-b.png'
                main_stat_names = {
                    'Flower': '生之花',
                    'Feather': '死之羽',
                    'Sands': '時之沙',
                    'Goblet': '空之杯',
                    'Circlet': '理之冠'}
                artifact_emojis = {
                    'Flower': '<:Flower_of_Life:982167959717945374>',
                    'Feather': '<:Plume_of_Death:982167959915077643>',
                    'Sands': '<:Sands_of_Eon:982167959881547877>',
                    'Goblet': '<:Goblet_of_Eonothem:982167959835402240>',
                    'Circlet': '<:Circlet_of_Logos:982167959692787802>'}
                embed = defaultEmbed(
                    f'得分: {score}',
                    f'{artifact_emojis.get(self.view.art_type)} {main_stat_names.get(self.view.art_type)}'
                )
                sub_stat_str = ''
                for index in range(0, 4):
                    sub_stat_str += f'{self.view.sub_stat_label[index]} - {sub_stats[index]}\n'
                if main_stat is None:
                    main_stat_str = '生命值' if self.view.art_type == 'Flower' else '攻擊力'
                else:
                    main_stat_str = sub_stat_dict.get(main_stat)
                embed.add_field(
                    name=f'主詞條: {main_stat_str}',
                    value=sub_stat_str
                )
                embed.set_thumbnail(url=url)
                await i.edit_original_message(embed=embed)
            else:
                await i.response.defer()

    class ArtifactSubStatVal(Modal):
        sub_one_val = TextInput(label='副詞條1')
        sub_two_val = TextInput(label='副詞條2')
        sub_three_val = TextInput(label='副詞條3')
        sub_four_val = TextInput(label='副詞條4', required=False)

        def __init__(self, labels: List[str]) -> None:
            self.sub_one_val.placeholder = f'輸入{labels[0]}的數值'
            self.sub_two_val.placeholder = f'輸入{labels[1]}的數值'
            self.sub_three_val.placeholder = f'輸入{labels[2]}的數值'
            self.sub_four_val.placeholder = f'輸入{labels[3]}的數值'
            super().__init__(title='輸入聖遺物資料', timeout=None)

        async def on_submit(self, i: Interaction) -> None:
            await i.response.defer()

    @app_commands.command(name='rate', description='聖遺物評分計算')
    @app_commands.rename(art_type='聖遺物類型')
    @app_commands.choices(art_type=[
        Choice(name='生之花', value='Flower'),
        Choice(name='死之羽', value='Feather'),
        Choice(name='時之沙', value='Sands'),
        Choice(name='空之杯', value='Goblet'),
        Choice(name='理之冠', value='Circlet')])
    async def rate(self, i: Interaction, art_type: str):
        view = GenshinCog.ArtifactStatView(self.bot.browser, art_type, i.user)
        await i.response.send_message(view=view)

    @app_commands.command(name='uid', description='查詢特定使用者的原神UID')
    @app_commands.rename(player='使用者')
    @app_commands.describe(player='選擇想要查詢的使用者')
    async def search_uid(self, i: Interaction, player: Member):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT uid FROM genshin_accounts WHERE user_id = ?', (player.id,))
        uid = await c.fetchone()
        if uid is None:
            await i.edit_original_message(embed=errEmbed('<a:error_animated:982579472060547092> 查無此用戶!', '這個使用者似乎還沒有註冊過UID\n輸入`/setuid`來設置uid'), ephemeral=True)
            return
        uid = uid[0]
        embed = defaultEmbed(f'UID查詢', uid)
        embed.set_author(name=player, icon_url=player.avatar)
        await i.edit_original_message(embed=embed)

    class CalcultorElementButtonView(View):
        def __init__(self, author: Member, chara_list: List, item_type: str):
            super().__init__(timeout=None)
            self.author = author
            for i in range(0, 6):
                self.add_item(GenshinCog.CalcultorElementButton(
                    i, chara_list, item_type))

        async def interaction_check(self, i: Interaction) -> bool:
            return i.user.id == self.author.id

    class CalcultorElementButton(Button):
        def __init__(self, index: int, chara_list: List, item_type: str):
            self.element_name_list = ['Anemo', 'Cryo',
                                      'Electro', 'Geo', 'Hydro', 'Pyro']
            element_emojis = ['<:WIND_ADD_HURT:982138235239137290>', '<:ICE_ADD_HURT:982138229140635648>', '<:ELEC_ADD_HURT:982138220248711178>',
                              '<:ROCK_ADD_HURT:982138232391237632>', '<:WATER_ADD_HURT:982138233813098556>', '<:FIRE_ADD_HURT:982138221569900585>']
            self.index = index
            self.chara_list = chara_list
            self.item_type = item_type
            super().__init__(
                emoji=element_emojis[index], style=ButtonStyle.gray, row=index % 2)

        async def callback(self, i: Interaction):
            element_chara_list = []
            for chara in self.chara_list:
                if chara[2] == self.element_name_list[self.index]:
                    element_chara_list.append(chara)
            self.view.element_chara_list = element_chara_list
            self.view.item_type = self.item_type
            await i.response.defer()
            self.view.stop()

    class CalculatorItems(View):
        def __init__(self, author: Member, item_list: List, item_type: str):
            super().__init__(timeout=None)
            self.author = author
            self.add_item(GenshinCog.CalculatorItemSelect(
                item_list, item_type))

        async def interaction_check(self, i: Interaction) -> bool:
            return self.author.id == i.user.id

    class CalculatorItemSelect(Select):
        def __init__(self, items, item_type):
            options = []
            for item in items:
                options.append(SelectOption(label=item[0], value=item[1]))
            super().__init__(placeholder=f'選擇{item_type}',
                             min_values=1, max_values=1, options=options)

        async def callback(self, i: Interaction):
            modal = GenshinCog.LevelModal()
            await i.response.send_modal(modal)
            await modal.wait()
            self.view.target = int(modal.chara.value)
            self.view.a = int(modal.attack.value)
            self.view.e = int(modal.skill.value)
            self.view.q = int(modal.burst.value)
            self.view.value = self.values[0]
            self.view.stop()

    class LevelModal(Modal):
        chara = TextInput(
            label='角色目標等級',
            placeholder='例如: 90',
        )

        attack = TextInput(
            label='普攻目標等級',
            placeholder='例如: 10',
        )

        skill = TextInput(
            label='元素戰技(E)目標等級',
            placeholder='例如: 8',
        )

        burst = TextInput(
            label='元素爆發(Q)目標等級',
            placeholder='例如: 9',
        )

        def __init__(self) -> None:
            super().__init__(title='計算資料輸入', timeout=None)

        async def on_submit(self, interaction: Interaction) -> None:
            await interaction.response.defer()

    def check_level_validity(self, target: int, a: int, e: int, q: int):
        if target > 90:
            return False, errEmbed('原神目前的最大等級是90唷')
        if a > 10 or e > 10 or q > 10:
            return False, errEmbed('天賦的最高等級是10唷', '有命座請自行減3')
        if target <= 0:
            return False, errEmbed('原神角色最少至少要1等唷')
        if a <= 0 or e <= 0 or q <= 0:
            return False, errEmbed('天賦至少要1等唷')
        else:
            return True, None

    class AddMaterialsView(View):
        def __init__(self, db: aiosqlite.Connection, disabled: bool, author: Member, materials):
            super().__init__(timeout=None)
            self.add_item(GenshinCog.AddTodoButton(disabled, db, materials))
            self.author = author

        async def interaction_check(self, interaction: Interaction) -> bool:
            return interaction.user.id == self.author.id

    class AddTodoButton(Button):
        def __init__(self, disabled: bool, db: aiosqlite.Connection, materials):
            super().__init__(style=ButtonStyle.blurple, label='新增到代辦清單', disabled=disabled)
            self.db = db
            self.materials = materials

        async def callback(self, i: Interaction) -> Any:
            c = await self.db.cursor()
            for item_data in self.materials:
                await c.execute('SELECT count FROM todo WHERE user_id = ? AND item = ?', (i.user.id, item_data[0]))
                count = await c.fetchone()
                if count is None:
                    await c.execute('INSERT INTO todo (user_id, item, count) VALUES (?, ?, ?)', (i.user.id, item_data[0], item_data[1]))
                else:
                    count = count[0]
                    await c.execute('UPDATE todo SET count = ? WHERE user_id = ? AND item = ?', (count+int(item_data[1]), i.user.id, item_data[0]))
            await self.db.commit()
            await i.response.send_message(embed=defaultEmbed('<a:check_animated:982579879239352370> 代辦事項新增成功', '使用`/todo`指令來查看你的代辦事項'), ephemeral=True)

    calc = app_commands.Group(name="calc", description="原神養成計算機")

    @calc.command(name='notown', description='計算一個自己不擁有的角色所需的素材')
    async def calc_notown(self, i: Interaction):
        client, uid, only_uid = await self.genshin_app.getUserCookie(i.user.id)
        charas = await client.get_calculator_characters()
        chara_list = []
        for chara in charas:
            chara_list.append([chara.name, chara.id, chara.element])
        button_view = GenshinCog.CalcultorElementButtonView(
            i.user, chara_list, '角色')
        embed = defaultEmbed('選擇角色的元素')
        await i.response.send_message(embed=embed, view=button_view)
        await button_view.wait()
        select_view = GenshinCog.CalculatorItems(
            i.user, button_view.element_chara_list, button_view.item_type)
        await i.edit_original_message(view=select_view)
        await select_view.wait()
        valid, error_msg = self.check_level_validity(
            select_view.target, select_view.a, select_view.e, select_view.q)
        if not valid:
            await i.followup.send(embed=error_msg, ephemeral=True)
            return
        chara_name = ''
        for chara in chara_list:
            if int(select_view.value) == int(chara[1]):
                chara_name = chara[0]
        character = await client.get_calculator_characters(query=chara_name)
        character = character[0]
        embed = defaultEmbed('計算結果')
        embed.set_thumbnail(url=character.icon)
        embed.add_field(
            name='計算內容',
            value=f'角色等級 1 ▸ {select_view.target}\n'
            f'普攻等級 1 ▸ {select_view.a}\n'
            f'元素戰技(E)等級 1 ▸ {select_view.e}\n'
            f'元素爆發(Q)等級 1 ▸ {select_view.q}',
            inline=False
        )
        talents = await client.get_character_talents(select_view.value)
        builder = client.calculator()
        builder.set_character(select_view.value, current=1,
                              target=select_view.target)
        builder.add_talent(talents[0].group_id,
                           current=1, target=select_view.a)
        builder.add_talent(talents[1].group_id,
                           current=1, target=select_view.e)
        builder.add_talent(talents[2].group_id,
                           current=1, target=select_view.q)
        cost = await builder.calculate()
        materials = []
        for index, tuple in enumerate(cost):
            if tuple[0] == 'character':
                value = ''
                for item in tuple[1]:
                    value += f'{item.name}  x{item.amount}\n'
                    materials.append([item.name, item.amount])
                if value == '':
                    value = '不需要任何素材'
                embed.add_field(name='角色所需素材', value=value, inline=False)
            if tuple[0] == 'talents':
                value = ''
                for item in tuple[1]:
                    value += f'{item.name}  x{item.amount}\n'
                    materials.append([item.name, item.amount])
                if value == '':
                    value = '不需要任何素材'
                embed.add_field(name='天賦所需素材', value=value, inline=False)
        if len(materials) == 0:
            view = GenshinCog.AddMaterialsView(
                self.bot.db, True, i.user, materials)
        else:
            view = GenshinCog.AddMaterialsView(
                self.bot.db, False, i.user, materials)
        await i.edit_original_message(embed=embed, view=view)

    @calc.command(name='character', description='個別計算一個角色所需的素材')
    async def calc_character(self, i: Interaction):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        client, uid, only_uid = await self.genshin_app.getUserCookie(i.user.id)
        if only_uid:
            embed = errEmbed('你不能使用這項功能!', '請使用`/cookie`的方式註冊後再來試試看')
            await i.edit_original_message(embed=embed)
            return
        try:
            charas = await client.get_calculator_characters(sync=True)
        except:
            embed = defaultEmbed(
                '等等!',
                '你需要先進行下列的操作才能使用此功能\n'
                '由於米哈遊非常想要大家使用他們的 hoyolab APP\n'
                '所以以下操作只能在手機上用 APP 進行 <:penguin_dead:978841159147343962>\n'
                'APP 下載連結: [IOS](https://apps.apple.com/us/app/hoyolab/id1559483982) [Android](https://play.google.com/store/apps/details?id=com.mihoyo.hoyolab&hl=en&gl=US)')
            embed.set_image(url='https://i.imgur.com/GiYbVwU.gif')
            await i.edit_original_message(embed=embed)
            return
        chara_list = []
        for chara in charas:
            chara_list.append([chara.name, chara.id, chara.element])
        button_view = GenshinCog.CalcultorElementButtonView(
            i.user, chara_list, '角色')
        embed = defaultEmbed('選擇角色的元素')
        await i.edit_original_message(embed=embed, view=button_view)
        await button_view.wait()
        select_view = GenshinCog.CalculatorItems(
            i.user, button_view.element_chara_list, button_view.item_type)
        await i.edit_original_message(view=select_view)
        await select_view.wait()
        valid, error_msg = self.check_level_validity(
            select_view.target, select_view.a, select_view.e, select_view.q)
        if not valid:
            await i.followup.send(embed=error_msg, ephemeral=True)
            return
        chara_name = ''
        for chara in chara_list:
            if int(select_view.value) == int(chara[1]):
                chara_name = chara[0]
        details = await client.get_character_details(select_view.value)
        character = await client.get_calculator_characters(query=chara_name, sync=True)
        character = character[0]
        embed = defaultEmbed('計算結果')
        embed.set_thumbnail(url=character.icon)
        value = ''
        for index, tuple in enumerate(details):
            if tuple[0] == 'talents':
                value += f'角色等級 {character.level} ▸ {select_view.target}\n'
                value += f'普攻等級 {tuple[1][0].level} ▸ {select_view.a}\n'
                value += f'元素戰技(E)等級 {tuple[1][1].level} ▸ {select_view.e}\n'
                value += f'元素爆發(Q)等級 {tuple[1][2].level} ▸ {select_view.q}\n'
                break
        embed.add_field(name='計算內容', value=value, inline=False)
        cost = await (
            client.calculator()
            .set_character(select_view.value, current=character.level, target=select_view.target)
            .with_current_talents(attack=select_view.a, skill=select_view.e, burst=select_view.q)
        )
        materials = []
        for index, tuple in enumerate(cost):
            if tuple[0] == 'character':
                value = ''
                for item in tuple[1]:
                    value += f'{item.name}  x{item.amount}\n'
                    materials.append([item.name, item.amount])
                if value == '':
                    value = '不需要任何素材'
                embed.add_field(name='角色所需素材', value=value, inline=False)
            if tuple[0] == 'talents':
                value = ''
                for item in tuple[1]:
                    value += f'{item.name}  x{item.amount}\n'
                    materials.append([item.name, item.amount])
                if value == '':
                    value = '不需要任何素材'
                embed.add_field(name='天賦所需素材', value=value, inline=False)
        if len(materials) == 0:
            view = GenshinCog.AddMaterialsView(
                self.bot.db, True, i.user, materials)
        else:
            view = GenshinCog.AddMaterialsView(
                self.bot.db, False, i.user, materials)
        await i.edit_original_message(embed=embed, view=view)

    def oculi_emebd_style(element: str, url: str):
        embed = defaultEmbed(f'{element}神瞳位置')
        embed.set_image(url=url)
        embed.set_footer(text='單純功能搬運, 圖源並非來自我')
        return embed

    def get_oculi_embeds(area: int):
        embeds = []
        if area == 0:
            for i in range(1, 5):
                url = f'https://fortoffans.github.io/Maps/Oculus/Anemoculus/Map_Anemoculus_{i}.jpg?width=831&height=554'
                embeds.append(GenshinCog.oculi_emebd_style('風', url))
        elif area == 1:
            for i in range(1, 6):
                url = f'https://images-ext-1.discordapp.net/external/Gm5I4dqqanZEksPk7pggWfwoqW5UOiKPJP8Rt-uYQ5E/https/fortoffans.github.io/Maps/Oculus/Geoculus/Map_Geoculus_{i}.jpg?width=831&height=554'
                embeds.append(GenshinCog.oculi_emebd_style('岩', url))
        elif area == 2:
            for i in range(1, 7):
                url = f'https://images-ext-1.discordapp.net/external/u6qgVi5Fk28_wwEuu3OS9blTzC-7JQpridJiWv0vI5s/https/fortoffans.github.io/Maps/Oculus/Electroculus/Map_Electroculus_{i}.jpg?width=831&height=554'
                embeds.append(GenshinCog.oculi_emebd_style('雷', url))
        return embeds

    @app_commands.command(name='oculi', description='查看不同地區的神瞳位置')
    @app_commands.rename(area='地區')
    @app_commands.choices(area=[
        Choice(name='蒙德', value=0),
        Choice(name='璃月', value=1),
        Choice(name='稻妻', value=2)])
    async def oculi(self, i: Interaction, area: int):
        embeds = GenshinCog.get_oculi_embeds(area)
        await GeneralPaginator(i, embeds).start(embeded=True)

    class EnkaPageView(View):
        def __init__(self, embeds: List[Embed], charas: List, equip_dict: dict, id: int, disabled: bool):
            super().__init__(timeout=None)
            self.add_item(GenshinCog.EnkaArtifactButton(
                equip_dict, id, disabled))
            self.add_item(GenshinCog.EnkaEmojiList())
            self.add_item(GenshinCog.EnkaPageSelect(
                embeds, charas, equip_dict))

    class EnkaPageSelect(Select):
        def __init__(self, embeds: List[Embed], charas: List, equip_dict: dict):
            options = [SelectOption(label='總覽', value=0)]
            self.embeds = embeds
            self.equip_dict = equip_dict
            self.charas = charas
            for chara in charas:
                options.append(SelectOption(
                    label=f"{chara[0]} {chara[1]}", value=f'{charas.index(chara)+1} {chara[2]}'))
            super().__init__(placeholder='選擇分頁', min_values=1, max_values=1, options=options)

        async def callback(self, i: Interaction) -> Any:
            value = self.values[0].split()
            disabled = False if int(value[0]) != 0 else True
            chara_id = 0 if len(value) == 1 else value[1]
            view = GenshinCog.EnkaPageView(
                self.embeds, self.charas, self.equip_dict, chara_id, disabled)
            await i.response.edit_message(embed=self.embeds[int(value[0])], view=view)

    def percent_symbol(propId: str):
        symbol = '%' if 'PERCENT' in propId or 'CRITICAL' in propId or 'CHARGE' in propId or 'HEAL' in propId or 'HURT' in propId else ''
        return symbol

    class EnkaArtifactButton(Button):
        def __init__(self, equip_dict: dict, id: int, disabled: bool):
            self.equipments = equip_dict
            self.name = ''
            self.id = id
            for e, val in equip_dict.items():
                if int(e) == int(id):
                    self.name = val['name']
                    self.chara_equipments = val['equipments']
            super().__init__(style=ButtonStyle.blurple, label=f'聖遺物', disabled=disabled)

        async def callback(self, i: Interaction) -> Any:
            await i.response.edit_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
            artifact_emojis = [
                '<:Flower_of_Life:982167959717945374>', '<:Plume_of_Death:982167959915077643>',
                '<:Sands_of_Eon:982167959881547877>', '<:Goblet_of_Eonothem:982167959835402240>',
                '<:Circlet_of_Logos:982167959692787802>']
            embed = defaultEmbed(f'{self.name} - 聖遺物')
            for e in self.chara_equipments:
                if 'weapon' not in e:
                    artifact_name = get_name.getNameTextHash(
                        e['flat']['setNameTextMapHash'])
                    main = e["flat"]["reliquaryMainstat"]
                    symbol = GenshinCog.percent_symbol(main['mainPropId'])
                    artifact_str = f'{artifact_emojis[self.chara_equipments.index(e)]} {artifact_name}  +{int(e["reliquary"]["level"])-1}'
                    value = ''
                    value += f'**主詞條 {getStatEmoji(main["mainPropId"])} {main["statValue"]}{symbol}**\n'
                    for sub in e['flat']['reliquarySubstats']:
                        symbol = GenshinCog.percent_symbol(sub['appendPropId'])
                        value += f'{getStatEmoji(sub["appendPropId"])} {sub["statValue"]}{symbol}\n'
                    embed.add_field(
                        name=artifact_str,
                        value=value
                    )
            embed.set_thumbnail(url=getCharacterIcon(int(self.id)))
            self.disabled = False
            await i.edit_original_message(embed=embed, view=self.view)

    class EnkaEmojiList(Button):
        def __init__(self):
            super().__init__(label='對照表', style=ButtonStyle.gray)

        async def callback(self, i: Interaction) -> Any:
            embed = defaultEmbed(
                '符號對照表',
                '<:HP:982068466410463272> 生命值\n'
                '<:HP_PERCENT:982138227450347553> 生命值%\n'
                '<:DEFENSE:982068463566721064> 防禦力\n'
                '<:DEFENSE_PERCENT:982138218822639626> 防禦力%\n'
                '<:ATTACK:982138214305390632> 攻擊力\n'
                '<:ATTACK_PERCENT:982138215832117308> 攻擊力%\n'
                '<:CRITICAL:982068460731392040> 暴擊率\n'
                '<:CRITICAL_HURT:982068462081933352> 暴擊傷害\n'
                '<:CHARGE_EFFICIENCY:982068459179503646> 充能效率\n'
                '<:ELEMENT_MASTERY:982068464938270730> 元素精通\n'
                '<:HEAL_ADD:982138224170401853> 治療加成\n\n'
                '<:ICE_ADD_HURT:982138229140635648> 冰元素傷害加成\n'
                '<:FIRE_ADD_HURT:982138221569900585> 火元素傷害加成\n'
                '<:ELEC_ADD_HURT:982138220248711178> 雷元素傷害加成\n'
                '<:GRASS_ADD_HURT:982138222891110432> 草元素傷害加成\n'
                '<:ROCK_ADD_HURT:982138232391237632> 岩元素傷害加成\n'
                '<:WATER_ADD_HURT:982138233813098556> 水元素傷害加成\n'
                '<:WIND_ADD_HURT:982138235239137290> 風元素傷害加成\n'
                '<:PHYSICAL_ADD_HURT:982138230923231242> 物理傷害加成'
            )
            await i.response.edit_message(embed=embed, view=self.view)

    @app_commands.command(name='profile', description='透過 enka API 查看各式原神數據')
    @app_commands.rename(member='其他人', custom_uid='uid')
    @app_commands.describe(member='查看其他人的資料', custom_uid='使用 UID 查閱')
    async def profile(self, i: Interaction, member: Member = None, custom_uid: int = None):
        await i.response.send_message(embed=defaultEmbed('<a:LOADER:982128111904776242> 獲取資料中'))
        member = member or i.user
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT uid FROM genshin_accounts WHERE user_id = ?', (member.id,))
        uid = await c.fetchone()
        if uid is None:
            uid_c = i.guild.get_channel(978871680019628032)
            await i.edit_original_message(embed=errEmbed('找不到 UID!', f'請先至 {uid_c.mention} 設置 UID!'))
            return
        uid = uid[0]
        uid = custom_uid if custom_uid is not None else uid
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://enka.shinshin.moe/u/{uid}/__data.json') as r:
                data = await r.json()
        if 'avatarInfoList' not in data:
            embed = defaultEmbed(
                '<a:error_animated:982579472060547092> 錯誤', '請在遊戲中打開「顯示角色詳情」\n\n有時候申鶴會判斷錯誤\n如果你很確定你已經打開了的話\n再輸入一次指令吧！')
            embed.set_image(url='https://i.imgur.com/frMsGHO.gif')
            await i.edit_original_message(embed=embed)
            return
        player = data['playerInfo']
        embeds = []
        sig = player['signature'] if 'signature' in player else '(空)'
        overview = defaultEmbed(
            f'{player["nickname"]}',
            f"「{sig}」\n"
            f"玩家等級: Lvl. {player['level']}\n"
            f"世界等級: W{player['worldLevel']}\n"
            f"完成成就: {player['finishAchievementNum']}\n"
            f"深淵已達: {player['towerFloorIndex']}-{player['towerLevelIndex']}")
        overview.set_author(name=member, icon_url=member.avatar)
        overview.set_image(
            url='https://cdn.discordapp.com/attachments/971472744820650035/971482996572057600/Frame_4905.png')
        embeds.append(overview)
        charas = []
        for chara in player['showAvatarInfoList']:
            if chara['avatarId'] == 10000007 or chara['avatarId'] == 10000005:
                continue
            charas.append([get_name.getName(chara['avatarId']),
                          f"Lvl. {chara['level']}", chara['avatarId']])
        info = data['avatarInfoList']
        equipt_dict = {}
        for chara in info:
            if chara['avatarId'] == 10000007 or chara['avatarId'] == 10000005:
                continue
            prop = chara['fightPropMap']
            talent_levels = chara['skillLevelMap']
            talent_str = ''
            const = 0 if 'talentIdList' not in chara else len(
                chara['talentIdList'])
            for id, level in talent_levels.items():
                talent_str += f'{get_name.getName(int(id))} - Lvl. {level}\n'
            equipments = chara['equipList']
            equipt_dict[chara['avatarId']] = {
                'name': get_name.getName(chara["avatarId"]),
                'equipments': equipments
            }
            weapon_str = ''
            for e in equipments:
                if 'weapon' in e:
                    weapon_name = get_name.getName(e['itemId'])
                    refinment_str = ''
                    if 'affixMap' in e['weapon']:
                        refinment_str = f"- R{int(list(e['weapon']['affixMap'].values())[0])+1}"
                    weapon_str += f"{weapon_name} - Lvl. {e['weapon']['level']} {refinment_str}\n"
                    weapon_sub_str = ''
                    if len(e['flat']['weaponStats']) == 2:
                        propId = e['flat']['weaponStats'][1]['appendPropId']
                        symbol = GenshinCog.percent_symbol(propId)
                        weapon_sub_str = f"{getStatEmoji(propId)} {e['flat']['weaponStats'][1]['statValue']}{symbol}"
                    weapon_str += f"<:ATTACK:982138214305390632> {e['flat']['weaponStats'][0]['statValue']}\n{weapon_sub_str}"
                    break
            max_level = 20
            ascention = chara['propMap']['1002']['ival']
            if ascention == 1:
                max_level = 30
            elif ascention == 2:
                max_level = 50
            elif ascention == 3:
                max_level = 60
            elif ascention == 4:
                max_level = 70
            elif ascention == 5:
                max_level = 80
            else:
                max_level = 90
            embed = defaultEmbed(
                f"{get_name.getName(chara['avatarId'])} C{const} (Lvl. {chara['propMap']['4001']['val']}/{max_level})",
                f'<:HP:982068466410463272> 生命值上限 - {round(prop["2000"])} ({round(prop["1"])}/{round(prop["2000"])-round(prop["1"])})\n'
                f"<:ATTACK:982138214305390632> 攻擊力 - {round(prop['2001'])} ({round(prop['4'])}/{round(prop['2001'])-round(prop['4'])})\n"
                f"<:DEFENSE:982068463566721064> 防禦力 - {round(prop['2002'])} ({round(prop['7'])}/{round(prop['2002'])-round(prop['7'])})\n"
                f"<:ELEMENT_MASTERY:982068464938270730> 元素精通 - {round(prop['28'])}\n"
                f"<:CRITICAL:982068460731392040> 暴擊率 - {round(prop['20']*100, 1)}%\n"
                f"<:CRITICAL_HURT:982068462081933352> 暴擊傷害 - {round(prop['22']*100, 1)}%\n"
                f"<:CHARGE_EFFICIENCY:982068459179503646> 元素充能效率 - {round(prop['23']*100, 1)}%\n"
                f"<:FRIENDSHIP:982843487697379391> 好感度 - {chara['fetterInfo']['expLevel']}")
            embed.add_field(
                name='天賦',
                value=talent_str,
                inline=False
            )
            embed.add_field(
                name='武器',
                value=weapon_str,
                inline=False
            )
            embed.set_thumbnail(url=getCharacterIcon(chara['avatarId']))
            embeds.append(embed)

        view = GenshinCog.EnkaPageView(embeds, charas, equipt_dict, 0, True)
        await i.edit_original_message(embed=overview, view=view)

    # @app_commands.command(name='wiki', description='查看原神維基百科')
    # @app_commands.choices(wikiType=[Choice(name='角色', value=0)])
    # @app_commands.rename(wikiType='類別', query='關鍵詞')
    # @app_commands.describe(wikiType='要查看的維基百科分頁類別')
    # async def wiki(self, i: Interaction, wikiType: int, query: str):
    #     client = getClient()
    #     if wikiType == 0:
    #         previews = await client.get_wiki_previews(WikiPageType.CHARACTER)
    #         for p in previews:
    #             d = await client.get_wiki_page(p.id)
    #             d = d.modules
    #             for item in d['屬性']['list']:
    #                 if item['key'] == '名字' and query in item['value']:
    #                     print(d)
    #                     break


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GenshinCog(bot))
