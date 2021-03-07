from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Set, Dict

from .errors import InvalidApiResponseError


@dataclass
class Event:
    id: int
    time: Optional[Tuple[int, int]]  # (minutes, seconds)
    is_break: Optional[int]
    game_phase: str
    sport_id: int
    sport_name: str
    league_name: str
    first_team: TeamInfo
    second_team: TeamInfo
    tips: List[Tip]
    raw_api_response_data: dict
    phase_related_bet_names: Set[str] = field(default_factory=set)
    current_phase_bet_names: Optional[Set[str]] = None
    deduced_current_phase: Optional[Dict[str, int]] = None

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

    SPORT_PHASE_NAMES = {
        1: ['half'],
        2: ['period'],
        3: ['half'],
        4: ['quarter', 'half'],
        9: ['set'],
        11: ['set', 'game'],
        17: ['frame'],
        119: ['map'],
        138: ['set' 'game']
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

    def _generate_phase_related_bet_name_list(self):
        phase_names = Event.SPORT_PHASE_NAMES.get(self.sport_id)

        if phase_names is None:
            return

        bet_names = {t.bet_group_name_real.lower() for t in self.tips}
        current_phase_bets = set()
        self.deduced_current_phase = {}

        for phase_name in phase_names:
            phase_related_bets = [bet_name for bet_name in bet_names if phase_name in bet_name]

            pattern_pre = re.compile('(\d+)\S* ' + phase_name, re.IGNORECASE)
            pattern_post = re.compile(phase_name + ' (\d+)', re.IGNORECASE)

            bet_names_with_phases = []

            for bet_name in phase_related_bets:
                match = pattern_pre.search(bet_name) or pattern_post.search(bet_name)
                if match is not None:
                    bet_names_with_phases.append((bet_name, int(match.group(1))))

            if len(bet_names_with_phases) == 0:
                continue

            current_phase = min(x[1] for x in bet_names_with_phases)
            current_phase_bets.update(x[0] for x in bet_names_with_phases if x[1] == current_phase)

            self.deduced_current_phase[phase_name] = current_phase
            self.phase_related_bet_names.update(x[0] for x in bet_names_with_phases)

        self.current_phase_bet_names = current_phase_bets

    def is_tip_eligible_for_notification(self, tip: Tip) -> bool:
        if self.sport_id not in Event.SPORT_PHASE_NAMES:
            return True

        if self.current_phase_bet_names is None:
            self._generate_phase_related_bet_name_list()

        bet_name = tip.bet_group_name_real.lower()

        if bet_name not in self.phase_related_bet_names:
            return True
        else:
            return bet_name in self.current_phase_bet_names

    def deduce_current_phase(self) -> Dict[str, int]:
        if self.deduced_current_phase is None:
            self._generate_phase_related_bet_name_list()

        return self.deduced_current_phase

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
                is_break=game_phase == 'Halftime',
                game_phase=game_phase,
                sport_id=data['ci'],
                sport_name=data['cn'],
                league_name=data['scn'],
                first_team=TeamInfo(id=data['epl'][0]['pi'], name=data['epl'][0]['pn'], score=team1_score),
                second_team=TeamInfo(id=data['epl'][1]['pi'], name=data['epl'][1]['pn'], score=team2_score),
                tips=Tip.from_json(data),
                raw_api_response_data=data,
                phase_related_bet_names=set(),
                current_phase_bet_names=None
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
    id: int
    name: str
    score: Optional[int]

    def __eq__(self, other: TeamInfo) -> bool:
        return self.id == other.id


@dataclass
class Tip:
    id: int
    unique_tip_group_id: int
    name: str
    odds: float
    market_group_id: int
    market_group_name: str
    bet_group_id: int
    bet_group_name: str
    bet_group_name_real: str
    is_active: bool
    selection_id: str
    associated_player_id: Optional[int]

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
                unique_tip_group_id = market['mi']
                market_group_id = market['bggi']
                market_group_name = market['bggn']
                bet_group_id = market['bgi']
                bet_group_name = Tip.parse_bet_group_name(market['bgn'])
                bet_group_name_real = market['mn']
                is_active = market['ms'] == 10

                for tip in market['msl']:
                    tips.append(Tip(
                        id=tip['msi'],
                        unique_tip_group_id=unique_tip_group_id,
                        name=tip['mst'],
                        odds=tip['msp'],
                        market_group_id=market_group_id,
                        market_group_name=market_group_name,
                        bet_group_id=bet_group_id,
                        bet_group_name=bet_group_name,
                        bet_group_name_real=bet_group_name_real,
                        is_active=is_active,
                        selection_id=tip['msit'],
                        associated_player_id=pid if (pid := tip['pi']) != 0 else None
                    ))
        except (KeyError, TypeError, ValueError) as e:
            raise InvalidApiResponseError(data, e)

        return tips

    def __hash__(self):
        return hash((self.market_group_id, self.bet_group_id, self.id))
