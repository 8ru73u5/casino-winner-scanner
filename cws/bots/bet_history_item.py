from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from json import dumps
from typing import Optional, List


class BetHistoryItemState(Enum):
    OPEN = 'open'
    WON = 'won'
    LOST = 'lost'


@dataclass
class BetHistoryItem:
    id: int
    event_name: str
    category_name: str
    market_name: str
    selection_name: str
    submission_date: datetime
    state: BetHistoryItemState
    odds: float
    stake: float
    payout: Optional[float]

    DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

    @property
    def profit(self) -> Optional[float]:
        if self.state is BetHistoryItemState.WON:
            return self.payout - self.stake
        elif self.state is BetHistoryItemState.LOST:
            return -self.stake
        else:
            return None

    @staticmethod
    def from_json(data: dict) -> BetHistoryItem:
        if 'won' in data['betsStatus']:
            state = BetHistoryItemState.WON
        elif 'lost' in data['betsStatus']:
            state = BetHistoryItemState.LOST
        else:
            state = BetHistoryItemState.OPEN

        bet_data = data['systemBet']['selections'][0]

        return BetHistoryItem(
            id=data['id'],
            event_name=data['eventNames'][0],
            category_name=bet_data['categoryName'],
            market_name=bet_data['marketName'],
            selection_name=bet_data['selectionName'],
            submission_date=datetime.strptime(data['submissionDate'], BetHistoryItem.DATE_FORMAT),
            state=state,
            odds=data['totalOdds'],
            stake=data['stake'],
            payout=data['totalPayout'] if state is BetHistoryItemState.WON else None
        )

    def to_json_str(self) -> str:
        return dumps({
            'event_name': self.event_name,
            'category_name': self.category_name,
            'market_name': self.market_name,
            'selection_name': self.selection_name,
            'submission_date': self.submission_date.strftime('%Y-%m-%d %H:%M:%S'),
            'state': self.state.value,
            'odds': self.odds,
            'stake': self.stake,
            'payout': self.payout,
            'profit': self.profit
        })

    @staticmethod
    def to_json_str_multiple(items: List[BetHistoryItem]) -> str:
        return '[%s]' % ','.join([item.to_json_str() for item in items])
