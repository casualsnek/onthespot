import threading
import time
from threading import Lock
from typing import List, Callable, Dict, Set

from .configuration import ConfigurationService
from .sessions import SessionsService
from queue import Queue
from lmttfy.thread import invoke_in_thread
from ..job import MediaDownloadJob, JobStatus


class DownloaderService:
    def __init__(self, config_service: ConfigurationService, sessions_service: SessionsService):
        self.__config_service: ConfigurationService = config_service
        self.__sessions_service: SessionsService = sessions_service
        self.__queue: Queue[MediaDownloadJob] = Queue()
        self.__job_active_in_threads: List[MediaDownloadJob] = []
        self.tracked_jobs_by_id: Dict[str, MediaDownloadJob] = {}
        self.cancelled_media_ids: Set[str] = set()
        self.__lock: threading.Lock = Lock()
        self.__new_job_handlers: List[Callable] = []

    @invoke_in_thread(max_concurrent_execs=1)
    def start(self):
        while True:
            if len(self.__job_active_in_threads) <= self.__config_service.get("max_concurrent_downloads"):
                job: MediaDownloadJob = self.__queue.get()
                if job.status == JobStatus.Cancelled:
                    self.cancelled_media_ids.add(job.media.id)
                    continue
                job.fetch_media(self.__sessions_service).on_complete(lambda ret: self.__remove_thread(job)).on_error(
                    lambda e: self.__remove_thread(job)
                )
                with self.__lock:
                    self.__job_active_in_threads.append(job)
            else:
                time.sleep(1)

    def __remove_thread(self, job: MediaDownloadJob):
        with self.__lock:
            self.__job_active_in_threads.remove(job)


    def add_job(self, job: MediaDownloadJob):
        # IMPORTANT: When canceling a job:
        # 1. If you only remove it from the view but keep it in jobs_by_media_id, the 'on_new_job' signal won't trigger when the job is re-added.
        # 2. To properly handle job re-adding, ensure you remove the job from both the view and jobs_by_media_id.

        ## If the same job is in cancel queue, remove it from cancel queue and just update the job status
        is_new_job: bool = False
        if job.media.id in self.cancelled_media_ids:
            # The song was canceled earlier, but it's being added again, it's old graphical view should be preserved
            self.cancelled_media_ids.remove(job.media.id)
        if job.media.id not in self.tracked_jobs_by_id:
            is_new_job = True
            self.tracked_jobs_by_id[job.media.id] = job
        self.tracked_jobs_by_id[job.media.id].reset()
        if not is_new_job and job.media.id not in self.cancelled_media_ids:
            # It's an old/canceled job not processed in queue yet, so no need to add in queue
            pass
        else:
            # It is a new job. So maybe send signals as well ??
            self.__queue.put(self.tracked_jobs_by_id[job.media.id])
        for handler in self.__new_job_handlers:
            handler(self.tracked_jobs_by_id[job.media.id])

    def on_new_job(self, handler: Callable):
        if handler not in self.__new_job_handlers:
            self.__new_job_handlers.append(handler)

    def remove_on_new_job(self, handler: Callable):
        if handler not in self.__new_job_handlers:
            return
        self.__new_job_handlers.remove(handler)


    @staticmethod
    def cancel_job(job: MediaDownloadJob):
        # IMPORTANT: When canceling a job:
        # 1. If you only remove it from the view but keep it in jobs_by_media_id, the 'on_new_job' signal won't trigger when the job is re-added.
        # 2. To properly handle job re-adding, ensure you remove the job from both the view and jobs_by_media_id.
        job.cancel()


