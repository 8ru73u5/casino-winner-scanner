from __future__ import annotations

from datetime import datetime
from typing import Dict

from cws.api.models import Event, Tip

MarketID_t = BetID_t = TipGroupID_t = int


class EventSnapshot:
    snapshot: Dict[MarketID_t, Dict[BetID_t, Dict[TipGroupID_t, TipSnapshot]]]
    event: Event
    timestamp: datetime
    seconds_since_active_tip_count_change: int
    active_tip_count: int

    def __init__(self, event: Event, timestamp: datetime, enabled_filters: Dict[int, int]):
        self.snapshot = {}
        self.event = event
        self.timestamp = timestamp

        self.active_tip_count = 0
        self.seconds_since_active_tip_count_change = 0

        self._create_snapshot(enabled_filters)

    def _create_snapshot(self, enabled_filters: Dict[int, int]):
        for tip in self.event.tips:
            ident = hash((self.event.sport_id, tip.market_group_id, tip.bet_group_id))

            if ident not in enabled_filters:
                continue

            self.active_tip_count += 1

            market_group = self.snapshot.setdefault(tip.market_group_id, {})
            tip_group = market_group.setdefault(tip.unique_tip_group_id, {})
            tip_group[tip.id] = TipSnapshot(tip)

    def update(self, old_snapshot: EventSnapshot):
        time_between_updates = int((self.timestamp - old_snapshot.timestamp).total_seconds())

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

        if self.active_tip_count == old_snapshot.active_tip_count:
            self.seconds_since_active_tip_count_change = old_snapshot.seconds_since_active_tip_count_change + time_between_updates
        else:
            self.seconds_since_active_tip_count_change = 0

    def check_if_has_only_three_active_unchanged_tips(self) -> bool:
        trigger_time = 60

        if self.active_tip_count > 3 or self.seconds_since_active_tip_count_change < trigger_time:
            return False

        for bets in self.snapshot.values():
            for tip_snapshots in bets.values():
                for tip_snapshot in tip_snapshots.values():
                    if tip_snapshot.tip.is_active and tip_snapshot.time_since_last_change < trigger_time:
                        return False

        return True


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
            self.time_since_last_change = old_snapshot.time_since_last_change + time_between_updates
