from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from cws.api.models import Tip, TeamInfo
from cws.bots.patterns import AbstractPatternMatcher
from cws.bots.patterns.abstract_pattern_matcher import check


@dataclass
class Team:
    id: int
    name: str
    total_points: int
    previous_total_points: int
    current_phase_points: int = 0
    previous_phase_points: Optional[int] = None

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
            'current_phase_points': self.current_phase_points,
            'previous_phase_points': self.previous_phase_points
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
        previous_division_type = self._previous_event.raw_api_response_data['sb']['gcp']['gpn'].lower()

        self.current_quarter = None
        self.current_half = None
        self.phase_changed = division_type != previous_division_type

        if division_type.endswith('quarter'):
            self.phase_type = PhaseType.QUARTER
            self.current_quarter = int(division_type[0])
            self.current_half = 1 if self.current_quarter <= 2 else 2
        elif division_type.endswith('half'):
            self.phase_type = PhaseType.HALF
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
        if self.phase_type is PhaseType.QUARTER and not (4 >= current_phase_id >= 1):
            raise ValueError(f'Wrong phase id for phase type: QUARTER: {current_phase_id}')
        elif self.phase_type is PhaseType.HALF and not (29 >= current_phase_id >= 28):
            raise ValueError(f'Wrong phase id for phase type: HALF: {current_phase_id}')

        current_phase_team_details = [
            x for x in self._event.raw_api_response_data['sb']['gsl']
            if x['gpi'] == current_phase_id
        ]

        for x in current_phase_team_details:
            if x['spi'] == self.first_team.id:
                self.first_team.current_phase_points = int(x['v'])
            else:
                self.second_team.current_phase_points = int(x['v'])

        if self.phase_changed:
            previous_phase_id = self._previous_event.raw_api_response_data['sb']['gcp']['gpi']
            previous_phase_team_details = [
                x for x in self._previous_event.raw_api_response_data['sb']['gsl']
                if x['gpi'] == previous_phase_id
            ]

            for x in previous_phase_team_details:
                if x['spi'] == self.first_team.id:
                    self.first_team.previous_phase_points = int(x['v'])
                else:
                    self.second_team.previous_phase_points = int(x['v'])

            self.previous_phase_total_points = self.first_team.previous_phase_points + self.second_team.previous_phase_points

        self.current_phase_total_points = self.first_team.current_phase_points + self.second_team.current_phase_points
        self.total_game_points = self.first_team.total_points + self.second_team.total_points

    def to_dict(self) -> dict:
        return {
            'home': self.first_team.to_dict(),
            'away': self.second_team.to_dict(),
            'current_quarter': self.current_quarter,
            'current_half': self.current_half,
            'phase_changed': self.phase_changed,
            'current_phase_total_points': self.current_phase_total_points,
            'previous_phase_total_points': self.previous_phase_total_points,
            'total_game_points': self.total_game_points
        }

    @check
    def phase_race_to_points_home_away(self) -> Optional[Tip]:
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

    @check
    def phase_total_points_over_under(self) -> List[Tip]:
        quarter = self._phase_total_points_over_under(PhaseType.QUARTER)
        half = self._phase_total_points_over_under(PhaseType.HALF)

        return [t for t in (quarter, half) if t is not None]

    def _phase_total_points_over_under(self, half_or_quarter: PhaseType) -> Optional[Tip]:
        assert half_or_quarter != PhaseType.OVERTIME

        if not self.phase_changed:
            return

        if half_or_quarter is PhaseType.QUARTER and self.phase_type is PhaseType.HALF:
            return

        if half_or_quarter is PhaseType.QUARTER:
            if self.current_quarter == 1:
                return

            market_ids = {
                1: 148,
                2: 149,
                3: 150,
                4: 151
            }

            bet_ids = {
                1: (1905, 6661),
                2: (1906, 6662),
                3: (1907, 6663),
                4: (1908, 6664)
            }

            if self.phase_type is PhaseType.OVERTIME:
                m_id = market_ids[4]
                b_ids = bet_ids[4]
            else:
                m_id = market_ids[self.current_quarter - 1]
                b_ids = bet_ids[self.current_quarter - 1]
        else:
            if self.current_half == 1:
                return

            market_ids = {
                1: 152,
                2: 153
            }

            bet_ids = {
                1: (1909, 6659),
                2: (1910, 6660)
            }

            if self.phase_type is PhaseType.OVERTIME:
                m_id = market_ids[2]
                b_ids = bet_ids[2]
            else:
                m_id = market_ids[1]
                b_ids = bet_ids[1]

        tip_groups = self.get_tip_groups(m_id, b_ids[0]) or []
        tip_groups.extend(self.get_tip_groups(m_id, b_ids[1]) or [])
        if len(tip_groups) == 0:
            return

        min_goal_group = min(tip_groups, key=lambda tg: float(tg[0].tip.template_value))

        over_tip = next((t.tip for t in min_goal_group if t.tip.bet_group_name_real.startswith('Over')), None)
        under_tip = next((t.tip for t in min_goal_group if t.tip.bet_group_name_real.startswith('Under')), None)

        if over_tip is not None:
            goal = float(over_tip.template_value)
            if self.previous_phase_total_points > goal:
                return over_tip

        if under_tip is not None:
            goal = float(under_tip.template_value)
            if self.previous_phase_total_points < goal:
                return under_tip
