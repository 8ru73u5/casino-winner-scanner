from abc import ABC, abstractmethod
from typing import Optional, List

from cws.api.models import Tip
from cws.core.snapshots import EventSnapshot, TipSnapshot


class AbstractPatternMatcher(ABC):
    SPORT_ID = None

    def __init__(self, event_snapshot: EventSnapshot, previous_snapshot: EventSnapshot):
        self._snapshot = event_snapshot.snapshot
        self._event = event_snapshot.event
        self._previous_snapshot = previous_snapshot.snapshot
        self._previous_event = previous_snapshot.event
        self._parse_event()

    @abstractmethod
    def _parse_event(self):
        pass

    @abstractmethod
    def check_for_matches(self) -> List[Tip]:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    def get_tip_groups(self, market_id: int, bet_id: int) -> Optional[List[List[TipSnapshot]]]:
        try:
            bet_group = self._snapshot[market_id]
        except KeyError:
            return None

        result = []
        for tip_group in bet_group.values():
            snapshots = list(tip_group.values())
            if bet_id == snapshots[0].tip.bet_group_id:
                result.append(snapshots)

        if len(result) > 0:
            return result
        else:
            return None
