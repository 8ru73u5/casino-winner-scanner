from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from cws.api.models import Tip, TeamInfo
from cws.bots.patterns import AbstractPatternMatcher


@dataclass
class Team:
    id: int
    name: str
    total_points: int
    previous_total_points: int
    current_phase_points: int = 0

    def __init__(self, team_info: TeamInfo, previous_team_info: TeamInfo):
        self.id = team_info.id
        self.name = team_info.name
        self.total_points = team_info.score
        self.previous_total_points = previous_team_info.score

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'total_points': self.total_points,
            'previous_total_points': self.previous_total_points,
            'current_phase_points': self.current_phase_points
        }

    def has_scored_any_points(self) -> bool:
        return self.total_points != self.previous_total_points


class PhaseType(Enum):
    QUARTER = 'quarter'
    HALF = 'half'
    OVERTIME = 'overtime'


class BasketballMatcher(AbstractPatternMatcher):
    SPORT_ID = 4

    def _parse_event(self):
        division_type = self._event.raw_api_response_data['sb']['gcp']['gpn'].lower()

        self.current_quarter = None
        self.current_half = None

        if division_type.endswith('quarter'):
            self.phase_type = PhaseType.QUARTER
            self.current_quarter = int(division_type[0])
            self.current_half = 1 if self.current_quarter <= 2 else 2
        elif division_type.endswith('half'):
            self.phase_type = PhaseType.HALF
            self.current_quarter = None
            self.current_half = int(division_type[0])
        elif division_type == 'overtime':
            self.phase_type = PhaseType.OVERTIME
        else:
            raise ValueError(f'Basketball phase name should be either quarter, half or overtime: {division_type}')

        self.first_team = Team(self._event.first_team, self._previous_event.first_team)
        self.second_team = Team(self._event.second_team, self._previous_event.second_team)

        if self.first_team.total_points > self.second_team.total_points:
            self.current_leader = self.first_team
        elif self.first_team.total_points < self.second_team.total_points:
            self.current_leader = self.second_team
        else:
            self.current_leader = None

        current_phase_id = self._event.raw_api_response_data['sb']['gcp']['gpi']
        current_phase_team_details = [
            x for x in self._event.raw_api_response_data['sb']['gsl']
            if x['gpi'] == current_phase_id
        ]

        for x in current_phase_team_details:
            if x['spi'] == self.first_team.id:
                self.first_team.current_phase_points = int(x['v'])
            else:
                self.second_team.current_phase_points = int(x['v'])

        dup = 1

    def to_dict(self) -> dict:
        pass

    def check_for_matches(self) -> List[Tip]:
        selection_ids = [
            self._check_race_to_points()
        ]

        return [x for x in selection_ids if x is not None]

    def _check_race_to_points(self) -> Optional[Tip]:
        if self.phase_type is not PhaseType.QUARTER or self.current_leader is None:
            return

        market_id = 4
        bet_id = 8404

        tip_groups = self.get_tip_groups(market_id, bet_id)
        if tip_groups is None:
            return

        current_quarter_groups = [
            tg for tg in tip_groups
            if int(tg[0].tip.bet_group_name_real.split()[1]) == self.current_quarter
        ]

        if len(current_quarter_groups) == 0:
            return

        min_goal_group = min(current_quarter_groups, key=lambda tg: int(tg[0].tip.bet_group_name_real.split()[-2]))
        goal = int(min_goal_group[0].tip.bet_group_name_real.split()[-2])

        if self.current_leader.current_phase_points >= goal:
            if self.current_leader is self.first_team:
                team = 'Home'
            else:
                team = 'Away'

            return next((t for t in min_goal_group if t.tip.name == team), None)
