from json import dumps
from typing import List, Optional

from telegram import Bot, ParseMode
from telegram.ext import messagequeue as mq

from cws.api.models import Tip, Event
from cws.bots.bet_bot import BetBot
from cws.config import AppConfig
from cws.core.notification import Notification, LowActiveTipsNotification


class TelegramNotifier(Bot):
    MAX_MSG_LENGTH = 4050
    MSG_GROUP_DELIMITER = '\n\n'

    def __init__(self):
        super(TelegramNotifier, self).__init__(AppConfig.get(AppConfig.Variables.TELEGRAM_TOKEN))
        self._is_messages_queued_default = True
        self._msg_queue = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3500)
        self.chat_id = AppConfig.get(AppConfig.Variables.TELEGRAM_CHAT_ID)
        self.bet_bot_chat_id = AppConfig.get(AppConfig.Variables.TELEGRAM_BET_BOT_CHAT_ID)

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        return super(TelegramNotifier, self).send_message(*args, **kwargs)

    @classmethod
    def arrange_messages(cls, messages: List[str]) -> List[str]:
        arranged = []
        current_group = ''
        for m in messages:
            if len(current_group) + len(m) > cls.MAX_MSG_LENGTH:
                arranged.append(current_group.strip())
                current_group = m + cls.MSG_GROUP_DELIMITER
            else:
                current_group += m + cls.MSG_GROUP_DELIMITER

        if len(current_group) != 0:
            arranged.append(current_group.strip())

        return arranged

    def send_notifications(self, notifications: List[Notification]):
        messages = [n.construct_telegram_message() for n in notifications]

        for msg in TelegramNotifier.arrange_messages(messages):
            self.send_message(self.chat_id, msg, ParseMode.HTML)

    def send_low_active_tips_notifications(self, notifications: List[LowActiveTipsNotification]):
        messages = [n.construct_telegram_message() for n in notifications]

        for msg in TelegramNotifier.arrange_messages(messages):
            self.send_message(self.chat_id, msg, ParseMode.HTML)

    def send_placing_bet_confirmation(self, bot: BetBot, event: Event, tip: Tip, status: Optional[List[dict]]):
        bot_header = f'{bot.name or "<no name>"} [<i>{bot.bookmaker.name}</i>]'
        header = f'{event.get_sport_name_or_emoji()} <b>{event.first_team.name} vs {event.second_team.name}</b>'
        phase = f'Time: {event.get_time_or_phase()}'
        score = f'Score: {event.get_score()}'
        if event.has_score_info():
            score += f' ({event.first_team.score + event.second_team.score})'
        bet = f'Bet: {tip.bet_group_name_real}'
        tip_info = f'Tip: {tip.name} ({tip.odds:.2f})'

        status_info = 'Status: '
        if status is None:
            status_info += '✅'
        else:
            status_info += '❌\nDetails:\n<pre>' + dumps(status, ensure_ascii=False, indent=1) + '</pre>'

        msg = '\n'.join([bot_header, header, phase, score, bet, tip_info, status_info])

        self.send_message(self.bet_bot_chat_id, msg, ParseMode.HTML)
