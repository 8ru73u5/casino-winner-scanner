from typing import List, Iterable, Optional, Dict, Union

from redis import Redis

from cws.config import AppConfig
from cws.core.notification import Notification


class RedisManager:
    NOTIFICATION_LIST_KEY = 'cw_notifications'
    APP_STATUS_EVENTS_KEY = 'cw_app_status_event_count'
    APP_STATUS_NOTIFICATIONS_KEY = 'cw_app_status_notification_count'
    APP_STATUS_HEAVY_LOAD_KEY = 'cw_app_status_heavy_load'
    APP_STATUS_ERROR_CLASS_KEY = 'cw_app_status_error_class'
    APP_STATUS_ERROR_DESC_KEY = 'cw_app_status_error_desc'
    APP_STATUS_ERROR_TRACEBACK_KEY = 'cw_app_status_error_traceback'

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

    def set_app_status(self, event_count: int, notification_count: int):
        self.conn.setex(RedisManager.APP_STATUS_EVENTS_KEY, 10, event_count)
        self.conn.setex(RedisManager.APP_STATUS_NOTIFICATIONS_KEY, 10, notification_count)

    def get_app_status(self) -> Union[Dict[str, int], Dict[str, str]]:
        event_count = self.conn.get(RedisManager.APP_STATUS_EVENTS_KEY)
        notification_count = self.conn.get(RedisManager.APP_STATUS_NOTIFICATIONS_KEY)

        if event_count is not None and notification_count is not None:
            event_count = int(event_count)
            notification_count = int(notification_count)
        else:
            event_count = '―'
            notification_count = '―'

        return {
            'events': event_count,
            'notifications': notification_count
        }

    def set_app_status_error(self, error_class: str, error_desc: str, traceback: str):
        self.conn.setex(RedisManager.APP_STATUS_ERROR_CLASS_KEY, 15, error_class)
        self.conn.setex(RedisManager.APP_STATUS_ERROR_DESC_KEY, 15, error_desc)
        self.conn.setex(RedisManager.APP_STATUS_ERROR_TRACEBACK_KEY, 15, traceback)

    def get_app_status_error(self) -> Optional[Dict[str, str]]:
        error_class = self.conn.get(RedisManager.APP_STATUS_ERROR_CLASS_KEY)
        error_desc = self.conn.get(RedisManager.APP_STATUS_ERROR_DESC_KEY)
        traceback = self.conn.get(RedisManager.APP_STATUS_ERROR_TRACEBACK_KEY)

        if error_class is not None and error_desc is not None and traceback is not None:
            return {
                'error_class': error_class.decode('utf-8'),
                'error_desc': error_desc.decode('utf-8'),
                'traceback': traceback.decode('utf-8')
            }
        else:
            return None

    def set_app_status_heavy_load(self):
        self.conn.setex(RedisManager.APP_STATUS_HEAVY_LOAD_KEY, 10, '1')

    def get_app_status_heavy_load(self) -> bool:
        return self.conn.get(RedisManager.APP_STATUS_HEAVY_LOAD_KEY) is not None
