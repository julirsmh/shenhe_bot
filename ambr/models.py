from typing import List

from data.game.elements import convert_elements
from pydantic import BaseModel, Field, validator


class City(BaseModel):
    id: int
    name: str


class Weapon(BaseModel):
    id: int
    rarity: int = Field(alias="rank")
    type: str
    name: str
    icon: str
    beta: bool = False
    default_icon: bool = False

    @validator("icon")
    def get_icon_url(cls, v):
        icon_url = f"https://api.ambr.top/assets/UI/{v}.png"
        return icon_url

    @validator("default_icon")
    def check_default_icon(cls, v, values):
        defaults = [
            "https://api.ambr.top/assets/UI/UI_EquipIcon_Sword_Blunt.png",
            "https://api.ambr.top/assets/UI/UI_EquipIcon_Claymore_Aniki.png",
            "https://api.ambr.top/assets/UI/UI_EquipIcon_Pole_Gewalt.png",
            "https://api.ambr.top/assets/UI/UI_EquipIcon_Catalyst_Apprentice.png",
            "https://api.ambr.top/assets/UI/UI_EquipIcon_Bow_Hunters.png",
        ]
        if values["icon"] in defaults:
            return True


class Character(BaseModel):
    id: str
    name: str
    rairty: int = Field(alias="rank")
    element: str
    weapon_type: str = Field(alias="weaponType")
    icon: str
    beta: bool = False

    @validator("icon")
    def get_icon_url(cls, v):
        icon_url = f"https://api.ambr.top/assets/UI/{v}.png"
        return icon_url

    @validator("element")
    def get_element_name(cls, v):
        element_name = convert_elements.get(v)
        return element_name


class Material(BaseModel):
    id: int
    name: str
    type: str
    recipe: bool
    map_mark: bool = Field(alias="mapMark")
    icon: str
    rarity: int = Field(alias="rank")
    beta: bool = False

    @validator("icon")
    def get_icon_url(cls, v, values):
        if values["type"] == "custom":
            return "https://i.imgur.com/ByIyBa7.png"
        elif values["id"] == 202:
            return "https://i.imgur.com/EbXcKOk.png"
        else:
            icon_url = f"https://api.ambr.top/assets/UI/{v}.png"
            return icon_url


class Domain(BaseModel):
    id: int
    name: str
    rewards: List[Material] = Field(alias="reward")
    city: City
    weekday: int


class CharacterUpgrade(BaseModel):
    character_id: str
    items: List[Material] = Field(alias="item_list")
    beta: bool = False


class WeaponUpgrade(BaseModel):
    weapon_id: int
    items: List[Material] = Field(alias="item_list")
    beta: bool = False
