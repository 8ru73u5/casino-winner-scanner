from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as psql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.functions import coalesce

from cws.api.casino_winner import CasinoWinnerApi as Api
from cws.api.models import Event
from cws.core.notification import Notification
from cws.core.snapshots import EventSnapshot
from cws.models import Sport, Market, Bet
from cws.redis_manager import RedisManager


class Scanner:
    session: scoped_session
    redis_manager: RedisManager
    event_snapshots: Dict[int, EventSnapshot]
    enabled_filters: Dict[int, int]
    notifications: Dict[int, Notification]

    def __init__(self, session: scoped_session):
        self.session = session
        self.redis_manager = RedisManager()

        self._load_enabled_filters()
        self.notifications = {}

        events, timestamp = Api.get_all_live_events()
        self.event_snapshots = self._make_snapshots(events, timestamp)

    def cycle(self):
        events, timestamp = Api.get_all_live_events()

        self._update_database(events)
        self._load_enabled_filters()

        new_event_snapshots = self._make_snapshots(events, timestamp)
        self._update_snapshots(new_event_snapshots)
        self._generate_notifications()

    def _make_snapshots(self, events: List[Event], timestamp: datetime) -> Dict[int, EventSnapshot]:
        return {event.id: EventSnapshot(event, timestamp, self.enabled_filters) for event in events}

    def _update_snapshots(self, new_event_snapshots: Dict[int, EventSnapshot]):
        for event_id, event_snapshot in new_event_snapshots.items():
            old_event_snapshot = self.event_snapshots.get(event_id)

            if old_event_snapshot is not None:
                event_snapshot.update(old_event_snapshot)

        self.event_snapshots = new_event_snapshots

    def _update_database(self, events: List[Event]):
        sports = set()
        markets = set()
        bets = set()

        for event in events:
            sports.add((event.sport_id, event.sport_name))

            for tip in event.tips:
                markets.add((tip.market_group_id, tip.market_group_name, True, None, event.sport_id))
                bets.add((tip.bet_group_id, tip.bet_group_name, True, event.sport_id, tip.market_group_id))

        db_error = None

        try:
            self.session.execute(
                psql_insert(Sport).values(list(sports)).on_conflict_do_nothing()
            )
            self.session.execute(
                psql_insert(Market).values(list(markets)).on_conflict_do_nothing()
            )
            self.session.execute(
                psql_insert(Bet).values(list(bets)).on_conflict_do_nothing()
            )
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            db_error = e
        finally:
            self.session.close()

        if db_error is not None:
            raise db_error

    def _load_enabled_filters(self):
        db_error = None

        try:
            enabled = self.session.query(
                Sport.id,
                Market.id,
                Bet.id,
                coalesce(Market.trigger_time, Sport.trigger_time)
            ).select_from(Sport) \
                .join(Market) \
                .join(Bet) \
                .filter(and_(
                Sport.is_enabled, Market.is_enabled, Bet.is_enabled
            )).all()

            self.enabled_filters = {
                hash((sport_id, market_id, bet_id)): trigger_time
                for sport_id, market_id, bet_id, trigger_time in enabled
            }
        except SQLAlchemyError as e:
            self.session.rollback()
            db_error = e
        finally:
            self.session.close()

        if db_error is not None:
            raise db_error

    def _generate_notifications(self):
        new_notifications = []
        updated_notifications = []

        for event_id, event_snapshot in self.event_snapshots.items():
            event_is_frozen = True
            event_new_notifications = []

            for market_id, bets in event_snapshot.snapshot.items():
                for bet_id, tip_snapshots in bets.items():
                    try:
                        ident = hash((event_snapshot.event.sport_id, market_id, bet_id))
                        trigger_time = self.enabled_filters[ident]
                    except KeyError:
                        continue

                    min_idle_time = min(snapshot.time_since_last_change for _, snapshot in tip_snapshots.items())
                    notification_hash = hash((event_id, market_id, bet_id))

                    if min_idle_time >= trigger_time:
                        if notification_hash in self.notifications:
                            updated_notifications.append((notification_hash, event_snapshot.event))
                        else:
                            event_new_notifications.append(Notification(event_snapshot.event, [ts.tip for ts in tip_snapshots.values()]))

                    if min_idle_time < 120:
                        event_is_frozen = False

            if not event_is_frozen:
                new_notifications.extend(event_new_notifications)

        notifications = {}

        # New notifications
        for n in new_notifications:
            notifications[hash(n)] = n

        # Updated notifications
        for notification_hash, event in updated_notifications:
            n = self.notifications.get(notification_hash)

            if n is not None:
                n.update(event)
                notifications[hash(n)] = n

        if len(new_notifications) == 0 and len(updated_notifications) == 0:
            print('No notifications to process')
        else:
            print(f'{len(notifications)} notifications processed: {len(new_notifications)} new and {len(updated_notifications)} updated')

        self.notifications = notifications
        self.redis_manager.set_notifications(notifications.values())