import os
import signal
import threading
import time
from typing import Any

from uvicorn_worker import UvicornWorker


class BasicWorker(UvicornWorker):
    CONFIG_KWARGS = {"lifespan": "off"}


class ReloaderThread(threading.Thread):
    def __init__(self, worker: UvicornWorker, sleep_interval: float = 0.25):
        super().__init__()
        self.setDaemon(True)
        self._worker = worker
        self._interval = sleep_interval

    def run(self) -> None:
        while True:
            if not self._worker.alive:
                os.kill(os.getpid(), signal.SIGINT)
            time.sleep(self._interval)


class RestartableUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {"lifespan": "off", "loop": "asyncio", "http": "h11"}

    def __init__(self, *args: list[Any], **kwargs: dict[str, Any]):
        super().__init__(*args, **kwargs)
        self._reloader_thread = ReloaderThread(self)

    def run(self) -> None:
        if self.cfg.reload:
            self._reloader_thread.start()
        super().run()


class DynamicWorker(UvicornWorker):
    if os.getenv("ENV") == "dev":
        CONFIG_KWARGS = {
            "lifespan": "off",
            "loop": "asyncio",
            "http": "h11",
            "reload": True,
        }
    else:
        CONFIG_KWARGS = {"lifespan": "off"}

    def __init__(self, *args: list[Any], **kwargs: dict[str, Any]):
        if os.getenv("ENV") == "dev":
            super().__init__(*args, **kwargs)
            self._reloader_thread = ReloaderThread(self)
        else:
            super().__init__(*args, **kwargs)

    def run(self) -> None:
        if os.getenv("ENV") == "dev" and self.cfg.reload:
            self._reloader_thread.start()
        super().run()
