import os
import subprocess
from enum import Enum
from typing import Callable, Any, List
from lmttfy import invoke_in_thread, ThreadedCall
from otslib.exceptions import StreamReadException
from .utils.utils import convert_media, set_audio_tags, set_music_thumbnail
from .services.configuration import ConfigurationService
from .services.sessions import SessionsService
from otslib.core.__base__ import AbstractMediaItem
from otslib.common.utils import MutableBool
from tempfile import NamedTemporaryFile
from pathlib import Path

class JobStatus(Enum):
    Pending = 0
    Downloading = 1
    Transcoding = 2
    Error = 3
    Success = 4
    Cancelled = 5

# This needs a lot of work
class MediaDownloadJob:
    def __init__(self, media: AbstractMediaItem,
                 on_progress: Callable|None = None,
                 on_complete: Callable|None = None,
                 on_error: Callable|None = None,
                 after_fetch: Callable|None = None
                 ):
        # Media metadata
        self.__media = media

        # Download state
        self.__bytes_downloaded = 0
        self.__bytes_total: int = media.media_stream.input_stream.size
        self.__status = JobStatus.Pending
        self.__status_text = "Pending"

        # Download paths
        self.___temp_download_file = None
        self.__media_download_destination: Path|None = None  # Set by transcoder

        # Event handlers
        self.__on_complete: List[Callable] = [on_complete] if on_complete else []  # When both download and transcoding are done
        self.__on_progress: List[Callable] = [on_progress] if on_complete else []  # When download progress is updated
        self.__on_error: List[Callable] = [on_error] if on_complete else [] # When download fails
        self.__after_fetch: List[Callable] = [after_fetch] if on_complete else []  # When download succeeds and transcoding begins

    @invoke_in_thread(max_concurrent_execs=1)
    def fetch_media(self, session_service: SessionsService, config_service: ConfigurationService, stop_marker: MutableBool) -> None|ThreadedCall:
        self.___temp_download_file = NamedTemporaryFile("wb", delete=True, delete_on_close=True)
        chunk_size: int = config_service.get('download_chunk_size')
        with session_service.rotated_session() as spotify_user:
            self.__status_text = "Downloading"
            self.__status = JobStatus.Downloading
            self.__media.set_user(spotify_user)
            # TODO: Maybe check if the media is playable before downloading
            while self.__bytes_downloaded < self.__bytes_total and bool(stop_marker) is False:
                data: bytes = self.__media.media_stream.input_stream.stream().read(chunk_size)
                if len(data) != 0:
                    self.___temp_download_file.write(data)
                    self.__bytes_downloaded += len(data)
                    for progress_handler in self.__on_progress:
                        progress_handler(self)
                if len(data) == 0 and chunk_size <= config_service.get('skip_bytes_at_the_end'):
                    break
                if (self.__bytes_total - self.__bytes_downloaded) < chunk_size:
                    chunk_size = self.__bytes_total - self.__bytes_downloaded
                if len(data) == 0 and chunk_size > config_service.get('skip_bytes_at_the_end'):
                    self.__media.reset_stream()
                    self.__status = JobStatus.Error
                    self.__bytes_downloaded = 0
                    self.__status_text = "Download Failed"
                    e: Exception = StreamReadException(
                        f'SRE000: Failed to stream for media "{self.__media.id}" properly.Might be due to parallel use of session. '
                        f'{self.__bytes_total - self.__bytes_downloaded} bytes were not read ! Ignorable bytes: {config_service.get('skip_bytes_at_the_end')}'
                    )
                    for error_handler in self.__on_error:
                        error_handler(self, e)
            if bool(stop_marker):
                self.__status = JobStatus.Cancelled
                self.__status_text = "Download Cancelled"
            if self.__bytes_downloaded >= self.__bytes_total or (self.__bytes_total - self.__bytes_downloaded) <= config_service.get('skip_bytes_at_the_end'):
                self.__bytes_downloaded = self.__bytes_total
                self.__status = JobStatus.Transcoding
                self.__status_text = "Fetch Successful"
                for after_fetch_handler in self.__after_fetch:
                    after_fetch_handler(self)


    @invoke_in_thread(max_concurrent_execs=1)
    def transcode(self, session_service: SessionsService, config_service: ConfigurationService,):
        self.__status = JobStatus.Transcoding
        self.__status_text = "Transcoding"
        self.__media_download_destination: Path|None = Path(
            self.__media.copy_meta_to_str("STRING HERE", is_filepath=True, use_lookalikes_in_path=True)
        ).resolve()
        os.makedirs(os.path.dirname(self.__media_download_destination), exist_ok=True)
        try:
            if config_service.get('raw_download_enabled'):
                with open(self.__media_download_destination, "wb") as raw_file:
                    raw_file.write(self.___temp_download_file.read())
                self.___temp_download_file.close()
            else:
                convert_media(config_service.get("ffmpeg_path"), self.___temp_download_file.name, self.__media_download_destination, config_service.get("ffmpeg_extra_args"))
                set_music_thumbnail(self.__media_download_destination, self.__media.hq_thumbnail)
                set_audio_tags(self.__media_download_destination, self.__media) # TODO: Fix it
            self.__status = JobStatus.Success
            self.__status_text = "Download Successful"
            for progress_handler in self.__on_progress:
                progress_handler(self)
            for handler in self.__on_complete:
                handler(self)
        except Exception as e:
            self.__status = JobStatus.Error
            self.__status_text = str(e)
            self.__media_download_destination = None
            for handler in self.__on_error:
                handler(self)
            for progress_handler in self.__on_progress:
                progress_handler(self)

    @property
    def progress(self) -> float:
        return (self.__bytes_downloaded / self.__bytes_total * 100) - 5 + 5 if self.__status == JobStatus.Success else 0

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
