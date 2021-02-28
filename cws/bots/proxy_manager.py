from random import choice
from typing import Union, List, Dict

from requests import get

from cws.config import AppConfig


class ProxyManager:
    WEBSHARE_API_TOKEN = None
    WEBSHARE_API_URL = 'https://proxy.webshare.io/api'

    @classmethod
    def _get_token(cls) -> str:
        if cls.WEBSHARE_API_TOKEN is None:
            cls.WEBSHARE_API_TOKEN = AppConfig.get(AppConfig.Variables.WEBSHARE_API_TOKEN)

        return cls.WEBSHARE_API_TOKEN

    @classmethod
    def get_proxy_list(cls, countries: Union[str, List[str]] = None) -> List[Dict[str, str]]:
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

        proxies = []
        for proxy in r.json()['results']:
            username = proxy['username']
            password = proxy['password']
            ip = proxy['proxy_address']
            port = proxy['ports']['http']

            proxies.append({
                'https': f'http://{username}:{password}@{ip}:{port}'
            })

        return proxies

    @classmethod
    def get_random_proxy(cls, countries: Union[str, List[str]] = None) -> Dict[str, str]:
        return choice(cls.get_proxy_list(countries))
