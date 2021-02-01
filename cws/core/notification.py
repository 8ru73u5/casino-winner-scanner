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

    @property
    def score(self) -> str:
        first_team_score = self.event.first_team.score
        second_team_score = self.event.second_team.score

        if first_team_score is None or second_team_score is None:
            return '<no score info>'
        else:
            return f'{first_team_score}:{second_team_score}'

    def to_json(self) -> str:
        n = {
            'id': hash(self),
            'link': self.event.link,
            'event_id': self.event.id,
            'sport_id': self.event.sport_id,
            'sport_name': self.event.sport_name,
            'first_team': self.event.first_team.name,
            'second_team': self.event.second_team.name,
            'score': self.score,
            'time': self.event.time_pretty,
            'market_name': self.tip_group[0].market_group_name,
            'bet_name': self.tip_group[0].bet_group_name,
            'tips': [{'name': tip.name, 'odds': tip.odds} for tip in self.tip_group],
            'uptime': self.uptime_formatted,
            'uptime_seconds': self.uptime_seconds
        }

        return json.dumps(n, ensure_ascii=False)

    def __hash__(self):
        return hash((self.event.id, self.tip_group[0].market_group_id, self.tip_group[0].bet_group_id))
