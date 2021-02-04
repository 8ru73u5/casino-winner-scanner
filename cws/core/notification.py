import json
from datetime import datetime
from typing import List

from cws.api.models import Event, Tip


class Notification:
    event: Event
    tip_group: List[Tip]
    triggered_on: datetime
    notification_sent: bool

    def __init__(self, event: Event, tip_group: List[Tip]):
        self.event = event
        self.tip_group = tip_group
        self.triggered_on = datetime.now()
        self.notification_sent = False

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
            'tips': [{'name': tip.name, 'odds': tip.odds} for tip in self.tip_group],
            'uptime': self.uptime_formatted,
            'uptime_seconds': self.uptime_seconds
        }

        return json.dumps(n, ensure_ascii=False)

    def construct_telegram_message(self) -> str:
        link = f'{self.event.get_sport_name_or_emoji()} <b>{self.event.first_team.name} vs {self.event.second_team.name}</b>'
        phase = f'Time: {self.event.get_time_or_phase()}'
        score = f'Score: {self.event.get_score()}'
        if self.event.has_score_info():
            score += f' ({self.event.first_team.score + self.event.second_team.score})'
        bet = f'Bet: {self.tip_group[0].bet_group_name_real}'
        tips = 'Tips:\n' + '\n'.join([f'-> {tip.name} ({tip.odds:.02f})' for tip in self.tip_group])

        return '\n'.join([link, phase, score, bet, tips])

    def __hash__(self):
        return hash((self.event.id, self.tip_group[0].unique_tip_group_id))
