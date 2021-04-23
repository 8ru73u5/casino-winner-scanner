from datetime import datetime
from typing import Tuple, List

from requests import get

from .models import Event


class CasinoWinnerApi:
    EVENTS_URL = 'https://krn-api-a.bpsgameserver.com/isa/v2/1101/en/event'
    DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
    TIMEOUT = 1

    @classmethod
    def get_all_live_events(cls) -> Tuple[List[Event], datetime]:
        r = get(cls.EVENTS_URL, params={
            'eventCount': 999,
            'eventPhase': 2,
            'include': 'scoreboard,scoresummary',
            'override': 'Mst1X2ParticipantName'
        }, timeout=cls.TIMEOUT)

        r.raise_for_status()

        return Event.from_json_multiple(r.json()), datetime.strptime(r.headers['Date'], cls.DATE_FORMAT)
