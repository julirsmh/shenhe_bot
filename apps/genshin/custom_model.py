from datetime import datetime
import io
import aiohttp
import aiosqlite
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, validator, Field
import discord
import genshin
from discord.ext import commands
from enkanetwork.model.base import EnkaNetworkResponse
import cachetools


class ShenheUser(BaseModel):
    client: genshin.Client
    uid: int | None
    discord_user: discord.User | discord.Member | discord.ClientUser
    user_locale: str | None
    china: bool
    daily_checkin: bool = True

    class Config:
        arbitrary_types_allowed = True


class DamageResult(BaseModel):
    result_embed: discord.Embed
    cond_embed: Optional[discord.Embed] = None

    class Config:
        arbitrary_types_allowed = True


class NotificationUser(BaseModel):
    user_id: int
    threshold: int
    current: int
    max: int
    uid: Optional[int]
    last_notif_time: Optional[str]
    shenhe_user: Optional[ShenheUser] = None


class WishData(BaseModel):
    title: str
    total_wishes: int
    pity: int
    four_star: int
    five_star: int
    recents: List[Dict[str, str | int]]


class Wish(BaseModel):
    time: str
    rarity: int
    name: str


class WishInfo(BaseModel):
    total: int
    newest_wish: Wish
    oldest_wish: Wish
    character_banner_num: int
    permanent_banner_num: int
    weapon_banner_num: int
    novice_banner_num: int


class ShenheBot(commands.Bot):
    genshin_client: genshin.Client
    session: aiohttp.ClientSession
    db: aiosqlite.Connection
    main_db: aiosqlite.Connection
    backup_db: aiosqlite.Connection
    debug: bool
    maintenance: bool = False
    maintenance_time: Optional[str] = ""
    launch_time: datetime
    stats_card_cache: cachetools.TTLCache
    enka_card_cache: cachetools.TTLCache
    area_card_cache: cachetools.TTLCache
    abyss_overview_card_cache: cachetools.TTLCache
    abyss_floor_card_cache: cachetools.TTLCache
    abyss_one_page_cache: cachetools.TTLCache


class TodoList:
    def __init__(self):
        self.dict: Dict[int, int] = {}

    def add_item(self, item: Dict[int, int]):
        key = list(item.keys())[0]
        value = list(item.values())[0]
        if key in self.dict:
            self.dict[key] += value
        else:
            self.dict[key] = value

    def remove_item(self, item: Dict[int, int]):
        key = list(item.keys())[0]
        value = list(item.values())[0]
        if key in self.dict:
            self.dict[key] -= value
            if self.dict[key] <= 0:
                self.dict.pop(key)

    def return_list(self) -> Dict[int, int]:
        return self.dict


class EnkaView(discord.ui.View):
    overview_embed: discord.Embed
    character_options: List[discord.SelectOption]
    character_id: str
    data: EnkaNetworkResponse
    eng_data: EnkaNetworkResponse
    member: discord.User | discord.Member
    locale: discord.Locale | str
    custom_image_url: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class UserCustomImage(BaseModel):
    url: str
    nickname: str
    character_id: str
    user_id: int
    current: bool

    @validator("current", pre=True, allow_reuse=True)
    def parse_current(cls, v):
        return True if v == 1 else False

class GenshinAppResult(BaseModel):
    success: bool
    result: Any

class AbyssResult(BaseModel):
    embed_title: str = Field(alias="title")
    abyss: genshin.models.SpiralAbyss
    genshin_user: genshin.models.PartialGenshinUserStats = Field(alias="user")
    discord_user: discord.User | discord.Member | discord.ClientUser
    overview_embed: discord.Embed = Field(alias="overview")
    overview_file: io.BytesIO = Field(alias="overview_card")
    abyss_floors: List[genshin.models.Floor] = Field(alias="floors")
    characters: List[genshin.models.Character]

    class Config:
        arbitrary_types_allowed = True

class RealtimeNoteResult(BaseModel):
    embed: discord.Embed
    file: io.BytesIO

    class Config:
        arbitrary_types_allowed = True
        
class StatsResult(BaseModel):
    embed: discord.Embed
    file: io.BytesIO

    class Config:
        arbitrary_types_allowed = True

class AreaResult(BaseModel):
    embed: discord.Embed
    file: io.BytesIO

    class Config:
        arbitrary_types_allowed = True

class DiaryResult(BaseModel):
    embed: discord.Embed
    file: io.BytesIO

    class Config:
        arbitrary_types_allowed = True

class CharacterResult(BaseModel):
    embed: discord.Embed
    options: List[discord.SelectOption]
    file: io.BytesIO
    characters: List[genshin.models.Character]
    
    class Config:
        arbitrary_types_allowed = True

class CharacterBuild(BaseModel):
    embed: discord.Embed
    weapon: Optional[str] = None
    artifact: Optional[str] = None
    is_thought: bool

    class Config:
        arbitrary_types_allowed = True

class FightProp(BaseModel):
    name: str
    emoji: str
    substat: bool
    text_map_hash: int

class EnkanetworkData(BaseModel):
    data: EnkaNetworkResponse
    eng_data: EnkaNetworkResponse
    cache: EnkaNetworkResponse
    eng_cache: EnkaNetworkResponse

class TopPadding(BaseModel):
    with_title: int
    without_title: int

class DynamicBackgroundInput(BaseModel):
    top_padding: TopPadding
    left_padding: int
    right_padding: int
    bottom_padding: int
    card_height: int
    card_width: int
    card_x_padding: int
    card_y_padding: int
    card_num: int
    max_card_num: int
    background_color: str
    draw_title: bool = True