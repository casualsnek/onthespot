import time
from threading import Lock
from .configuration import ConfigurationService
from .sessions import SessionsService
from queue import Queue
from lmttfy.thread import invoke_in_thread
from ..job import MediaDownloadJob, JobStatus


class DownloaderService:
    def __init__(self, config_service: ConfigurationService, sessions_service: SessionsService):
        self.__config_service = config_service
        self.__sessions_service = sessions_service
        self.__queue: Queue[MediaDownloadJob] = Queue()
        self.__threads = []
        self.jobs_by_media_id = {}
        self.cancelled_media_ids = set()
        self.__lock = Lock()

    @invoke_in_thread(max_concurrent_execs=1)
    def start(self):
        while True:
            if len(self.__threads) <= self.__config_service.get("max_concurrent_downloads"):
                job: MediaDownloadJob = self.__queue.get()
                if job.status == JobStatus.Cancelled:
                    self.cancelled_media_ids.add(job.media.id)
                    continue
                job.fetch_media(self.__sessions_service).on_complete(lambda ret: self.__remove_thread(job)).on_error(
                    lambda e: self.__remove_thread(job)
                )
                with self.__lock:
                    self.__threads.append(job)
            else:
                time.sleep(1)

    def __remove_thread(self, job: MediaDownloadJob):
        with self.__lock:
            self.__threads.remove(job)


    def add_job(self, job: MediaDownloadJob):
        # IMPORTANT: When canceling a job:
        # 1. If you only remove it from the view but keep it in jobs_by_media_id, the 'on_new_job' signal won't trigger when the job is re-added.
        # 2. To properly handle job re-adding, ensure you remove the job from both the view and jobs_by_media_id.

        ## If the same job is in cancel queue, remove it from cancel queue and just update the job status
        is_new_job: bool = False
        if job.media.id in self.cancelled_media_ids:
            # The song was cancelled earlier, but it's being added again, it's old graphical view should be preserved
            self.cancelled_media_ids.remove(job.media.id)
        if job.media.id not in self.jobs_by_media_id:
            is_new_job = True
            self.jobs_by_media_id[job.media.id] = job
        self.jobs_by_media_id[job.media.id].reset()
        if not is_new_job and job.media.id not in self.cancelled_media_ids:
            # It's an old/cancelled job which is not processed in queue yet, so no need to add in queue
            pass
        else:
            # It's a new job. so maybe send signals as well ??
            self.__queue.put(self.jobs_by_media_id[job.media.id])

    @staticmethod
    def cancel_job(job: MediaDownloadJob):
        # IMPORTANT: When canceling a job:
        # 1. If you only remove it from the view but keep it in jobs_by_media_id, the 'on_new_job' signal won't trigger when the job is re-added.
        # 2. To properly handle job re-adding, ensure you remove the job from both the view and jobs_by_media_id.
        job.cancel()

