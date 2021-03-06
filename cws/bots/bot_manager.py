import asyncio
from typing import List, Dict, Tuple, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cws.bots.bet_bot import BetBot, WalletBalance
from cws.bots.bet_history_item import BetHistoryItem
from cws.models import BettingBot as dbBetBot
from cws.redis_manager import RedisManager


class BotManager:
    _bots: Dict[int, BetBot]

    def __init__(self, session: Session):
        self.session = session
        self.redis_manager = RedisManager()

        self._bots = {}
        self.load_bots(log_in_bots=True)

    @property
    def enabled_bots(self) -> List[BetBot]:
        return [b for b in self._bots.values() if b.is_enabled]

    def _get_bots_from_db(self) -> List[dbBetBot]:
        db_error = None

        bots = []
        try:
            bots = self.session.query(dbBetBot).all()
        except SQLAlchemyError as e:
            db_error = e
            self.session.rollback()
        finally:
            self.session.close()

        if db_error is not None:
            raise db_error
        else:
            return bots

    def load_bots(self, log_in_bots: bool = False):
        bots = self._get_bots_from_db()
        db_bot_ids = set()

        for b in bots:
            db_bot_ids.add(b.id)

            if b.id not in self._bots:
                self._bots[b.id] = BetBot(b.username, b.password, b.bookmaker, b.proxy_country_code, b.is_enabled)
            else:
                self._bots[b.id].is_enabled = b.is_enabled

        # Remove bots that have been deleted from the database
        for bot_id in set(self._bots.keys()).difference(db_bot_ids):
            del self._bots[bot_id]

        if log_in_bots:
            asyncio.run(self._log_in_bots())

    async def _log_in_bots(self):
        logged_off_bots = [bot for bot in self._bots.values() if not bot.has_session()]

        if len(logged_off_bots) == 0:
            return

        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(None, BetBot.login, bot, True)
            for bot in logged_off_bots
        ]

        await asyncio.gather(*futures)

    async def _get_bots_wallet_balance(self) -> Dict[int, Optional[WalletBalance]]:
        loop = asyncio.get_event_loop()

        def get_wallet_balance(bot_id: int, bot: BetBot) -> Tuple[int, Optional[WalletBalance]]:
            # noinspection PyBroadException
            try:
                return bot_id, bot.get_wallet_balance(reload=True)
            except:
                return bot_id, None

        futures = [
            loop.run_in_executor(None, get_wallet_balance, bot_id, bot)
            for bot_id, bot in self._bots.items()
        ]

        return {bot_id: wallet_balance for bot_id, wallet_balance in await asyncio.gather(*futures)}

    async def _get_bots_bet_history(self) -> Dict[int, Optional[List[BetHistoryItem]]]:
        loop = asyncio.get_event_loop()

        def get_bet_history(bot_id: int, bot: BetBot) -> Tuple[int, Optional[List[BetHistoryItem]]]:
            # noinspection PyBroadException
            try:
                return bot_id, bot.get_bet_history()
            except:
                return bot_id, None

        futures = [
            loop.run_in_executor(None, get_bet_history, bot_id, bot)
            for bot_id, bot in self._bots.items()
        ]

        return {bot_id: bet_history for bot_id, bet_history in await asyncio.gather(*futures)}

    def save_bots_info_to_redis(self):
        wallet_balances = asyncio.run(self._get_bots_wallet_balance())
        bet_histories = asyncio.run(self._get_bots_bet_history())

        self.redis_manager.set_bet_bots_wallet_balance(wallet_balances)
        self.redis_manager.set_bet_bots_bet_history(bet_histories)
