import asyncio
from datetime import datetime, timedelta
from typing import Any, List, Optional

import aiosqlite
import discord
import yaml
from discord import (ButtonStyle, Guild, Interaction, Member, SelectOption,
                     User, app_commands)
from discord.app_commands import Choice
from discord.ext import commands, tasks
from discord.ui import Button, Modal, Select, TextInput, View, button
from utility.AbyssPaginator import AbyssPaginator
from utility.GenshinApp import GenshinApp
from utility.utils import defaultEmbed, errEmbed, getWeekdayName, log


class GenshinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.genshin_app = GenshinApp(self.bot.db, self.bot)
        self.debug_toggle = self.bot.debug_toggle
        self.claim_reward.start()
        self.resin_notification.start()

    def cog_unload(self):
        self.claim_reward.cancel()
        self.resin_notification.cancel()

    @tasks.loop(hours=24)
    async def claim_reward(self):
        await self.bot.log.send(log(True, False, 'Task loop', 'Auto claim started'))
        count = 0
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT user_id FROM genshin_accounts')
        users = await c.fetchall()
        count = 0
        for index, tuple in enumerate(users):
            user_id = tuple[0]
            await self.genshin_app.claimDailyReward(user_id)
            count += 1
            await asyncio.sleep(3.0)
        await self.bot.log.send(log(True, False, 'Schedule',
                                    f'Auto claim finished, {count} in total'))

    @tasks.loop(hours=2)
    async def resin_notification(self):
        await self.bot.log.send(log(True, False, 'Task loop', 'Resin check started'))
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT user_id, resin_threshold, current_notif, max_notif FROM genshin_accounts WHERE resin_notification_toggle = 1')
        users = await c.fetchall()
        count = 0
        for index, tuple in enumerate(users):
            user_id = tuple[0]
            resin_threshold = tuple[1]
            current_notif = tuple[2]
            max_notif = tuple[3]
            resin = await self.genshin_app.getRealTimeNotes(user_id, True)
            await self.bot.log.send(log(True, False, 'Resin Check',
                                        f'user_id = {user_id}, resin = {resin}'))
            count += 1
            if resin >= resin_threshold and current_notif < max_notif:
                guild: Guild = self.bot.get_guild(
                    778804551972159489) if self.debug_toggle else self.bot.get_guild(916838066117824553)
                thread = guild.get_thread(
                    978092463749234748) if self.debug_toggle else guild.get_thread(978092252154982460)
                user: User = self.bot.get_user(user_id)
                embed = defaultEmbed(
                    '<:PaimonSeria:958341967698337854> 樹脂要滿出來啦',
                    f'目前樹脂: {resin}/160\n'
                    f'目前設定閥值: {resin_threshold}\n'
                    f'目前最大提醒值: {max_notif}\n\n'
                    '輸入`/remind`來更改設定')
                await thread.send(content=user.mention, embed=embed)
                await c.execute('UPDATE genshin_accounts SET current_notif = ? WHERE user_id = ?', (current_notif+1, user_id))
            if resin < resin_threshold:
                await c.execute('UPDATE genshin_accounts SET current_notif = 0 WHERE user_id = ?', (user_id,))
            await asyncio.sleep(3.0)
        await self.bot.log.send(log(True, False, 'Task loop',
                                    f'Resin check finished {count} in total'))
        await self.bot.db.commit()

    @claim_reward.before_loop
    async def before_claiming_reward(self):
        now = datetime.now().astimezone()
        next_run = now.replace(hour=1, minute=0, second=0)  # 等待到早上1點
        if next_run < now:
            next_run += timedelta(days=1)
        await discord.utils.sleep_until(next_run)

    @resin_notification.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

