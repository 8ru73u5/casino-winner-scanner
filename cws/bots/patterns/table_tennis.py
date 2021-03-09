from dataclasses import dataclass
from math import ceil
from typing import List, Optional

from cws.api.models import TeamInfo, Tip
from cws.bots.patterns.abstract_pattern_matcher import AbstractPatternMatcher


@dataclass
class Player:
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

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'sets_won': self.sets_won,
            'current_set_points': self.set_points,
            'total_points_current_scan': self.total_points,
            'total_points_previous_scan': self.previous_total_points
        }

    def has_scored_any_points(self) -> bool:
        return self.total_points != self.previous_total_points


class TableTennisMatcher(AbstractPatternMatcher):
    SPORT_ID = 138

    def _parse_event(self):
        self.first_player = Player(self._event.first_team)
        self.second_player = Player(self._event.second_team)
        self.current_set = self._event.raw_api_response_data['sb']['gcp']['gpi']
        assert 5 >= self.current_set >= 1

        for x in self._event.raw_api_response_data['sb']['gsl']:
            if 5 >= (set_number := x['gpi']) >= 1:
                score = int(x['v'])

                if self.first_player.id == x['spi']:
                    player = self.first_player
                else:
                    player = self.second_player

                player.total_points += score
                if set_number == self.current_set:
                    player.set_points = score

        for x in self._previous_event.raw_api_response_data['sb']['gsl']:
            if 5 >= x['gpi'] >= 1:
                score = int(x['v'])
                if self.first_player.id == x['spi']:
                    self.first_player.previous_total_points += score
                else:
                    self.second_player.previous_total_points += score

        self.game_total_points = self.first_player.total_points + self.second_player.total_points
        self.set_total_points = self.first_player.set_points + self.second_player.set_points
        self.set_points_diff = abs(self.first_player.set_points - self.second_player.set_points)

        self.set_leader = max((self.first_player, self.second_player), key=lambda p: p.set_points)
        self.min_sets_to_win = 3 - max(self.first_player.sets_won, self.second_player.sets_won)

        self.is_margin_score = self.first_player.set_points >= 10 and self.second_player.set_points >= 10

        if self.is_margin_score:
            self.min_points_to_win_set = 2 - self.set_points_diff
        else:
            self.min_points_to_win_set = 11 - self.set_leader.set_points

    def to_dict(self) -> dict:
        return {
            'player_one': self.first_player.to_dict(),
            'player_two': self.second_player.to_dict(),
            'current_set': self.current_set,
            'game_total_points': self.game_total_points,
            'set_total_points': self.set_total_points,
            'set_points_diff': self.set_points_diff,
            'points_to_win_set': self.min_points_to_win_set,
            'margin_score': self.is_margin_score
        }

    def check_for_matches(self) -> List[Tip]:
        selection_ids = [
            self._check_total_set_points(),
            self._check_total_game_points(),
            self._check_set_winner(),
            self._check_total_team_points('home'),
            self._check_total_team_points('away'),
            self._check_set_points_winner()
        ]

        return [x for x in selection_ids if x is not None]

    def _check_total_set_points(self) -> Optional[Tip]:
        market_id = 4
        bet_id = 8555

        tip_groups = self.get_tip_groups(market_id, bet_id)
        if tip_groups is None:
            return

        min_tip_group = min(tip_groups, key=lambda tg: int(tg[0].tip.bet_group_name_real.split()[1]))

        over_tip = next((ts.tip for ts in min_tip_group if ts.tip.name.startswith('Over')), None)
        under_tip = next((ts.tip for ts in min_tip_group if ts.tip.name.startswith('Under')), None)

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
        market_id = 216
        bet_id = 8438

        tip_group = self.get_tip_groups(market_id, bet_id)
        if tip_group is None or len(tip_group) != 1:
            return

        over_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Over')), None)

        if over_tip is not None:
            over_points = float(over_tip.name.split()[1])
            remaining_points = ceil(over_points - self.game_total_points)

            if self.min_sets_to_win == 0 and self.game_total_points >= over_points:
                return over_tip

            min_points_to_win_match = self.min_points_to_win_set + (1 - self.min_points_to_win_set) * 11

            if min_points_to_win_match >= remaining_points:
                return over_tip

    def _check_set_winner(self) -> Optional[Tip]:
        market_id = 218
        bet_id = 8435

        tip_groups = self.get_tip_groups(market_id, bet_id)
        if tip_groups is None:
            return

        min_tip_group = min(tip_groups, key=lambda tg: int(tg[0].tip.bet_group_name_real.split()[1]))

        if self.min_points_to_win_set == 0:
            return next((
                ts.tip for ts in min_tip_group
                if ts.tip.associated_player_id == self.set_leader.id
            ), None)

    def _check_total_team_points(self, home_or_away: str) -> Optional[Tip]:
        assert home_or_away in ['home', 'away']

        market_id = 4
        bet_ids = {
            'home': 8558,
            'away': 8559
        }

        tip_group = self.get_tip_groups(market_id, bet_ids[home_or_away])
        if tip_group is None or len(tip_group) != 1:
            return

        over_tip = next((ts.tip for ts in tip_group[0] if ts.tip.name.startswith('Over')), None)
        team = self.first_player if home_or_away == 'home' else self.second_player

        if over_tip is not None:
            over_points = float(over_tip.name.split()[1])

            if self.min_sets_to_win == 0 and team.total_points >= over_points:
                return over_tip

    def _check_set_points_winner(self) -> Optional[Tip]:
        market_id = 4
        bet_id = 8556

        tip_groups = self.get_tip_groups(market_id, bet_id)
        if tip_groups is None:
            return

        current_set_tip_groups = [
            tg for tg in tip_groups
            if int(tg[0].tip.bet_group_name_real.split()[1]) == self.current_set
        ]

        if len(current_set_tip_groups) == 0:
            return

        min_goal_tip_group = min(current_set_tip_groups, key=lambda tg: int(tg[0].tip.bet_group_name_real.split()[-2]))

        if self.first_player.has_scored_any_points() ^ self.second_player.has_scored_any_points():
            goal = int(min_goal_tip_group[0].tip.bet_group_name_real.split()[-2])

            if self.set_total_points == goal:
                scorer = self.first_player if self.first_player.has_scored_any_points() else self.second_player
                return next((ts.tip for ts in min_goal_tip_group if ts.tip.associated_player_id == scorer.id), None)
