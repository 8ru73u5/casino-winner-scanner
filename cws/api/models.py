from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, List, Tuple

from .errors import InvalidApiResponseError


@dataclass
class Event:
    id: int
    time: Optional[Tuple[int, int]]  # (minutes, seconds)
    game_phase: str
    sport_id: int
    sport_name: str
    league_name: str
    first_team: TeamInfo
    second_team: TeamInfo
    tips: List[Tip]

    SPORT_EMOJI = {
        1: '⚽️',
        2: '🏒',
        3: '🤾',
        4: '🏀',
        8: '🏉',
        9: '🏐',
        11: '🎾',
        15: '⛳',
        17: '🎱',
        26: '🏏',
        34: '🎯',
        92: '❄',
        119: '🎮',
        138: '🏓'
    }

    def has_time_info(self) -> bool:
        return self.time is not None

    def has_score_info(self) -> bool:
        return self.first_team.score is not None and self.second_team.score is not None

    def get_time_or_phase(self) -> str:
        if self.has_time_info():
            minutes, seconds = self.time
            return f'{minutes:02}:{seconds:02}'
        elif self.game_phase is not None:
            return self.game_phase
        else:
            return '―'

    def get_score(self) -> str:
        if self.has_score_info():
            return f'{self.first_team.score}:{self.second_team.score}'
        else:
            return '―'

    def get_sport_name_or_emoji(self) -> str:
        return Event.SPORT_EMOJI.get(self.sport_id) or self.sport_name

    @property
    def link(self):
        return f'https://www.casinowinner.com/en/live-betting#/event/{self.id}'

    @staticmethod
    def from_json(data: dict) -> Event:
        try:
            if data['ss'] is not None:
                team1_score, team2_score = [int(s) for s in data['ss'].split(' - ')]
            else:
                team1_score = team2_score = None

            if data['sb'] is not None:
                time = (data['sb']['gmc']['m'], data['sb']['gmc']['s'])
                if time == (0, 0):
                    time = None
                game_phase = data['sb']['gcp']['gpn']
            else:
                time = None
                game_phase = None

            event = Event(
                id=data['ei'],
                time=time,
                game_phase=game_phase,
                sport_id=data['ci'],
                sport_name=data['cn'],
                league_name=data['scn'],
                first_team=TeamInfo(name=data['epl'][0]['pn'], score=team1_score),
                second_team=TeamInfo(name=data['epl'][1]['pn'], score=team2_score),
                tips=Tip.from_json(data)
            )
        except (KeyError, ValueError, IndexError, TypeError) as e:
            raise InvalidApiResponseError(data, e)

        return event

    @staticmethod
    def from_json_multiple(data: dict) -> List[Event]:
        try:
            events = [Event.from_json(event) for event in data['el']]
        except (KeyError, TypeError) as e:
            raise InvalidApiResponseError(data, e)

        return events

    def __hash__(self):
        return self.id


@dataclass
class TeamInfo:
    name: str
    score: Optional[int]


@dataclass
class Tip:
    id: int
    name: str
    odds: float
    market_group_id: int
    market_group_name: str
    bet_group_id: int
    bet_group_name: str
    bet_group_name_real: str
    is_active: bool

    BGN_TEMPLATE_REGEX = re.compile('#[^#]+#')

    @classmethod
    def parse_bet_group_name(cls, bgn: str) -> str:
        if '#' in bgn:
            return re.sub(cls.BGN_TEMPLATE_REGEX, '∅', bgn)
        else:
            return bgn

    @staticmethod
    def from_json(data: dict) -> List[Tip]:
        tips = []

        try:
            for market in data['ml']:
                market_group_id = market['bggi']
                market_group_name = market['bggn']
                bet_group_id = market['bgi']
                bet_group_name = Tip.parse_bet_group_name(market['bgn'])
                bet_group_name_real = market['mn']
                is_active = market['ms'] == 10

                for tip in market['msl']:
                    tips.append(Tip(
                        id=tip['msi'],
                        name=tip['mst'],
                        odds=tip['msp'],
                        market_group_id=market_group_id,
                        market_group_name=market_group_name,
                        bet_group_id=bet_group_id,
                        bet_group_name=bet_group_name,
                        bet_group_name_real=bet_group_name_real,
                        is_active=is_active
                    ))
        except (KeyError, TypeError, ValueError) as e:
            raise InvalidApiResponseError(data, e)

        return tips

    def __hash__(self):
        return hash((self.market_group_id, self.bet_group_id, self.id))
