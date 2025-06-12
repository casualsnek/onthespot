import os
from enum import Enum
from threading import Lock
from typing import Callable, Any, List
from lmttfy import invoke_in_thread, ThreadedCall
from otslib.exceptions import StreamReadException
from .utils.utils import convert_media, set_audio_tags, set_music_thumbnail
from .services.configuration import ConfigurationService
from .services.sessions import SessionsService
from otslib.core.__base__ import AbstractMediaItem, AbstractMediaCollection
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
                 on_progress: List[Callable]|None = None,
                 on_complete: List[Callable]|None = None,
                 on_error: List[Callable[['MediaDownloadJob', Exception, ...], Any]] | None = None,
                 after_fetch: List[Callable]|None = None
                 ):
        # Media metadata
        self.__media = media

        # Download state
        self.__bytes_downloaded = 0
        self.__bytes_total: int = 0
        self.__status = JobStatus.Pending
        self.__status_text = "Pending"

        # Download paths
        self.___temp_download_file = None
        self.__media_download_destination: Path|None = None  # Set by transcoder

        # Event handlers
        self.on_complete: List[Callable] = on_complete if on_complete else []  # When both download and transcoding are done
        self.on_progress: List[Callable] = on_progress if on_complete else []  # When download progress is updated
        self.on_error: List[Callable] = on_error if on_complete else [] # When download fails
        self.after_fetch: List[Callable] = after_fetch if on_complete else []  # When download succeeds and transcoding begins

        self.part_of_playlist = False

    @invoke_in_thread(max_concurrent_execs=1)
    def fetch_media(self, session_service: SessionsService, config_service: ConfigurationService) -> None|ThreadedCall:
        # TODO: Add retry mechanism
        """
        Downloads the media associated with this job and calls the on_progress handlers on every chunk.

        :param session_service: The SessionsService instance to use for creating a user session
        :param config_service: The ConfigurationService instance to get configuration values from
        :return: None or a ThreadedCall that represents the running thread
        """
        self.___temp_download_file = NamedTemporaryFile("wb", delete=True, delete_on_close=True)
        chunk_size: int = config_service.get('download_chunk_size')
        try:
            with session_service.rotated_session() as spotify_user:
                self.__bytes_total: int = self.__media.media_stream.input_stream.size
                self.__status_text = "Downloading"
                self.__status = JobStatus.Downloading
                self.__media.set_user(spotify_user)
                # TODO: Maybe check if the media is playable before downloading
                while self.__bytes_downloaded < self.__bytes_total and self.__status == JobStatus.Downloading:
                    data: bytes = self.__media.media_stream.input_stream.stream().read(chunk_size)
                    if len(data) != 0:
                        self.___temp_download_file.write(data)
                        self.__bytes_downloaded += len(data)
                        for progress_handler in self.on_progress:
                            progress_handler(self)
                    if len(data) == 0 and chunk_size <= config_service.get('skip_bytes_at_the_end'):
                        break
                    if (self.__bytes_total - self.__bytes_downloaded) < chunk_size:
                        chunk_size = self.__bytes_total - self.__bytes_downloaded
                    if len(data) == 0 and chunk_size > config_service.get('skip_bytes_at_the_end'):
                        self.__media.reset_stream()
                        self.__bytes_downloaded = 0
                        self.__status_text = "Failed. Retrying"
                        e: Exception = StreamReadException(
                            f'SRE000: Failed to stream for media "{self.__media.id}" properly.Might be due to parallel use of session. '
                            f'{self.__bytes_total - self.__bytes_downloaded} bytes were not read ! Ignorable bytes: {config_service.get('skip_bytes_at_the_end')}'
                        )
                        raise e
                if self.__status == JobStatus.Cancelled:
                    self.__status_text = "Download Cancelled"
                if self.__bytes_downloaded >= self.__bytes_total or (self.__bytes_total - self.__bytes_downloaded) <= config_service.get('skip_bytes_at_the_end'):
                    self.__bytes_downloaded = self.__bytes_total
                    self.__status = JobStatus.Transcoding
                    self.__status_text = "Fetch Successful"
                    for after_fetch_handler in self.after_fetch:
                        after_fetch_handler(self)
        except StreamReadException as e:
            self.__status = JobStatus.Error
            self.__status_text = "Download Error"
            for error_handler in self.on_error:
                error_handler(self, e)

    @invoke_in_thread(max_concurrent_execs=1)
    def transcode(self, config_service: ConfigurationService,):
        """
        This function is run in a separate thread and will transcode the downloaded file using ffmpeg.
        The output file is placed in the download directory specified in the configuration.
        The file is converted to the target format specified in the configuration.
        After transcoding, the function will set the status of the job to Success or Error depending on whether the transcoding was successful.
        It will also call the on_complete or on_error handlers as appropriate.
        :param config_service: The ConfigurationService instance to get configuration values from
        :return: None
        """
        self.__status = JobStatus.Transcoding
        self.__status_text = "Transcoding"
        name_format_scheme: str = config_service.get('file_name_format')
        if config_service.get('use_alternate_formatter_for_playlist', False):
            name_format_scheme = config_service.get('playlist_alternate_formatter')
        self.__media_download_destination: Path|None = Path(
            os.path.join(
                config_service.get("download_directory"),
                self.__media.copy_meta_to_str(name_format_scheme, is_filepath=True, use_lookalikes_in_path=True)
            )
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
                set_audio_tags(self.__media_download_destination, self.__media, config_service.get("audio_tags_seperator"))
            self.__status = JobStatus.Success
            self.__status_text = "Download Successful"
            for progress_handler in self.on_progress:
                progress_handler(self)
            for handler in self.on_complete:
                handler(self)
        except Exception as e:
            self.__status = JobStatus.Error
            self.__status_text = "Failed to transcode"
            self.__media_download_destination = None
            for handler in self.on_error:
                handler(self, e)
            for progress_handler in self.on_progress:
                progress_handler(self)

    def cancel(self):
        if self.__status == [JobStatus.Transcoding, JobStatus.Success]:
            # Cannot be cancelled at this stage
            return
        self.reset()
        self.__status = JobStatus.Cancelled
        self.__status_text = "Cancelled"
        for progress_handler in self.on_progress:
            progress_handler(self)

    def reset(self):
        if self.__status == [JobStatus.Transcoding, JobStatus.Success]:
            # Cannot be reset at this stage
            return
        self.__status = JobStatus.Pending
        self.__status_text = "Pending"
        self.__media_download_destination = None
        self.__media.reset_stream()
        self.__bytes_downloaded = 0
        for progress_handler in self.on_progress:
            progress_handler(self)

    @property
    def progress(self) -> float:
        return (self.__bytes_downloaded / self.__bytes_total * 100) - 5 + 5 if self.__status == JobStatus.Success else 0

    @property
    def destination(self) -> Path|None:
        return self.__media_download_destination

    @property
    def status(self) -> JobStatus:
        return self.__status

    @property
    def status_text(self) -> str:
        return self.__status_text

    @property
    def media(self) -> AbstractMediaItem:
        return self.__media


class CollectionsDownloadJobMaker:
    def __init__(self, collection: AbstractMediaCollection,
                 on_progress: List[Callable] | None = None,
                 on_complete: List[Callable] | None = None,
                 on_error: List[Callable[[MediaDownloadJob, Exception, ...], Any]] | None = None,
                 after_fetch: List[Callable]|None = None,
                 config_service: ConfigurationService|None = None
                 ):
        self.__collection = collection
        self.__succeed_jobs: List[MediaDownloadJob] = []
        self.__failed_jobs: List[MediaDownloadJob] = []
        self.__all_jobs: List[MediaDownloadJob] = []
        self.__lock  = Lock()
        self.__config_service = config_service
        # Event handlers
        self.on_complete: List[Callable] = on_complete if on_complete else []  # When both download and transcoding are done
        self.on_progress: List[Callable] = on_progress if on_complete else []  # When download progress is updated
        self.on_error: List[Callable] = on_error if on_complete else []  # When download fails
        self.after_fetch: List[Callable] = after_fetch if on_complete else []  # When download succeeds and transcoding begins


    @invoke_in_thread(max_concurrent_execs=1)
    def make_jobs(self) -> List[MediaDownloadJob]: # Boo hoo, scary
        # Begin parsing
        self.__all_jobs: List[MediaDownloadJob] = []
        for item in self.__collection.items:
            job: MediaDownloadJob = MediaDownloadJob(item, on_progress=self.on_progress, on_complete=self.on_complete, on_error=self.on_error, after_fetch=self.after_fetch)
            job.part_of_playlist = True
            job.on_complete.extend([lambda j: self.__succeed_jobs.append(j), lambda j, e: self.__try_make_m3u()])
            job.on_error.extend([lambda j, e: self.__failed_jobs.append(j), lambda j, e: self.__try_make_m3u()])
            self.__all_jobs.append(job)
        return self.__all_jobs

    def __try_make_m3u(self):
        if self.__config_service is None:
            return
        if self.__config_service.get("enable_m3u_playlist", False) is False:
            return
        with self.__lock:
            all_done = len(self.__failed_jobs) + len(self.__succeed_jobs) == len(self.__all_jobs)
            playlist_file: str = os.path.join(
                self.__config_service.get("m3u_playlist_directory"),
                self.__collection.copy_meta_to_str(self.__config_service.get("m3u_playlist_formatter"))
                )
            playlist_file = playlist_file if playlist_file.endswith(".m3u") else playlist_file + ".m3u"
            os.makedirs(os.path.dirname(playlist_file), exist_ok=True)
            if all_done:
                with open(playlist_file, "w", encoding="utf-8") as m3u_file:
                    m3u_file.write("#EXTM3U\n")
                    for i in range(len(self.__all_jobs)):
                        job: MediaDownloadJob = self.__all_jobs[i]
                        if job not in self.__succeed_jobs:
                            continue
                        m3u_file.write(
                                f'#EXTINF:{i+1}, {job.media.meta_name} BY {job.media.meta_artists[0]}\n'
                                f'{job.destination}\n'
                            )
