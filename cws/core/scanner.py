from __future__ import annotations

from datetime import datetime
from itertools import cycle
from typing import Dict, List

from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as psql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import coalesce

from cws.api.casino_winner import CasinoWinnerApi as Api
from cws.api.models import Event
from cws.bots.bot_manager import BotManager
from cws.core.notification import Notification
from cws.core.notifier import TelegramNotifier
from cws.core.snapshots import EventSnapshot
from cws.database import SessionLocal
from cws.models import Sport, Market, Bet, AppOption
from cws.redis_manager import RedisManager


class Scanner:
    session: Session
    redis_manager: RedisManager
    event_snapshots: Dict[int, EventSnapshot]
    enabled_filters: Dict[int, int]
    notifications: Dict[int, Notification]
    min_odds: float
    max_odds: float
    auto_break_min_idle_time: int
    telegram_notification_min_uptime: int
    telegram_second_notification_min_uptime: int
    telegram_notifier: TelegramNotifier

    def __init__(self, session: Session):
        self.session = session
        self.redis_manager = RedisManager()
        self.telegram_notifier = TelegramNotifier()
        self.bot_manager = BotManager(SessionLocal())
        self._bot_manager_update_cycle = cycle(range(10))

        self._load_enabled_filters()
        self._load_odds_options()
        self.notifications = {}

        events, timestamp = Api.get_all_live_events()
        self.event_snapshots = self._make_snapshots(events, timestamp)

    def cycle(self):
        events, timestamp = Api.get_all_live_events()

        self._update_database(events)
        self._load_enabled_filters()
        self._load_odds_options()

        if next(self._bot_manager_update_cycle) == 0:
            self.bot_manager.load_bots(log_in_bots=True)
            self.bot_manager.save_bots_info_to_redis()

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
        db_change = False

        try:
            if len(sports) > 0:
                db_change = True
                self.session.execute(
                    psql_insert(Sport).values(list(sports)).on_conflict_do_nothing()
                )

            if len(markets) > 0:
                db_change = True
                self.session.execute(
                    psql_insert(Market).values(list(markets)).on_conflict_do_nothing()
                )

            if len(bets) > 0:
                db_change = True
                self.session.execute(
                    psql_insert(Bet).values(list(bets)).on_conflict_do_nothing()
                )

            if db_change:
                self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            db_error = e
        finally:
            if db_change:
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

    def _load_odds_options(self):
        db_error = None

        try:
            self.min_odds = AppOption.get_option(AppOption.OptionType.MIN_ODDS, self.session)
            self.max_odds = AppOption.get_option(AppOption.OptionType.MAX_ODDS, self.session)
            self.auto_break_min_idle_time = AppOption.get_option(AppOption.OptionType.AUTO_BREAK_MIN_IDLE_TIME, self.session)
            self.telegram_notification_min_uptime = AppOption.get_option(AppOption.OptionType.TELEGRAM_NOTIFICATION_MIN_UPTIME, self.session)
            self.telegram_second_notification_min_uptime = AppOption.get_option(
                AppOption.OptionType.TELEGRAM_SECOND_NOTIFICATION_MIN_UPTIME, self.session
            )
        except SQLAlchemyError as e:
            db_error = e
            self.session.rollback()
        finally:
            self.session.close()

        if db_error is not None:
            raise db_error

    def _generate_notifications(self):
        new_notifications = []
        updated_notifications = []

        for event_id, event_snapshot in self.event_snapshots.items():
            if event_snapshot.event.is_break:
                continue

            event_updated_notifications = []
            event_new_notifications = []
            event_auto_break_detected = True

            for market_id, bets in event_snapshot.snapshot.items():
                for tip_group_id, tip_snapshots in bets.items():
                    tips = [ts.tip for ts in tip_snapshots.values()]

                    try:
                        filter_ident = hash((event_snapshot.event.sport_id, market_id, tips[0].bet_group_id))
                        trigger_time = self.enabled_filters[filter_ident]
                    except KeyError:
                        continue

                    min_idle_time = min(ts.time_since_last_change for ts in tip_snapshots.values())
                    notification_hash = hash((event_id, tip_group_id))

                    is_market_active = tips[0].is_active

                    min_market_odds = min(t.odds for t in tips)
                    max_market_odds = max(t.odds for t in tips)

                    if is_market_active and min_idle_time >= trigger_time \
                            and min_market_odds >= self.min_odds and max_market_odds <= self.max_odds:
                        if notification_hash in self.notifications:
                            event_updated_notifications.append((notification_hash, event_snapshot.event))
                        else:
                            event_new_notifications.append(Notification(event_snapshot.event, tips))

                    if min_idle_time < self.auto_break_min_idle_time:
                        event_auto_break_detected = False

            if len(event_snapshot.event.tips) <= 5:
                event_auto_break_detected = False

            if not event_auto_break_detected:
                new_notifications.extend(event_new_notifications)
                updated_notifications.extend(event_updated_notifications)

        notifications = {}

        # New notifications
        for n in new_notifications:
            if n.event.is_tip_eligible_for_notification(n.tip_group[0]):
                notifications[hash(n)] = n

        # Updated notifications
        for notification_hash, event in updated_notifications:
            n = self.notifications.get(notification_hash)

            if n is not None and n.event.is_tip_eligible_for_notification(n.tip_group[0]):
                n.update(event)
                notifications[hash(n)] = n

        if len(new_notifications) == 0 and len(updated_notifications) == 0:
            print('No notifications to process')
        else:
            print(f'{len(notifications)} notifications processed: {len(new_notifications)} new and {len(updated_notifications)} updated')

        self.notifications = notifications
        self.redis_manager.set_notifications(notifications.values())
        self.redis_manager.set_app_status(len(self.event_snapshots), len(self.notifications))

        self._send_telegram_notification()

    def _send_telegram_notification(self):
        to_send = []

        for n in self.notifications.values():
            if not n.first_notification_sent and n.uptime_seconds >= self.telegram_notification_min_uptime:
                n.first_notification_sent = True
                to_send.append(n)
            elif not n.second_notification_sent and n.uptime_seconds >= self.telegram_second_notification_min_uptime:
                n.second_notification_sent = True
                to_send.append(n)

        self.telegram_notifier.send_notifications(to_send)
