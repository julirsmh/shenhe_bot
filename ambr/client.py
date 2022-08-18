import json
import os
import time
from typing import Dict, KeysView, List, Optional

import aiohttp

from ambr.constants import CITIES, LANGS
from ambr.endpoints import BASE, ENDPOINTS, STATIC_ENDPOINTS
from ambr.models import Character, CharacterUpgrade, City, Domain, Material, Weapon, WeaponUpgrade


class AmbrTopAPI:
    def __init__(self, session: aiohttp.ClientSession, lang: str = 'en'):
        self.session = session
        self.lang = lang
        if self.lang not in LANGS:
            raise ValueError(
                f'Invalid language: {self.lang}, valid values are: {LANGS.keys()}')
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        cache = {}
        for lang in list(LANGS.keys()):
            if lang not in cache:
                cache[lang] = {}
            for endpoint in list(ENDPOINTS.keys()):
                cache[lang][endpoint] = self._request_from_cache(endpoint)
        for static_endpoint in list(STATIC_ENDPOINTS.keys()):
            cache[static_endpoint] = self._request_from_cache(static_endpoint, static=True)
            
        return cache
    
    def _get_cache(self, endpoint: str, static: bool = False) -> Dict:
        if static:
            return self.cache[endpoint]
        else:
            return self.cache[self.lang][endpoint]
    
    async def _request_from_endpoint(self, endpoint: str, static: bool = False) -> Dict:
        if static:
            endpoint_url = f'{BASE}static/{STATIC_ENDPOINTS.get(endpoint)}'
        else:
            endpoint_url = f'{BASE}{self.lang}/{ENDPOINTS.get(endpoint)}'
        async with self.session.get(endpoint_url) as r:
            endpoint_data = await r.json()
        if 'code' in endpoint_data:
            raise ValueError(
                f'Invalid endpoint = {endpoint} | URL = {endpoint_url}')
        return endpoint_data

    def _request_from_cache(self, endpoint: str, static: bool = False) -> Dict:
        if static:
            with open(f'ambr/cache/{STATIC_ENDPOINTS.get(endpoint)}.json') as f:
                endpoint_data = json.load(f)
        else:
            with open(f'ambr/cache/{self.lang}/{ENDPOINTS.get(endpoint)}.json') as f:
                endpoint_data = json.load(f)

        return endpoint_data

    async def _update_cache(self) -> None:
        endpoints = list(ENDPOINTS.keys())
        for endpoint in endpoints:
            data = await self._request_from_endpoint(endpoint)
            path = f'ambr/cache/{self.lang}'
            if not os.path.exists(path):
                os.makedirs(path)
            with open(f'ambr/cache/{self.lang}/{ENDPOINTS.get(endpoint)}.json', 'w+') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        static_endpoints = list(STATIC_ENDPOINTS.keys())
        for static_endpoint in static_endpoints:
            data = await self._request_from_endpoint(static_endpoint, static=True)
            with open(f'ambr/cache/{STATIC_ENDPOINTS.get(static_endpoint)}.json', 'w+') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    def get_material(self, id: Optional[int] = None) -> List[Material]:
        result = []
        data = self._get_cache('material')
        for material_id, material_info in data['data']['items'].items():
            if id is not None:
                if id == material_info['id']:
                    result.append(Material(**material_info))
            else:
                result.append(Material(**material_info))

        return result
    
    def get_character(self, id: Optional[str] = None) -> List[Character]:
        result = []
        data = self._get_cache('character')
        for character_id, character_info in data['data']['items'].items():
            if id is not None:
                if id == character_id:
                    result.append(Character(**character_info))
            else:
                result.append(Character(**character_info))
                
        return result
    
    def get_weapon(self, id: Optional[int] = None) -> List[Weapon]:
        result = []
        data = self._get_cache('weapon')
        for weapon_id, weapon_info in data['data']['items'].items():
            if id is not None:
                if id == int(weapon_id):
                    result.append(Weapon(**weapon_info))
            else:
                result.append(Weapon(**weapon_info))
                
        return result

    def get_character_upgrade(self, character_id: Optional[str] = None) -> List[CharacterUpgrade]:
        result = []
        data = self._get_cache('upgrade', static=True)
        for upgrade_id, upgrade_info in data['data']['avatar'].items():
            item_list = []
            for material_id, rarity in upgrade_info['items'].items():
                material = self.get_material(id=int(material_id))
                item_list.append(material[0])
            upgrade_info['item_list'] = item_list
            upgrade_info['character_id'] = upgrade_id
            if character_id is not None:
                if character_id == upgrade_id:
                    result.append(CharacterUpgrade(**upgrade_info))
            else:
                result.append(CharacterUpgrade(**upgrade_info))
                
        return result
    
    def get_weapon_upgrade(self, character_id: Optional[str] = None) -> List[WeaponUpgrade]:
        result = []
        data = self._get_cache('upgrade', static=True)
        for upgrade_id, upgrade_info in data['data']['weapon'].items():
            item_list = []
            for material_id, rarity in upgrade_info['items'].items():
                material = self.get_material(id=int(material_id))
                item_list.append(material[0])
            upgrade_info['item_list'] = item_list
            upgrade_info['weapon_id'] = upgrade_id
            if character_id is not None:
                if character_id == upgrade_id:
                    result.append(WeaponUpgrade(**upgrade_info))
            else:
                result.append(WeaponUpgrade(**upgrade_info))
                
        return result

    def get_domain(self, id: Optional[int] = None) -> List[Domain]:
        result = []
        data = self._get_cache('domain')
        for weekday, domain_dict in data['data'].items():
            weekday_int = time.strptime(weekday, "%A").tm_wday
            for domain_full_name, domain_info in domain_dict.items():
                city_id = domain_info['city']
                city = City(id=city_id, name=CITIES.get(city_id)[self.lang])
                rewards = []
                for reward in domain_info['reward']:
                    if len(str(reward)) == 6:
                        material = self.get_material(id=reward)
                        rewards.append(material[0])
                domain_info['city'] = city
                domain_info['weekday'] = weekday_int
                domain_info['reward'] = rewards
                if id is not None:
                    if id == domain_info['id']:
                        result.append(Domain(**domain_info))
                else:
                    result.append(Domain(**domain_info))

        return result