# cookie

    class CookieModal(discord.ui.Modal):
        def __init__(self, db: aiosqlite.Connection, bot):
            self.genshin_app = GenshinApp(db, bot)
            super().__init__(title='提交cookie', timeout=None, custom_id='cookie_modal')

        cookie = discord.ui.TextInput(
            label='Cookie',
            placeholder='請貼上從網頁上取得的Cookie, 取得方式請使用指令 /cookie',
            style=discord.TextStyle.long,
            required=True,
            min_length=100,
            max_length=1500
        )

        async def on_submit(self, interaction: Interaction):
            result = await self.genshin_app.setCookie(interaction.user.id, self.cookie.value)
            await interaction.response.send_message(result, ephemeral=True)

        async def on_error(self, error: Exception, interaction: Interaction):
            await interaction.response.send_message('發生未知錯誤', ephemeral=True)
# Cookie Submission

    @app_commands.command(
        name='cookie',
        description='設定Cookie')
    @app_commands.rename(option='選項')
    @app_commands.choices(option=[
        Choice(name='1. 顯示說明如何取得Cookie', value=0),
        Choice(name='2. 提交已取得的Cookie', value=1)])
    async def slash_cookie(self, interaction: Interaction, option: int):
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
            await interaction.response.send_message(embed=embed)
            await interaction.followup.send(content=code_msg)
        elif option == 1:
            await interaction.response.send_modal(GenshinCog.CookieModal(self.bot.db, self.bot))
# /setuid

    @app_commands.command(
        name='setuid',
        description='設定原神UID')
    @app_commands.describe(uid='請輸入要保存的原神UID')
    async def slash_uid(self, interaction: Interaction, uid: int):
        result, success = await self.genshin_app.setUID(interaction.user.id, uid)
        if not success:
            await interaction.response.send_message(embed=result, ephemeral=True)
        await interaction.response.send_message(embed=result, ephemeral=True)

    @app_commands.command(
        name='check',
        description='查看即時便籤, 例如樹脂、洞天寶錢、探索派遣'
    )
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def check(self, interaction: Interaction,
                    member: Optional[Member] = None
                    ):
        member = member or interaction.user
        result = await self.genshin_app.getRealTimeNotes(member.id, False)
        result.set_author(name=member, icon_url=member.avatar)
        await interaction.response.send_message(embed=result)
# /stats

    @app_commands.command(
        name='stats',
        description='查看原神資料, 如活躍時間、神瞳數量、寶箱數量'
    )
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def stats(self, interaction: Interaction,
                    member: Optional[Member] = None
                    ):
        member = member or interaction.user
        result = await self.genshin_app.getUserStats(member.id)
        result.set_author(name=member, icon_url=member.avatar)
        await interaction.response.send_message(embed=result)
# /area

    @app_commands.command(
        name='area',
        description='查看區域探索度'
    )
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def area(self, interaction: Interaction,
                   member: Optional[Member] = None
                   ):
        member = member or interaction.user
        result = await self.genshin_app.getArea(member.id)
        result.set_author(name=member, icon_url=member.avatar)
        await interaction.response.send_message(embed=result)
# /claim

    @app_commands.command(
        name='claim',
        description='領取hoyolab登入獎勵'
    )
    @app_commands.rename(all='全部人', member='其他人')
    @app_commands.describe(all='是否要幫全部已註冊的使用者領取獎勵', member='查看其他群友的資料')
    @app_commands.choices(all=[
        Choice(name='是', value=1),
        Choice(name='否', value=0)])
    async def claim(self, interaction: Interaction, all: Optional[int] = 0, member: Optional[Member] = None):
        if all == 1:
            await interaction.response.send_message(embed=defaultEmbed('⏳ 全員簽到中'))
            c: aiosqlite.Cursor = await self.bot.db.cursor()
            await c.execute('SELECT user_id FROM genshin_accounts')
            users = await c.fetchall()
            count = 0
            for index, tuple in enumerate(users):
                user_id = tuple[0]
                await self.genshin_app.claimDailyReward(user_id)
                count += 1
            await interaction.followup.send(embed=defaultEmbed(f'✅ 全員簽到完成 ({count})'))
        else:
            member = member or interaction.user
            result = await self.genshin_app.claimDailyReward(member.id)
            result.set_author(name=member, icon_url=member.avatar)
            await interaction.response.send_message(embed=result)
