from typing import Optional, Iterable

from .abstract_pattern_matcher import AbstractPatternMatcher
from .basketball import BasketballMatcher
from .table_tennis import TableTennisMatcher
from .volleyball import VolleyballMatcher
from ...core.snapshots import EventSnapshot

_matcher_list = [VolleyballMatcher, TableTennisMatcher, BasketballMatcher]
_matcher_sports = {matcher.SPORT_ID: matcher for matcher in _matcher_list}


def get_matcher(sport_id: int, new_snapshot: EventSnapshot, old_snapshot: EventSnapshot) -> Optional[AbstractPatternMatcher]:
    try:
        return _matcher_sports[sport_id](new_snapshot, old_snapshot)
    except KeyError:
        return None


def get_supported_sports() -> Iterable[int]:
    return _matcher_sports.keys()
