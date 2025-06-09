from collections.abc import Callable
from threading import Lock
from typing import List, Any
from enum import Enum
from .configuration import ConfigurationService
from .sessions import SessionsService
from queue import Queue
from lmttfy.thread import invoke_in_thread, ThreadedCall
from ..job import MediaDownloadJob


class DownloaderService:
    def __init__(self, config_service: ConfigurationService, sessions_service: SessionsService):
        self.__config_service = config_service
        self.__sessions_service = sessions_service
        self.__queue: Queue[MediaDownloadJob] = Queue()
        self.__threads = []
        self.__lock = Lock()

    @invoke_in_thread(max_concurrent_execs=1)
    def start(self):
        while True:
            if len(self.__threads) <= self.__config_service.get("max_concurrent_downloads"):
                job: MediaDownloadJob = self.__queue.get()
                job.fetch_media(self.__sessions_service).on_complete(lambda ret: self.__remove_thread(job)).on_error(
                    lambda e: self.__remove_thread(job)
                )
                with self.__lock:
                    self.__threads.append(job)

    def __remove_thread(self, job: MediaDownloadJob):
        with self.__lock:
            self.__threads.remove(job)


    def add_job(self, job: MediaDownloadJob):
        self.__queue.put(job)

