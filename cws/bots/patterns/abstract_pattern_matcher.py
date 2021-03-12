from abc import abstractmethod, ABCMeta
from typing import Optional, List

from cws.api.models import Tip
from cws.core.snapshots import EventSnapshot, TipSnapshot


def check(check_method):
    def _check_method_wrapper(*args, **kwargs):
        return check_method(*args, **kwargs)

    return _check_method_wrapper


class PatternMatcherMeta(ABCMeta):
    def __new__(mcs, class_name, bases, attributes):
        checks = []

        if attributes.get('SPORT_ID') is None and class_name != 'AbstractPatternMatcher':
            raise AttributeError(f'Set SPORT_ID attribute in {class_name}')

        for value in attributes.values():
            try:
                # Gather all methods decorated with @check
                if callable(value) and value.__name__ == '_check_method_wrapper':
                    checks.append(value)
            except AttributeError:
                continue

        pattern_matcher = super(PatternMatcherMeta, mcs).__new__(mcs, class_name, bases, attributes)
        pattern_matcher._checks = checks

        return pattern_matcher


class AbstractPatternMatcher(metaclass=PatternMatcherMeta):
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
    def to_dict(self) -> dict:
        pass

    def run_checks(self) -> List[Tip]:
        check_results = []

        for check_function in self._checks:
            result = check_function(self)

            if result is not None:
                if isinstance(result, list):
                    check_results.extend(result)
                else:
                    check_results.append(result)

        return check_results

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