# /diary

    @app_commands.command(
        name='diary',
        description='查看旅行者日記'
    )
    @app_commands.rename(month='月份', member='其他人')
    @app_commands.describe(month='要查詢的月份', member='查看其他群友的資料')
    @app_commands.choices(month=[
        app_commands.Choice(name='這個月', value=0),
        app_commands.Choice(name='上個月', value=-1),
        app_commands.Choice(name='上上個月', value=-2)]
    )
    async def diary(self, interaction: Interaction,
                    month: int, member: Optional[Member] = None
                    ):
        member = member or interaction.user
        month = datetime.now().month + month
        month = month + 12 if month < 1 else month
        result = await self.genshin_app.getDiary(member.id, month)
        result.set_author(name=member, icon_url=member.avatar)
        await interaction.response.send_message(embed=result)
# /log

    @app_commands.command(
        name='log',
        description='查看最近25筆原石或摩拉收入紀錄'
    )
    @app_commands.choices(
        data_type=[app_commands.Choice(name='原石', value=0),
                   app_commands.Choice(name='摩拉', value=1)]
    )
    @app_commands.rename(data_type='類別', member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def log(self, interaction: Interaction, data_type: int,
                  member: Optional[Member] = None
                  ):
        member = member or interaction.user
        result = await self.genshin_app.getDiaryLog(member.id)
        if type(result) is discord.Embed:
            await interaction.response.send_message(embed=result)
            return
        embed = result[data_type]
        result.set_author(name=member, icon_url=member.avatar)
        await interaction.response.send_message(embed=embed)
# /users

    @app_commands.command(
        name='users',
        description='查看所有已註冊原神帳號'
    )
    async def users(self, interaction: Interaction):
        await self.bot.log.send(log(False, False, 'Users', interaction.user.id))
        user_dict = self.genshin_app.getUserData()
        userStr = ""
        count = 0
        for user_id, value in user_dict.items():
            count += 1
            name = self.bot.get_user(user_id)
            userStr = userStr + \
                f"{count}. {name} - {value['uid']}\n"
        embed = defaultEmbed("所有帳號", userStr)
        await interaction.response.send_message(embed=embed)
# /today

    @app_commands.command(
        name='today',
        description='查看今日原石與摩拉收入'
    )
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def today(self, interaction: Interaction,
                    member: Optional[Member] = None
                    ):
        member = member or interaction.user
        result = await self.genshin_app.getToday(member.id)
        result.set_author(name=member, icon_url=member.avatar)
        await interaction.response.send_message(embed=result)
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
    async def abyss(self, interaction: Interaction, check_type: int, season: int = 1, floor: int = 0, member: Optional[Member] = None):
        member = member or interaction.user
        previous = True if season == 0 else False
        result = await self.genshin_app.getAbyss(member.id, previous)
        if type(result) is not list:
            result.set_author(name=member, icon_url=member.avatar)
        else:
            for embed in result:
                embed.set_author(name=member, icon_url=member.avatar)
        if type(result) == discord.Embed:
            await interaction.response.send_message(embed=result)
            return
        if check_type == 0:
            await interaction.response.send_message(embed=result[0])
        else:
            if floor == 1:
                await interaction.response.send_message(embed=result[-1])
            else:
                await AbyssPaginator(interaction, result[1:]).start(embeded=True)
# /stuck

    @app_commands.command(
        name='stuck',
        description='找不到資料?'
    )
    async def stuck(self, interaction: Interaction):
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='remind', description='設置樹脂提醒')
    @app_commands.rename(toggle='開關', resin_threshold='樹脂閥值', max_notif='最大提醒數量')
    @app_commands.describe(toggle='要開啟或關閉樹脂提醒功能', resin_threshold='在超過此樹脂量時, 申鶴會tag你進行提醒', max_notif='申鶴每一小時提醒一次, 超過這個數字就會停止提醒')
    @app_commands.choices(toggle=[Choice(name='開', value=1),
                                  Choice(name='關', value=0)])
    async def resin_remind(self, i: Interaction, toggle: int, resin_threshold: int = 140, max_notif: int = 3):
        result = await self.genshin_app.setResinNotification(i.user.id, toggle, resin_threshold, max_notif)
        await i.response.send_message(embed=result)

