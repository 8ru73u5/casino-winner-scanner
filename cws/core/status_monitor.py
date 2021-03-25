from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_ERROR, JobExecutionEvent

from cws.redis_manager import RedisManager


class StatusMonitor:
    SUBSCRIBED_EVENTS = EVENT_JOB_EXECUTED | EVENT_JOB_MAX_INSTANCES | EVENT_JOB_ERROR

    def __init__(self):
        self.redis_manager = RedisManager()
        self.heavy_load_hits = 0

    def scheduler_monitor(self, event: JobExecutionEvent):
        if event.code == EVENT_JOB_ERROR:
            self.redis_manager.set_app_status_error(type(event.exception).__name__, str(event.exception), event.traceback)

        if event.code == EVENT_JOB_MAX_INSTANCES:
            self.heavy_load_hits += 1
            if self.heavy_load_hits > 2:
                self.redis_manager.set_app_status_heavy_load()
        elif self.heavy_load_hits != 0:
            self.heavy_load_hits -= 1
