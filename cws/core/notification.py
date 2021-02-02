import json
from datetime import datetime
from typing import List

from cws.api.models import Event, Tip


class Notification:
    event: Event
    tip_group: List[Tip]
    triggered_on: datetime

    def __init__(self, event: Event, tip_group: List[Tip]):
        self.event = event
        self.tip_group = tip_group
        self.triggered_on = datetime.now()

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

    def __hash__(self):
        return hash((self.event.id, self.tip_group[0].market_group_id, self.tip_group[0].bet_group_id))
