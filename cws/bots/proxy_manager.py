from random import choice
from threading import Lock
from typing import Union, List, Dict, Set

from requests import get

from cws.config import AppConfig


class ProxyManager:
    WEBSHARE_API_TOKEN = None
    WEBSHARE_API_URL = 'https://proxy.webshare.io/api'

    USED_PROXIES = set()
    USED_PROXIES_LOCK = Lock()

    @classmethod
    def _get_token(cls) -> str:
        if cls.WEBSHARE_API_TOKEN is None:
            cls.WEBSHARE_API_TOKEN = AppConfig.get(AppConfig.Variables.WEBSHARE_API_TOKEN)

        return cls.WEBSHARE_API_TOKEN

    @classmethod
    def get_proxy_list(cls, countries: Union[str, List[str]] = None) -> Set[str]:
        if countries is None:
            params = {}
        elif isinstance(countries, list):
            params = {'countries': '-'.join(countries)}
        else:
            params = {'countries': countries}

        headers = {
            'Authorization': f'Token {cls._get_token()}'
        }

        r = get(cls.WEBSHARE_API_URL + '/proxy/list', headers=headers, params=params)
        r.raise_for_status()

        proxies = set()
        for proxy in r.json()['results']:
            username = proxy['username']
            password = proxy['password']
            ip = proxy['proxy_address']
            port = proxy['ports']['http']

            proxies.add(f'http://{username}:{password}@{ip}:{port}')

        return proxies

    @classmethod
    def get_random_proxy(cls, countries: Union[str, List[str]] = None) -> Dict[str, str]:
        proxies = cls.get_proxy_list(countries)

        with cls.USED_PROXIES_LOCK:
            available_proxies = proxies.difference(cls.USED_PROXIES)

            if len(proxies) == 0 or len(available_proxies) == 0:
                raise RuntimeError('No available proxies')

            proxy = choice(list(available_proxies))
            cls.USED_PROXIES.add(proxy)

        return {'https': proxy}

    @classmethod
    def remove_proxy_from_used_proxy_list(cls, proxy: str):
        with cls.USED_PROXIES_LOCK:
            cls.USED_PROXIES.discard(proxy)

    @classmethod
    def set_used_proxies(cls, new_used_proxy_list: Set[str]):
        with cls.USED_PROXIES_LOCK:
            cls.USED_PROXIES = new_used_proxy_list
