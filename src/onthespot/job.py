from enum import Enum
from typing import Callable, Any, List
from lmttfy import invoke_in_thread, ThreadedCall
from .services.sessions import SessionsService
from otslib.core.__base__ import AbstractMediaItem
from otslib.common.url import
class DownloadStatus(Enum):
    Pending = 0
    Downloading = 1
    Error = 2
    Success = 3
    Cancelled = 4

# This needs a lot of work
class MediaDownloadJob:
    def __init__(self, media: AbstractMediaItem,
                 on_progress: Callable,
                 on_complete: Callable,
                 on_error: Callable,
                 after_fetch: Callable
                 ):
        # Media metadata
        self.__media = AbstractMediaItem

        # Download state
        self.__bytes_downloaded = 0
        self.__bytes_total = 0
        self.__status = DownloadStatus.Pending
        self.__status_text = "Pending"

        # Download paths
        self.___temp_download_path = None
        self.__media_download_destination = None  # Set by transcoder

        # Event handlers
        self.__on_complete = on_complete  # When both download and transcoding are done
        self.__on_progress = on_progress  # When download progress is updated
        self.__on_error = on_error  # When download fails
        self.__on_success = after_fetch  # When download succeeds and transcoding begins

    @invoke_in_thread(max_concurrent_execs=1)
    def fetch_media(self, session_service: SessionsService) -> None|ThreadedCall:
        pass

class CollectionsDownloadJobMaker:
    def __init__(self, media_uuid: str, media_type: int,
                 on_progress: Callable,
                 on_complete: Callable,
                 on_error: Callable,
                 on_success: Callable,
                 ):
        self.__media_uuid = media_uuid
        self.__media_type = media_type

        # Event handlers
        self.__on_complete = on_complete  # When both download and transcoding are done
        self.__on_progress = on_progress  # When download progress is updated
        self.__on_error = on_error  # When download fails
        self.__on_success = on_success  # When download succeeds and transcoding begins


    @invoke_in_thread(max_concurrent_execs=1)
    def make_jobs(self, parsing_session: Any) -> List[MediaDownloadJob]: # Boo hoo, scary
        # Begin parsing
        medias: List[MediaDownloadJob] = []
        return medias
