from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import List, Optional

from cws.api.models import Tip, TeamInfo
from cws.bots.patterns.abstract_pattern_matcher import AbstractPatternMatcher


@dataclass
class Team:
    id: int
    name: str
    sets_won: int
    total_points: int = 0
    previous_total_points: int = 0
    set_points: int = 0

    def __init__(self, team_info: TeamInfo):
        self.id = team_info.id
        self.name = team_info.name
        self.sets_won = team_info.score

    def has_scored_any_points(self) -> bool:
        return self.total_points != self.previous_total_points

    def how_many_points_has_scored(self) -> int:
        return self.previous_total_points - self.total_points

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'sets_won': self.sets_won,
            'current_set_points': self.set_points,
            'total_points_current_scan': self.total_points,
            'total_points_previous_scan': self.previous_total_points
        }


class VolleyballMatcher(AbstractPatternMatcher):
    SPORT_ID = 9

    def _parse_event(self):
        self.first_team = Team(self._event.first_team)
        self.second_team = Team(self._event.second_team)
        self.current_set = self._event.raw_api_response_data['sb']['gcp']['gpi']
        assert 5 >= self.current_set >= 1

        for x in self._event.raw_api_response_data['sb']['gsl']:
            if x['gpn'].endswith('Set'):
                set_number = int(x['gpn'][0])
                score = int(x['v'])

                if self.first_team.id == x['spi']:
                    team = self.first_team
                else:
                    team = self.second_team

                team.total_points += score
                if set_number == self.current_set:
                    team.set_points = score

        for x in self._previous_event.raw_api_response_data['sb']['gsl']:
            if x['gpn'].endswith('Set'):
                score = int(x['v'])
                if self.first_team.id == x['spi']:
                    self.first_team.previous_total_points += score
                else:
                    self.second_team.previous_total_points += score

        self.game_total_points = self.first_team.total_points + self.second_team.total_points
        self.set_total_points = self.first_team.set_points + self.second_team.set_points
        self.set_points_diff = abs(self.first_team.set_points - self.second_team.set_points)

        self.set_leader = max((self.first_team, self.second_team), key=lambda t: t.set_points)
        self.min_sets_to_win = 3 - max(self.first_team.sets_won, self.second_team.sets_won)

        margin = 24 if self.current_set != 5 else 14
        self.is_margin_score = self.first_team.set_points >= margin and self.second_team.set_points >= margin

        if self.is_margin_score:
            self.min_points_to_win_set = 2 - self.set_points_diff
        else:
            if self.current_set == 5:
                self.min_points_to_win_set = 15 - self.set_leader.set_points
            else:
                self.min_points_to_win_set = 25 - self.set_leader.set_points

    def to_dict(self) -> dict:
        return {
            'home': self.first_team.to_dict(),
            'away': self.second_team.to_dict(),
            'current_set': self.current_set,
            'game_total_points': self.game_total_points,
            'set_total_points': self.set_total_points,
            'set_points_diff': self.set_points_diff,
            'sets_to_win_game': self.min_sets_to_win,
            'points_to_win_set': self.min_points_to_win_set,
            'margin_score': self.is_margin_score,
        }

    def check_for_matches(self) -> List[Tip]:
        selection_ids = [
            self._check_total_set_points(),
            self._check_total_game_points(),
            self._check_total_team_points('home'),
            self._check_total_team_points('away'),
            self._check_set_winner(),
            self._check_set_points_winner(),
            self._check_set_race_to_points()
        ]

        return [x for x in selection_ids if x is not None]

    def _check_total_set_points(self) -> Optional[Tip]:
        market_id = 199
        bet_ids = {
            1: 2250,
            2: 2254,
            3: 2258,
            4: 2262,
            5: 2266
        }

        tip_group = self.get_tip_groups(market_id, bet_ids[self.current_set])
        if tip_group is None or len(tip_group) != 1:
            return

        over_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Over')), None)
        under_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Under')), None)

        if over_tip is not None:
            over_points = float(over_tip.name.split()[1])
            remaining_points = ceil(over_points - self.set_total_points)

            if self.min_points_to_win_set >= remaining_points:
                return over_tip

        if under_tip is not None:
            under_points = float(under_tip.name.split()[1])

            if not self.is_margin_score and self.min_points_to_win_set == 0 and under_points > self.set_total_points:
                return under_tip

    def _check_total_game_points(self) -> Optional[Tip]:
        market_id = 198
        bet_id = 2248

        tip_group = self.get_tip_groups(market_id, bet_id)
        if tip_group is None or len(tip_group) != 1:
            return

        over_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Over')), None)
        under_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Under')), None)

        if over_tip is not None:
            over_points = float(over_tip.name.split()[1])
            remaining_points = ceil(over_points - self.game_total_points)

            if self.min_sets_to_win == 0 and self.game_total_points >= over_points:
                return over_tip

            min_points_to_win_match = self.min_points_to_win_set + (1 - self.min_sets_to_win) * 25

            if min_points_to_win_match >= remaining_points:
                return over_tip

        if under_tip is not None:
            under_points = float(under_tip.name.split()[1])

            if self.current_set == 5 and not self.is_margin_score and self.min_points_to_win_set == 0 and under_points > self.game_total_points:
                return under_tip

    def _check_set_winner(self) -> Optional[Tip]:
        market_id = 197
        bet_id = 2245

        tip_group = self.get_tip_groups(market_id, bet_id)
        if tip_group is None or len(tip_group) != 1:
            return

        if int(tip_group[0][0].tip.bet_group_name_real.split()[1]) != self.current_set:
            return

        if self.min_points_to_win_set == 0:
            return next((
                ts.tip for ts in tip_group[0]
                if ts.tip.associated_player_id == self.set_leader.id
            ), None)

    def _check_total_team_points(self, home_or_away: str) -> Optional[Tip]:
        assert home_or_away in ['home', 'away']

        market_id = 189
        bet_ids = {
            'home': 4833,
            'away': 4834
        }

        tip_group = self.get_tip_groups(market_id, bet_ids[home_or_away])
        if tip_group is None or len(tip_group) != 1:
            return

        over_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Over')), None)

        team = self.first_team if home_or_away == 'home' else self.second_team

        if over_tip is not None:
            over_points = float(over_tip.name.split()[1])

            if self.min_sets_to_win == 0 and team.total_points >= over_points:
                return over_tip

    def _check_set_points_winner(self) -> Optional[Tip]:
        market_id = 199
        bet_ids = {
            1: 2252,
            2: 2256,
            3: 2260,
            4: 2264,
            5: 2268
        }

        tip_group = self.get_tip_groups(market_id, bet_ids[self.current_set])
        if tip_group is None or len(tip_group) != 1:
            return

        if self.first_team.has_scored_any_points() ^ self.second_team.has_scored_any_points():
            goal = int(tip_group[0][0].tip.bet_group_name_real.split()[-2])

            if self.set_total_points == goal:
                scorer = self.first_team if self.first_team.has_scored_any_points() else self.second_team
                return next((ts.tip for ts in tip_group[0] if ts.tip.associated_player_id == scorer.id), None)

    def _check_set_race_to_points(self) -> Optional[Tip]:
        market_id = 199
        bet_ids = {
            1: 2251,
            2: 2255,
            3: 2259,
            4: 2263,
            5: 2267
        }

        tip_group = self.get_tip_groups(market_id, bet_ids[self.current_set])
        if tip_group is None:
            return None

        min_goal_group = min(tip_group, key=lambda ts: int(ts[0].tip.bet_group_name_real.split()[-2]))
        goal = int(min_goal_group[0].tip.bet_group_name_real.split()[-2])

        if self.set_leader.set_points == goal and self.first_team.set_points != self.second_team.set_points:
            return next((ts.tip for ts in min_goal_group if ts.tip.associated_player_id == self.set_leader.id), None)
