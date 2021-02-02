from __future__ import annotations

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship

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
            'name': self.name,
            'is_enabled': self.is_enabled
        }

    def __repr__(self):
        return f'<[{"+" if self.is_enabled else "-"}] Bet: {self.name}>'

    def __hash__(self):
        return hash((self.id, self.market_id, self.sport_id))
