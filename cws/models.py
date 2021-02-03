from __future__ import annotations

from enum import Enum
from typing import Optional, Any

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship, Session

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
