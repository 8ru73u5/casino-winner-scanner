from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_ERROR, JobExecutionEvent

from cws.redis_manager import RedisManager


class StatusMonitor:
    SUBSCRIBED_EVENTS = EVENT_JOB_EXECUTED | EVENT_JOB_MAX_INSTANCES | EVENT_JOB_ERROR

    def __init__(self):
        self.redis_manager = RedisManager()

    def scheduler_monitor(self, event: JobExecutionEvent):
        if event.code == EVENT_JOB_ERROR:
            self.redis_manager.set_app_status_error(type(event.exception).__name__, str(event.exception), event.traceback)
        elif event.code == EVENT_JOB_MAX_INSTANCES:
            self.redis_manager.set_app_status_heavy_load()
