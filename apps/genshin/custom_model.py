import io
from typing import Dict, List, Optional
from pydantic import BaseModel
import discord
import genshin

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
    recents: List[Dict[str, str|int]]

    
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