from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from requests import Session, HTTPError

from cws.bots.bet_history_item import BetHistoryItem


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


class BetBot:
    def __init__(self, username: str, password: str, bookmaker: BookmakerType, log_in: bool = False):
        self._username = username
        self._password = password
        self.bookmaker = bookmaker

        self._session = None
        self._session_token = None
        self._sportsbook_token = None
        self._customer_id = None

        if log_in:
            self.login()
            self.get_sportsbook_token()

    def __del__(self):
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

        return self._session

    def login(self):
        data = {
            'username': self._username,
            'password': self._password
        }

        print('Logging in...', end=' ')
        r = self._get_session().post(self.bookmaker.url + '/api/v1/single-sign-on-sessions', json=data)
        r.raise_for_status()
        print('done!')

        data = r.json()
        self._session_token = data['sessionToken']
        self._customer_id = data['customerId']
        self._get_session().headers.update({'sessionToken': self._session_token})

    def logout(self):
        if not self.has_session():
            return

        print('Logging out...', end=' ')
        r = self._get_session().delete(self.bookmaker.url + '/api/v1/current-single-sign-on-session')
        r.raise_for_status()
        print('done!')

        self._reset_session()

    @bet_login_required
    def get_sportsbook_token(self):
        print('Getting sportsbook token...', end=' ')
        r = self._get_session().get(f'{self.bookmaker.url}/api/sb/v2/sportsbookgames/{self.bookmaker.name}/{self._customer_id}')
        r.raise_for_status()
        print('done!')

        self._sportsbook_token = r.json()['token']

    @bet_login_required
    def get_wallet_balance(self) -> WalletBalance:
        print('Getting wallet balance...', end=' ')
        r = self._get_session().get(self.bookmaker.url + '/api/v2/wallet/balance')
        r.raise_for_status()
        print('done!')

        return WalletBalance.from_json(r.json()['balance'])

    @bet_login_required
    def get_bet_history(self) -> List[BetHistoryItem]:
        if self._sportsbook_token is None:
            self.get_sportsbook_token()

        params = {
            'couponFilter': 'Settled',
            'page': 1,
            'pageSize': 19
        }

        headers = {'sportsbookToken': self._sportsbook_token}

        print('Getting bet history...', end=' ')
        r = self._get_session().get(self.bookmaker.url + '/api/sb/v1/widgets/coupon-history/v1', headers=headers, params=params)
        r.raise_for_status()
        print('done!')

        return [BetHistoryItem.from_json(bet) for bet in r.json()['data']['coupons']]
