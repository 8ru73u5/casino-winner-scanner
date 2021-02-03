from typing import List

from telegram import Bot, ParseMode
from telegram.ext import messagequeue as mq

from cws.config import AppConfig
from cws.core.notification import Notification


class TelegramNotifier(Bot):
    MAX_MSG_LENGTH = 4050
    MSG_GROUP_DELIMITER = '\n\n'

    def __init__(self):
        super(TelegramNotifier, self).__init__(AppConfig.get(AppConfig.Variables.TELEGRAM_TOKEN))
        self._is_messages_queued_default = True
        self._msg_queue = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3500)
        self.chat_id = AppConfig.get(AppConfig.Variables.TELEGRAM_CHAT_ID)

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
