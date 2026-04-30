import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vouch.settings")

app = Celery("vouch")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Heartbeat interval (seconds)
app.conf.worker_send_task_events = True  # Enable task events
app.conf.task_send_sent_event = True  # Enable task sent events
app.conf.worker_heartbeat_interval = 2  # Send heartbeat every 2 seconds (default)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


app.conf.beat_schedule = {
    "run-every-minute": {
        "task": "common.tasks.add",
        "schedule": crontab(),
        "args": (16, 16),
    },
}
