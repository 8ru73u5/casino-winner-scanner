from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from json import dumps
from json.decoder import JSONDecodeError
from typing import List

from requests import Session, HTTPError

from cws.bots.bet_history_item import BetHistoryItem
from cws.bots.proxy_manager import ProxyManager


class BookmakerType(Enum):
    BETSSON = {
        'url': 'https://www.betsson.com',
        'name': 'betsson',
        'base_headers': {
            'marketCode': 'en',
            'brandId': 'e123be9a-fe1e-49d0-9200-6afcf20649af'
        }
    }
    BETSAFE = {
        'url': 'https://www.betsafe.com',
        'name': 'betsafe',
        'base_headers': {
            'marketCode': 'en',
            'brandId': '11a81f20-a960-49e4-8748-51f750c1b27c'
        }
    }

    @property
    def url(self):
        return self.value['url']

    @property
    def name(self):
        return self.value['name']

    @property
    def base_headers(self):
        return self.value['base_headers']


class CouponFilterType(Enum):
    ALL = 'All'
    OPEN = 'Open'
    SETTLED = 'Settled'


@dataclass
class WalletBalance:
    total_amount: float
    withdrawable_amount: float
    locked_amount: float
    currency: str

    @staticmethod
    def from_json(data: dict) -> WalletBalance:
        return WalletBalance(
            total_amount=data['totalAmount'],
            withdrawable_amount=data['withdrawableAmount'],
            locked_amount=data['lockedAmount'],
            currency=data['currencyCode'],
        )

    @property
    def funds(self) -> str:
        return f'{self.total_amount} {self.currency}'


def bet_login_required(method):
    def wrapper(bet_bot: BetBot, *args, **kwargs):
        auto_login_performed = False

        if not bet_bot.has_session():
            print('Bot is not logged in! Performing auto-login...')
            bet_bot.login()
            auto_login_performed = True

        try:
            return method(bet_bot, *args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 401 and not auto_login_performed:
                bet_bot.login()
                return method(bet_bot, *args, **kwargs)
            else:
                raise

    return wrapper


class BotInvalidCredentialsError(Exception):
    pass


class BetBot:
    def __init__(self, username: str, password: str, bookmaker: BookmakerType, country_code: str, is_enabled: bool, log_in: bool = False):
        self._username = username
        self._password = password
        self.bookmaker = bookmaker
        self._proxy_country_code = country_code
        self.is_enabled = is_enabled

        self._session = None
        self._session_token = None
        self._sportsbook_token = None
        self._customer_id = None

        self._wallet_balance = None

        if log_in:
            self.login()
            self.get_wallet_balance(reload=True)
            self._get_sportsbook_token()

    def __del__(self):
        if self.has_session():
            self.logout()

    def has_session(self) -> bool:
        return self._session is not None

    def _reset_session(self):
        if self.has_session():
            self._session.close()
            self._session = None

        self._session_token = None
        self._sportsbook_token = None
        self._customer_id = None

    def _get_session(self) -> Session:
        if not self.has_session():
            self._session = Session()
            self._session.headers.update(self.bookmaker.base_headers)
            self._refresh_proxy()

        return self._session

    def _refresh_proxy(self):
        if self.has_session():
            self._session.proxies = ProxyManager.get_random_proxy(self._proxy_country_code)

    def login(self, get_sportsbook_token: bool = False):
        self._reset_session()

        data = {
            'username': self._username,
            'password': self._password
        }

        print('Logging in...', end=' ')
        r = self._get_session().post(self.bookmaker.url + '/api/v1/single-sign-on-sessions', json=data)

        try:
            r.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 400:
                try:
                    if e.response.json()['code'] == 'E_SESSIONS_LOGIN_INVALIDCREDENTIALS':
                        raise BotInvalidCredentialsError()
                except (JSONDecodeError, KeyError):
                    pass

            raise

        print('done!')

        data = r.json()
        self._session_token = data['sessionToken']
        self._customer_id = data['customerId']
        self._get_session().headers.update({'sessionToken': self._session_token})

        if get_sportsbook_token:
            self._get_sportsbook_token()

    def logout(self):
        if not self.has_session():
            return

        print('Logging out...', end=' ')
        r = self._get_session().delete(self.bookmaker.url + '/api/v1/current-single-sign-on-session')
        r.raise_for_status()
        print('done!')

        self._reset_session()

    @bet_login_required
    def _get_sportsbook_token(self):
        print('Getting sportsbook token...', end=' ')
        r = self._get_session().get(f'{self.bookmaker.url}/api/sb/v2/sportsbookgames/betsson/{self._customer_id}')
        r.raise_for_status()
        print('done!')

        self._sportsbook_token = r.json()['token']

    @bet_login_required
    def get_wallet_balance(self, reload: bool = False) -> WalletBalance:
        if reload:
            print('Getting wallet balance...', end=' ')
            r = self._get_session().get(self.bookmaker.url + '/api/v2/wallet/balance')
            r.raise_for_status()
            print('done!')

            self._wallet_balance = WalletBalance.from_json(r.json()['balance'])

        return self._wallet_balance

    @bet_login_required
    def get_bet_history(self, coupon_filter: CouponFilterType = CouponFilterType.ALL) -> List[BetHistoryItem]:
        if self._sportsbook_token is None:
            self._get_sportsbook_token()

        params = {
            'couponFilter': coupon_filter.value,
            'page': 1,
            'pageSize': 19
        }

        headers = {'sportsbookToken': self._sportsbook_token}

        print('Getting bet history...', end=' ')
        r = self._get_session().get(self.bookmaker.url + '/api/sb/v1/widgets/coupon-history/v1', headers=headers, params=params)
        r.raise_for_status()
        print('done!')

        return [BetHistoryItem.from_json(bet) for bet in r.json()['data']['coupons']]

    @bet_login_required
    def place_bet(self, stake: float, odds: float, market_selection_id: str):
        if self._sportsbook_token is None:
            self._get_sportsbook_token()

        data = {
            'acceptOddsChanges': False,
            'bets': [
                {
                    'stake': stake,
                    'stakeForReview': 0,
                    'betSelections': [
                        {
                            'marketSelectionId': market_selection_id,
                            'odds': odds
                        }
                    ]
                }
            ]
        }

        headers = {'sportsbookToken': self._sportsbook_token}

        print('Placing bet...', end=' ')
        r = self._get_session().post(self.bookmaker.url + '/api/sb/v1/coupons', headers=headers, json=data)
        r.raise_for_status()
        print('done! Response:')

        # TODO: Parse the response and extract success/failure information
        print(dumps(r.json(), ensure_ascii=False, indent=2))
