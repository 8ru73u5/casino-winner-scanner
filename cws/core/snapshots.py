from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from cws.api.models import Event, Tip

MarketID_t = BetID_t = TipGroupID_t = int


class EventSnapshot:
    snapshot: Dict[MarketID_t, Dict[BetID_t, Dict[TipGroupID_t, TipSnapshot]]]
    event: Event
    timestamp: datetime
    seconds_since_active_tip_group_count_change: int
    active_tip_groups: Dict[TipGroupID_t, List[Tip]]

    def __init__(self, event: Event, timestamp: datetime, enabled_filters: Dict[int, int]):
        self.snapshot = {}
        self.event = event
        self.timestamp = timestamp

        self._create_snapshot(enabled_filters)

        self.active_tip_groups = self._get_active_tip_groups()
        self.seconds_since_active_tip_group_count_change = 0

    def _create_snapshot(self, enabled_filters: Dict[int, int]):
        for tip in self.event.tips:
            ident = hash((self.event.sport_id, tip.market_group_id, tip.bet_group_id))

            if ident not in enabled_filters:
                continue

            market_group = self.snapshot.setdefault(tip.market_group_id, {})
            tip_group = market_group.setdefault(tip.unique_tip_group_id, {})
            tip_group[tip.id] = TipSnapshot(tip)

    def _get_active_tip_groups(self) -> Dict[TipGroupID_t, List[Tip]]:
        bet_tips = {}
        for tip in self.event.tips:
            tips = bet_tips.setdefault(tip.unique_tip_group_id, [])
            tips.append(tip)

        active_tip_group_ids = []
        for tip_group_id, tips in bet_tips.items():
            if all(t.is_active for t in tips):
                active_tip_group_ids.append(tip_group_id)

        return {
            tip_group_id: tips
            for tip_group_id, tips in bet_tips.items()
            if tip_group_id in active_tip_group_ids
        }

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

        if len(self.active_tip_groups) == len(old_snapshot.active_tip_groups):
            self.seconds_since_active_tip_group_count_change = old_snapshot.seconds_since_active_tip_group_count_change + time_between_updates
        else:
            self.seconds_since_active_tip_group_count_change = 0

    def get_unchanged_active_tip_groups(self) -> Optional[List[List[Tip]]]:
        trigger_time = 60

        active_tip_groups_count = len(self.active_tip_groups)
        if active_tip_groups_count == 0 or active_tip_groups_count > 3 or self.seconds_since_active_tip_group_count_change < 30:
            return None

        unchanged_tip_groups = []

        for bets in self.snapshot.values():
            for tip_group_id, tip_snapshots in bets.items():
                if tip_group_id not in self.active_tip_groups:
                    continue

                tip = next(t.tip for t in tip_snapshots.values())

                if min(t.time_since_last_change for t in tip_snapshots.values()) >= trigger_time \
                        and self.event.is_tip_eligible_for_notification(tip):
                    unchanged_tip_groups.append(self.active_tip_groups[tip_group_id])

        if len(unchanged_tip_groups) != 0:
            return unchanged_tip_groups
        else:
            return None


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
