import json
from datetime import datetime
from typing import List, FrozenSet

from cws.api.models import Event, Tip


class Notification:
    event: Event
    tip_group: List[Tip]
    triggered_on: datetime
    first_notification_sent: bool
    second_notification_sent: bool
    has_five_minute_action_tips: bool

    def __init__(self, event: Event, tip_group: List[Tip]):
        self.event = event
        self.tip_group = tip_group
        self.triggered_on = datetime.now()
        self.first_notification_sent = False
        self.second_notification_sent = False
        self.has_five_minute_action_tips = self.event.check_if_tip_is_five_minute_action(self.tip_group[0])

    def update(self, updated_event: Event):
        self.event = updated_event

    @property
    def uptime_seconds(self) -> int:
        return int((datetime.now() - self.triggered_on).total_seconds())

    @property
    def uptime_formatted(self) -> str:
        uptime = datetime.now() - self.triggered_on
        minutes = int(uptime.total_seconds() // 60)
        seconds = int(uptime.total_seconds() % 60)

        return f'{minutes:02}:{seconds:02}'

    def to_json(self) -> str:
        n = {
            'id': hash(self),
            'link': self.event.link,
            'sport_name': self.event.get_sport_name_or_emoji(),
            'first_team': self.event.first_team.name,
            'second_team': self.event.second_team.name,
            'score': self.event.get_score(),
            'time': self.event.get_time_or_phase(),
            'bet_name': self.tip_group[0].bet_group_name_real,
            'tips': [{'name': tip.name, 'odds': tip.odds, 'selection_id': tip.selection_id} for tip in self.tip_group],
            'uptime': self.uptime_formatted,
            'uptime_seconds': self.uptime_seconds
        }

        return json.dumps(n, ensure_ascii=False)

    def construct_telegram_message(self) -> str:
        header = f'{self.event.get_sport_name_or_emoji()} <b>{self.event.first_team.name} vs {self.event.second_team.name}</b>'
        phase = f'Time: {self.event.get_time_or_phase()}'
        score = f'Score: {self.event.get_score()}'
        if self.event.has_score_info():
            score += f' ({self.event.first_team.score + self.event.second_team.score})'
        bet = f'Bet: {self.tip_group[0].bet_group_name_real}'
        tips = 'Tips:\n' + '\n'.join([f'-> {tip.name} ({tip.odds:.02f})' for tip in self.tip_group])

        if self.second_notification_sent:
            header = '‼‼‼\n' + header

        if self.has_five_minute_action_tips:
            header = '🔔' + header

        return '\n'.join([header, phase, score, bet, tips])

    def __hash__(self):
        return hash((self.event.id, self.tip_group[0].unique_tip_group_id))


class LowActiveTipsNotification:
    event: Event
    bet_names: FrozenSet[str]
    sent: bool

    def __init__(self, event: Event, tip_groups: List[List[Tip]]):
        self.event = event
        self.bet_names = frozenset(t[0].bet_group_name_real for t in tip_groups)
        self.sent = False

    def construct_telegram_message(self) -> str:
        header = f'🧨🧨🧨\n{self.event.get_sport_name_or_emoji()} <b>{self.event.first_team.name} vs {self.event.second_team.name}</b>'
        phase = f'Time: {self.event.get_time_or_phase()}'
        score = f'Score: {self.event.get_score()}'
        if self.event.has_score_info():
            score += f' ({self.event.first_team.score + self.event.second_team.score})'

        bets = 'Bets:\n' + '\n'.join([f'-> {bet_name}' for bet_name in self.bet_names])

        return '\n'.join([header, phase, score, bets])

    def __hash__(self):
        return hash((self.event.id, self.bet_names))
