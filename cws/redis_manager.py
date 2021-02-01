from typing import List, Iterable

from redis import Redis

from cws.config import AppConfig
from cws.core.notification import Notification


class RedisManager:
    NOTIFICATION_LIST_KEY = 'cw_notifications'

    def __init__(self):
        self.conn = Redis(host=AppConfig.get(AppConfig.Variables.REDIS_HOST), port=AppConfig.get(AppConfig.Variables.REDIS_PORT))

    def set_notifications(self, notifications: Iterable[Notification]):
        self.conn.delete(RedisManager.NOTIFICATION_LIST_KEY)

        notifications_json = [n.to_json() for n in notifications]

        if len(notifications_json) > 0:
            self.conn.lpush(RedisManager.NOTIFICATION_LIST_KEY, *notifications_json)
            self.conn.expire(RedisManager.NOTIFICATION_LIST_KEY, 30)

    def get_notifications_json(self) -> List[str]:
        return [n.decode('utf-8') for n in self.conn.lrange(RedisManager.NOTIFICATION_LIST_KEY, 0, -1)]
