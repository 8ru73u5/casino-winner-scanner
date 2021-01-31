from __future__ import annotations

from datetime import datetime
from typing import Dict

from cws.api.models import Event, Tip

MarketID_t = BetID_t = TipID_t = int


class EventSnapshot:
    snapshot: Dict[MarketID_t, Dict[BetID_t, Dict[TipID_t, TipSnapshot]]]
    event: Event
    timestamp: datetime

    def __init__(self, event: Event, timestamp: datetime):
        self.snapshot = {}
        self.event = event
        self.timestamp = timestamp

        self._create_snapshot()

    def _create_snapshot(self):
        for tip in self.event.tips:
            market_group = self.snapshot.setdefault(tip.market_group_id, {})
            bet_group = market_group.setdefault(tip.bet_group_id, {})
            bet_group[tip.id] = TipSnapshot(tip)

    def update(self, old_snapshot: EventSnapshot):
        time_between_updates = (self.timestamp - old_snapshot.timestamp).seconds

        for market_id, bets in self.snapshot.items():
            for bet_id, tip_snapshots in bets.items():
                try:
                    old_tip_snapshots = old_snapshot.snapshot[market_id][bet_id]
                except KeyError:
                    continue
                else:
                    for tip_id, tip_snapshot in tip_snapshots.items():
                        try:
                            old_tip_snapshot = old_tip_snapshots[tip_id]
                        except KeyError:
                            continue
                        else:
                            tip_snapshot.update(old_tip_snapshot, time_between_updates)


class TipSnapshot:
    tip: Tip
    time_since_last_change: int

    def __init__(self, tip: Tip):
        self.tip = tip
        self.time_since_last_change = 0

    def update(self, old_snapshot: TipSnapshot, time_between_updates: int):
        if self.tip.odds != old_snapshot.tip.odds:
            self.time_since_last_change = 0
        else:
            self.time_since_last_change += time_between_updates