# /farm

    @app_commands.command(
        name='farm',
        description='查看原神今日可刷素材'
    )
    async def farm(self, interaction: Interaction):
        await self.bot.log.send(log(False, False, 'Farm', interaction.user.id))
        weekdayGet = datetime.today().weekday()
        embedFarm = defaultEmbed(
            f"今天({getWeekdayName(weekdayGet)})可以刷的副本材料", " ")
        if weekdayGet == 0 or weekdayGet == 3:
            embedFarm.set_image(
                url="https://media.discordapp.net/attachments/823440627127287839/958862746349346896/73268cfab4b4a112.png")
        elif weekdayGet == 1 or weekdayGet == 4:
            embedFarm.set_image(
                url="https://media.discordapp.net/attachments/823440627127287839/958862746127060992/5ac261bdfc846f45.png")
        elif weekdayGet == 2 or weekdayGet == 5:
            embedFarm.set_image(
                url="https://media.discordapp.net/attachments/823440627127287839/958862745871220796/0b16376c23bfa1ab.png")
        elif weekdayGet == 6:
            embedFarm = defaultEmbed(
                f"今天({getWeekdayName(weekdayGet)})可以刷的副本材料", "禮拜日可以刷所有素材 (❁´◡`❁)")
        await interaction.response.send_message(embed=embedFarm)

    class ElementChooseView(View):  # 選擇元素按鈕的view
        def __init__(self, db: aiosqlite.Connection, bot, author: Member, user: Member = None, user_characters: dict = None):
            super().__init__(timeout=None)
            self.author = author
            for i in range(0, 6):
                self.add_item(GenshinCog.ElementButton(
                    i, user_characters, user, db, bot))

        async def interaction_check(self, interaction: Interaction) -> bool:
            return interaction.user.id == self.author.id

    class ElementButton(Button):  # 元素按鈕
        def __init__(self, index: int, user_characters: dict, user: Member, db: aiosqlite.Connection, bot):
            elemenet_chinese = ['風', '冰', '雷', '岩', '水', '火']
            self.index = index
            self.user_characters = user_characters
            self.user = user
            self.db = db
            self.bot = bot
            super().__init__(
                label=f'{elemenet_chinese[index]}元素', style=ButtonStyle.blurple, row=index % 2)

        async def callback(self, i: Interaction):
            view = GenshinCog.CharactersDropdownView(
                self.index, self.user_characters, self.user, self.db, self.bot, i.user)
            embed = defaultEmbed('請選擇角色')
            await i.response.edit_message(embed=embed, view=view)

    class CharactersDropdownView(View):  # 角色配置下拉選單的view
        def __init__(self, index: int, user_characters: dict, user: Member, db: aiosqlite.Connection, bot, author):
            super().__init__(timeout=None)
            self.author = author
            if user_characters is None:
                self.add_item(
                    GenshinCog.BuildCharactersDropdown(index, db, bot))
            else:
                self.add_item(GenshinCog.UserCharactersDropdown(
                    index, user_characters, user, db, bot))

        async def interaction_check(self, interaction: Interaction) -> bool:
            return interaction.user.id == self.author.id

    class UserCharactersDropdown(Select):  # 使用者角色下拉選單(依元素分類)
        def __init__(self, index: int, user_characters: dict, user: Member, db: aiosqlite.Connection, bot):
            elemenet_chinese = ['風', '冰', '雷', '岩', '水', '火']
            elements = ['Anemo', 'Cryo', 'Electro', 'Geo', 'Hydro', 'Pyro']
            options = []
            self.user_characters = user_characters
            self.user = user
            self.genshin_app = GenshinApp(db, bot)
            for character in user_characters:
                if character.element == elements[index]:
                    options.append(SelectOption(
                        label=f'C{character.constellation}R{character.weapon.refinement} {character.name}', value=character.name))
            if not options:
                super().__init__(
                    placeholder=f'該元素沒有任何角色', min_values=1, max_values=1, options=[SelectOption(label='disabled')], disabled=True)
            else:
                super().__init__(
                    placeholder=f'{elemenet_chinese[index]}元素角色', min_values=1, max_values=1, options=options)

        async def callback(self, interaction: Interaction):
            await interaction.response.edit_message(embed=self.genshin_app.parseCharacter(self.user_characters, self.values[0], self.user), view=None)

    class BuildCharactersDropdown(Select):  # 角色配置下拉選單(依元素分類)
        def __init__(self, index: int, db: aiosqlite.Connection, bot):
            self.genshin_app = GenshinApp(db, bot)
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
            await interaction.response.edit_message(embed=result, view=None)

    # /build
    @app_commands.command(name='build', description='查看角色推薦主詞條、畢業面板、不同配置等')
    async def build(self, i: Interaction):
        view = GenshinCog.ElementChooseView(self.bot.db, self.bot, i.user)
        await i.response.send_message(embed=defaultEmbed('請選擇想查看角色的元素'), view=view)

    # /characters
    @app_commands.command(name='characters', description='查看已擁有角色資訊, 如命座、親密度、聖遺物')
    @app_commands.rename(member='其他人')
    @app_commands.describe(member='查看其他群友的資料')
    async def characters(self, i: Interaction, member: Optional[Member] = None):
        member = member or i.user
        user_characters = await self.genshin_app.getUserCharacters(user_id=member.id)
        if type(user_characters) is discord.Embed:
            await i.response.send_message(embed=user_characters)
            return
        view = GenshinCog.ElementChooseView(
            self.bot.db, self.bot, i.user, member, user_characters)
        embed = defaultEmbed('請選擇想查看角色的元素', '如果你沒有用`/cookie`註冊過, 只會顯示等級前8的角色')
        embed.set_author(name=member, icon_url=member.avatar)
        await i.response.send_message(embed=embed, view=view)

