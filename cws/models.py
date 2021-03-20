from __future__ import annotations

from datetime import datetime
from enum import Enum
from json import dumps
from typing import Optional, Any

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, ForeignKeyConstraint, Enum as sql_Enum, UniqueConstraint, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship, Session

from .bots.bet_bot import BookmakerType
from .database import Base


class Sport(Base):
    __tablename__ = 'sports'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    trigger_time = Column(Integer, nullable=False, default=300)

    def to_json(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'is_enabled': self.is_enabled,
            'trigger_time': self.trigger_time
        }

    def __repr__(self):
        return f'<[{"+" if self.is_enabled else "-"}] Sport: {self.name}>'

    def __hash__(self):
        return self.id


class Market(Base):
    __tablename__ = 'markets'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    trigger_time = Column(Integer, nullable=True, default=None)

    sport_id = Column(Integer, ForeignKey('sports.id'), primary_key=True)

    sport = relationship('Sport', lazy=False)

    def to_json(self) -> dict:
        return {
            'id': self.id,
            'sport_id': self.sport_id,
            'name': self.name,
            'is_enabled': self.is_enabled,
            'trigger_time': self.trigger_time
        }

    def __repr__(self):
        return f'<[{"+" if self.is_enabled else "-"}] Market: {self.name}>'

    def __hash__(self):
        return hash((self.id, self.sport_id))


class Bet(Base):
    __tablename__ = 'bets'

    __table_args__ = (
        ForeignKeyConstraint(
            ('sport_id', 'market_id'),
            ('markets.sport_id', 'markets.id')
        ),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)

    sport_id = Column(Integer, primary_key=True)
    market_id = Column(Integer, primary_key=True)

    market = relationship('Market', lazy=False, foreign_keys=[sport_id, market_id])

    def to_json(self) -> dict:
        return {
            'id': self.id,
            'sport_id': self.sport_id,
            'market_id': self.market_id,
            'name': self.name,
            'is_enabled': self.is_enabled
        }

    def __repr__(self):
        return f'<[{"+" if self.is_enabled else "-"}] Bet: {self.name}>'

    def __hash__(self):
        return hash((self.id, self.market_id, self.sport_id))


class BettingBotCategory(Base):
    __tablename__ = 'betting_bots_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)


class BettingBot(Base):
    __tablename__ = 'betting_bots'

    __table_args__ = (
        UniqueConstraint('username', 'bookmaker'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    username = Column(String(50), nullable=False)
    password = Column(String(50), nullable=False)
    bookmaker = Column(sql_Enum(BookmakerType), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    proxy_country_code = Column(String(5), nullable=False, default='US')

    category_id = Column(Integer, ForeignKey('betting_bots_categories.id', ondelete='set null'), nullable=True, default=None)
    category = relationship('BettingBotCategory', lazy=False)


class BettingBotHistory(Base):
    __tablename__ = 'betting_bot_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(500), nullable=False)
    market_name = Column(String(100), nullable=False)
    selection_name = Column(String(100), nullable=False)
    stake = Column(Float, nullable=False)
    odds = Column(Float, nullable=False)
    submission_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    success = Column(Boolean, nullable=False)
    details = Column(JSONB, nullable=False)
    bookmaker_response = Column(JSONB, nullable=True, default=None)

    bot_id = Column(Integer, ForeignKey('betting_bots.id'), nullable=False)
    sport_id = Column(Integer, ForeignKey('sports.id'), nullable=False)

    @property
    def details_pretty(self) -> str:
        return dumps(self.details, ensure_ascii=False, indent=2)

    @property
    def bookmaker_response_pretty(self) -> Optional[str]:
        if self.bookmaker_response is not None:
            return dumps(self.bookmaker_response, ensure_ascii=False, indent=2)


class AppOption(Base):
    class OptionType(Enum):
        MIN_ODDS = {
            'id': 1,
            'default': 1.0,
            'check': lambda v: float(v) >= 1.0,
            'name': 'Minimum odds'
        }
        MAX_ODDS = {
            'id': 2,
            'default': 15.0,
            'check': lambda v: float(v) >= 1.1,
            'name': 'Maximum odds'
        }
        TELEGRAM_NOTIFICATION_MIN_UPTIME = {
            'id': 3,
            'default': 120,
            'check': lambda v: int(v) >= 5,
            'name': 'Telegram notification after × seconds'
        }
        SOUND_NOTIFICATION_MIN_UPTIME = {
            'id': 4,
            'default': 60,
            'check': lambda v: int(v) >= 5,
            'name': 'Sound notification after × seconds'
        }
        TELEGRAM_SECOND_NOTIFICATION_MIN_UPTIME = {
            'id': 5,
            'default': 600,
            'check': lambda v: int(v) >= 10,
            'name': 'Telegram second notification after × seconds'
        }
        AUTO_BREAK_MIN_IDLE_TIME = {
            'id': 6,
            'default': 180,
            'check': lambda v: int(v) >= 10,
            'name': 'Auto-break after × seconds'
        }

        @staticmethod
        def get_by_id(option_id: int) -> Optional[dict]:
            return next((o.value for o in AppOption.OptionType.__members__.values() if o.value['id'] == option_id), None)

    __tablename__ = 'options'

    id = Column(Integer, primary_key=True, autoincrement=False)
    value = Column(JSONB, nullable=False)

    # noinspection PyBroadException
    def check(self) -> bool:
        option = AppOption.OptionType.get_by_id(self.id)

        try:
            return option['check'](self.value['value'])
        except:
            return False

    def set_value(self, new_value: Any):
        self.value['value'] = new_value

    @staticmethod
    def get_option(option_type: AppOption.OptionType, session: Session) -> Optional[Any]:
        o = session.query(AppOption).get(option_type.value['id'])

        if o is not None:
            return o.value['value']
        else:
            return None

    @classmethod
    def insert_default_options(cls, session: Session):
        db_error = None

        try:
            for option in cls.OptionType.__members__.values():
                o = AppOption(id=option.value['id'], value={
                    'name': option.value['name'],
                    'value': option.value['default']
                })

                if o.check():
                    session.add(o)

            session.commit()
        except SQLAlchemyError as e:
            db_error = e
            session.rollback()
        finally:
            session.close()

        if db_error is not None:
            raise db_error
