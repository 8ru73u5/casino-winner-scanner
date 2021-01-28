from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple

from .errors import InvalidApiResponseError


@dataclass
class Event:
    id: int
    time: Optional[Tuple[int, int]]  # (minutes, seconds)
    sport_id: int
    sport_name: str
    league_name: str
    first_team: TeamInfo
    second_team: TeamInfo
    markets: List[Market]

    def has_time_info(self) -> bool:
        return self.time is not None

    def has_score_info(self) -> bool:
        return self.first_team.score is not None and self.second_team.score is not None

    @property
    def minutes(self) -> Optional[int]:
        return self.time[0] if self.has_time_info() else None

    @property
    def seconds(self) -> Optional[int]:
        return self.time[1] if self.has_time_info() else None

    @property
    def time_pretty(self) -> str:
        return f'{self.minutes:02}:{self.seconds:02}' if self.has_time_info() else '<no time info>'

    @staticmethod
    def from_json(data: dict) -> Event:
        try:
            if data['ss'] is not None:
                team1_score, team2_score = [int(s) for s in data['ss'].split(' - ')]
            else:
                team1_score = team2_score = None

            if data['sb'] is not None:
                time = (data['sb']['gmc']['m'], data['sb']['gmc']['s'])
            else:
                time = None

            event = Event(
                id=data['ei'],
                time=time,
                sport_id=data['ci'],
                sport_name=data['cn'],
                league_name=data['scn'],
                first_team=TeamInfo(name=data['epl'][0]['pn'], score=team1_score),
                second_team=TeamInfo(name=data['epl'][1]['pn'], score=team2_score),
                markets=[Market.from_json(market) for market in data['ml']]
            )
        except (KeyError, ValueError, IndexError) as e:
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
class Market:
    group_id: int
    group_name: str
    bet_group_id: int
    bet_group_name: str
    tips: List[Tip]

    @staticmethod
    def _parse_bet_group_name(bgn: str) -> str:
        return bgn.replace('#line#', '×')

    @staticmethod
    def from_json(data: dict) -> Market:
        try:
            market = Market(
                group_id=data['bggi'],
                group_name=data['bggn'],
                bet_group_id=data['bgi'],
                bet_group_name=Market._parse_bet_group_name(data['bgn']),
                tips=[Tip.from_json(tip) for tip in data['msl']]
            )
        except (KeyError, TypeError) as e:
            raise InvalidApiResponseError(data, e)

        return market

    def __hash__(self):
        return hash((self.group_id, self.bet_group_id))


@dataclass
class Tip:
    id: int
    name: str
    odds: float

    @staticmethod
    def from_json(data: dict) -> Tip:
        try:
            tip = Tip(id=data['msi'], name=data['mst'], odds=data['msp'])
        except KeyError as e:
            raise InvalidApiResponseError(data, e)

        return tip