# /rate

    @app_commands.command(name='rate', description='聖遺物評分計算(根據副詞條)')
    @app_commands.rename(type='聖遺物類型', crit_dmg='暴傷', crit_rate='暴擊率', atk='攻擊百分比')
    @app_commands.choices(type=[
        Choice(name='生之花', value=0),
        Choice(name='死之羽', value=1),
        # Choice(name='時之沙', value=2),
        Choice(name='空之杯', value=3)])
    # Choice(name='理之冠', value=4)])
    async def rate(self, interaction: Interaction, type: int, crit_dmg: float, crit_rate: float, atk: float):
        score = crit_rate*2 + atk*1.3 + crit_dmg*1
        typeStr = ''
        if type == 0:
            typeStr = '生之花'
        elif type == 1:
            typeStr = '死之羽'
        elif type == 2:
            typeStr = '時之沙'
        elif type == 3:
            typeStr = '空之杯'
        else:
            typeStr = '理之冠'
        if type == 0 or type == 1:
            if score >= 40:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-s.png'
                desc = '極品聖遺物, 足以用到關服'
            elif score >= 30:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-a.png'
                desc = '良品, 追求強度的人的目標'
            elif score >= 20:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-b.png'
                desc = '及格, 可以用了'
            else:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-c.png'
                desc = '過渡用, 繼續刷'
        else:
            if score >= 50:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-s.png'
                desc = '極品聖遺物, 足以用到關服'
            elif score >= 40:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-a.png'
                desc = '良品, 追求強度的人的目標'
            elif score >= 30:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-b.png'
                desc = '及格, 可以用了'
            else:
                tier_url = 'https://www.expertwm.com/static/images/badges/badge-c.png'
                desc = '過渡用, 繼續刷'
        result = defaultEmbed(
            '聖遺物評分結果',
            f'總分: {round(score,2)}\n'
            f'「{desc}」'
        )
        result.add_field(
            name='詳情',
            value=f'類型: {typeStr}\n'
            f'暴傷: {crit_dmg}%\n'
            f'暴擊率: {crit_rate}%\n'
            f'攻擊百分比: {atk}%'
        )
        result.set_thumbnail(url=tier_url)
        result.set_footer(
            text='[來源](https://forum.gamer.com.tw/C.php?bsn=36730&snA=11316)')
        await interaction.response.send_message(embed=result)

    @app_commands.command(name='uid', description='查詢特定使用者的原神UID')
    @app_commands.rename(player='使用者')
    @app_commands.describe(player='選擇想要查詢的使用者')
    async def search_uid(self, i: Interaction, player: Member):
        c: aiosqlite.Cursor = await self.bot.db.cursor()
        await c.execute('SELECT uid FROM genshin_accounts WHERE user_id = ?', (player.id,))
        uid = await c.fetchone()
        if uid is None:
            await i.response.send_message(embed=errEmbed('查無此用戶!', '這個使用者似乎還沒有註冊過UID\n輸入`/setuid`來設置uid'), ephemeral=True)
            return
        uid = uid[0]
        embed = defaultEmbed(f'UID查詢', uid)
        embed.set_author(name=player, icon_url=player.avatar)
        await i.response.send_message(embed=embed)

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
            elemenet_chinese = ['風', '冰', '雷', '岩', '水', '火']
            self.element_name_list = ['Anemo', 'Cryo',
                                      'Electro', 'Geo', 'Hydro', 'Pyro']
            self.index = index
            self.chara_list = chara_list
            self.item_type = item_type
            super().__init__(
                label=f'{elemenet_chinese[index]}元素', style=ButtonStyle.blurple, row=index % 2)

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
            await i.response.send_message(embed=defaultEmbed('✅ 代辦事項新增成功', '使用`/todo`指令來查看你的代辦事項'), ephemeral=True)

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
        await i.response.send_message(view=button_view)
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
            view = GenshinCog.AddMaterialsView(self.bot.db, True, i.user, materials)
        else:
            view = GenshinCog.AddMaterialsView(self.bot.db, False, i.user, materials)
        await i.edit_original_message(embed=embed, view=view)

    @calc.command(name='character', description='個別計算一個角色所需的素材')
    async def calc_character(self, i: Interaction):
        await self.bot.log.send(log(False, False, 'Calc Character', i.user.id))
        client, uid, only_uid = await self.genshin_app.getUserCookie(i.user.id)
        if only_uid:
            embed = errEmbed('你不能使用這項功能!', '請使用`/cookie`的方式註冊後再來試試看')
            await i.followup.send(embed=embed)
            return
        try:
            charas = await client.get_calculator_characters(sync=True)
        except:
            embed = defaultEmbed(
                '等等!',
                '非常抱歉\n'
                '由於米哈遊真的很煩\n'
                '你需要先進行下列的操作才能使用此功能\n'
                '並且由於米哈遊非常想要大家使用他們的 hoyolab APP\n'
                '所以以下操作只能在手機上用 APP 進行 <:penguin_dead:978841159147343962>\n'
                'APP 下載連結: [IOS](https://apps.apple.com/us/app/hoyolab/id1559483982) [Android](https://play.google.com/store/apps/details?id=com.mihoyo.hoyolab&hl=en&gl=US)')
            embed.set_image(url='https://i.imgur.com/GiYbVwU.gif')
            await i.followup.send(embed=embed, ephemeral=True)
            return
        chara_list = []
        for chara in charas:
            chara_list.append([chara.name, chara.id, chara.element])
        button_view = GenshinCog.CalcultorElementButtonView(
            i.user, chara_list, '角色')
        await i.response.send_message(view=button_view)
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
            view = GenshinCog.AddMaterialsView(self.bot.db, True, i.user, materials)
        else:
            view = GenshinCog.AddMaterialsView(self.bot.db, False, i.user, materials)
        await i.edit_original_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GenshinCog(bot))
