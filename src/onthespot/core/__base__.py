import subprocess
import threading
import time
from typing import Optional, Any, Union, TYPE_CHECKING
from io import BytesIO
import requests
from PIL import Image
from librespot.audio import PlayableContentFeeder
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.metadata import TrackId, EpisodeId
from ..expections import MedaFetchInterruptedException, ThumbnailUnavailableException, UnknownMediaTypeException, \
    UnplayableMediaException, StreamReadException
from ..common.utils import pick_thumbnail

if TYPE_CHECKING:
    from ..core.user import SpotifyUser


class SpotifyMediaProperty:
    """
    This class defines the base for Media and Media Collection classe, and houses common functions for similar tasks
    """
    __id: Union[str, None] = None
    _covers: Union[list[dict], None] = None
    _metadata: Union[dict, None] = None
    _thumbnail: Union[BytesIO, None] = None
    _user: Union['SpotifyUser', None] = None
    __token: Union[str, None] = None
    _FULL_METADATA_ACQUIRED: bool = False

    def __init__(self, media_id: str):
        """
        Base class that represents a media or media collection on spotify
        :param media_id:  ID of media / media collection
        :return:
        """
        self.__id = media_id

    def _fetch_metadata(self) -> None:
        """
        Function to fetch metadata for a spotify object, to be implemented by children
        :return:
        """
        pass

    def get_thumbnail_url(self, preferred_size: int = 640000) -> str:
        """
        Returns url for the artwork from available artworks
        :param preferred_size: Size of media (width*height) which will be returned or next available better one
        :return: Url of the cover art for media
        """
        return pick_thumbnail(self._covers, preferred_size=preferred_size)

    def set_partial_meta(self, meta_dict: dict) -> None:
        """
        Sets martial metadata for a media property
        :param meta_dict: Dictionary containing meta keys/values
        :return:
        """
        self._FULL_METADATA_ACQUIRED = False
        if self._metadata is None:
            self._metadata = {}
        for key in meta_dict:
            self._metadata[key] = meta_dict[key]

    def get_meta_keys(self, disable_filters: bool = False) -> list[str]:
        """
        Returns the available metadata keys
        :param disable_filters: Show all metadata keys even if they are not string or integer
        :return: list[str] | list of keys
        """
        keys: list[str] = []
        for key in self._metadata.keys():
            data_type = type(self._metadata[key])
            if data_type is bool or data_type is int or data_type is str or disable_filters:
                keys.append(key)
        return keys

    def get_thumbnail(self, preferred_size: int = 640000) -> bytes:
        """
         Returns the thumbnail of preferred size for current media as BytesIO object
        :return: BytesIO containing the thumbnail
        """
        if self._thumbnail is None:
            self._thumbnail = BytesIO()
            thumbnail_url = self.get_thumbnail_url(preferred_size)
            if thumbnail_url == '':
                raise ThumbnailUnavailableException(f'No thumbnail available for media: {self.id}')
            img = Image.open(
                BytesIO(requests.get(thumbnail_url).content)
            )
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(self._thumbnail, format='png')
        self._thumbnail.seek(0)
        return self._thumbnail.read()

    def set_user(self, user: 'SpotifyUser') -> None:
        """
        Sets the librespot session to be used with spotify
        :param user: SpotifyUser to use by default
        :return:
        """
        self._user = user

    @property
    def session_token(self) -> str:
        """
        Returns the current session token being used for requests to spotify from this instance
        :return: String: Session token
        """
        if self.__token is None:
            self.__token = self._user.session.tokens().get("user-read-email")
        return self.__token

    @property
    def req_header(self) -> dict:
        """
        Returns basic authorization header for use with spotify API requests
        :return: dict
        """
        return {"Authorization": "Bearer %s" % self.session_token}

    @property
    def hq_thumbnail(self) -> bytes:
        """
        Returns the high-quality thumbnail for current media as BytesIO object
        :return: BytesIO containing the thumbnail
        """
        return self.get_thumbnail()

    @property
    def id(self) -> str:
        """
        Returns spotify media id of current media
        :return: String spotify id of media
        """
        return self.__id

    def __getattribute__(self, name: str) -> Any:
        """
        Gets attribute of class, in this particular one add support for accessing metadata name with meta_ prefix
        :param name: Attribute
        :return:
        """
        if name.startswith('meta_') and name != 'meta_':
            meta_key = name[5:]
            metadata = object.__getattribute__(self, '_metadata')
            metadata = {} if metadata is None else metadata
            if metadata == {} or (meta_key not in metadata and self._FULL_METADATA_ACQUIRED is False):
                self._fetch_metadata()
                self._FULL_METADATA_ACQUIRED = True
                metadata = object.__getattribute__(self, '_metadata')
            if meta_key in metadata:
                return metadata[meta_key]
            else:
                raise AttributeError('No such meta field !')
        return object.__getattribute__(self, name)


class AbstractMediaItem(SpotifyMediaProperty):
    # Media Type 0 is songs, 1 is podcast
    __media_type: Optional[int] = None
    __use_audio_quality: Union[AudioQuality, None] = None
    __stream: Union[PlayableContentFeeder.LoadedStream, None] = None

    def __init__(self, media_id: str, media_type: int) -> None:
        """
        Base class representing a singleton-playable spotify medias like tracks and episodes
        :param media_id: Spotify ID of media
        :param media_type: Type of media 0/1.
        Zero for tracks and one for episodes
        """
        self.__media_type = media_type
        super().__init__(media_id=media_id)

    def set_media_quality(self, quality: AudioQuality) -> None:
        """
        Sets the quality of audio to get for media and media streams
        :param quality: Quality of media stream, expects librespot AudioQuality
        :return:
        """
        self.__use_audio_quality = quality

    def reset_stream(self) -> None:
        """
        Resets the current media stream if it exists
        :return: None
        """
        self.__stream = None

    def get_media(self, chunk_size: int = 50000, stop_check_list: Union[list, None] = None, pg_notify=None,
                  skip_at_end_bytes: int = 167) -> bytes:
        """
        Fetches the full audio media for the media object
        :param chunk_size: Size of chunks in bytes to download
        :param stop_check_list: List in which, if the current media id is found terminates the fetching
        :param pg_notify: Function which will be called to notify the progress, target function is expected to have
        three  parameters ( int: bytes_fetched, int: bytes_total, str: Progress info text)
        :param skip_at_end_bytes: Bytes that can be safely ignored at the end of stream without calling it a failure
        :return: Complete Audio as bytes
        """
        if stop_check_list is None:
            stop_check_list = []
        raw_media: bytes = bytes()
        total_size: int = self.media_stream.input_stream.size
        while len(raw_media) < total_size and self.id not in stop_check_list:
            data: bytes = self.media_stream.input_stream.stream().read(chunk_size)
            if len(data) != 0:
                raw_media += data
            if pg_notify is not None:
                pg_notify(len(raw_media), total_size, 'Downloading')
            if len(data) == 0 and chunk_size <= skip_at_end_bytes:
                break
            if (total_size - len(raw_media)) < chunk_size:
                chunk_size = total_size - len(raw_media)
            if len(data) == 0 and chunk_size > skip_at_end_bytes:
                pg_notify(0, 1, 'Read Error')
                self.reset_stream()
                raise StreamReadException(
                    f'Failed to stream for media "{self.id}" properly.Might be due to parallel use of session. '
                    f'{total_size - len(raw_media)} bytes were not read ! Ignorable bytes: {skip_at_end_bytes}'
                )
        if self.id in stop_check_list:
            stop_check_list.pop(stop_check_list.index(self.id))
            pg_notify(0, 1, 'Cancelled')
            self.reset_stream()
            raise MedaFetchInterruptedException('Fetch interrupted by external event')
        self.reset_stream()
        return raw_media

    def media_stream_as_user(self, user: 'SpotifyUser') -> PlayableContentFeeder.LoadedStream:
        """
        Returns the media stream for the current spotify media with set user
        :return: LoadedStream
        """
        if self.__stream is not None:
            return self.__stream

        quality = AudioQuality.HIGH
        if self.__media_type not in [0, 1]:
            raise UnknownMediaTypeException('Not a track or podcast. Unknown media type !')
        if self.__use_audio_quality is None:
            if user.session.get_user_attribute("type") == "premium":
                quality = AudioQuality.VERY_HIGH
        else:
            quality = self.__use_audio_quality
        if not self.meta_is_playable:
            raise UnplayableMediaException(
                f'The media "{self.id}" of type "{self.__media_type}" is unplayable exception'
            )
        media_id: Union[TrackId, EpisodeId, None] = TrackId.from_base62(self.meta_scraped_id) \
            if self.__media_type == 0 else \
            EpisodeId.from_base62(self.meta_scraped_id)

        self.__stream = user.session.content_feeder().load(
            media_id, VorbisOnlyAudioQuality(quality), False, None
        )
        return self.__stream

    def play(self, ffplay_path: str | None = None, chunk_size=1024, skip_at_end_bytes=167) -> None:
        """
        Plays the media with ffplay.
        :param ffplay_path: Full path to ffplay binary.
        :param chunk_size: Size of chunks in bytes to read at a time.
        :param skip_at_end_bytes: Bytes at the end of stream, whom if missed can be safely ignored
        :return: None
        """

        def fetch_thread_worker(media_container: list[bytes], media_stream, chunk: int = 50000,
                                skip_at_end: int = 167) -> None:
            """
            Worker thread for fetching media
            :param media_container: Container where fetched media will be added to
            :param media_stream: media_stream property
            :param chunk: Size of chunks in bytes to read at a time
            :param skip_at_end: Bytes at the end of stream if missed can be safely ignored
            :return: None
            """
            total_size: int = media_stream.input_stream.size
            size_fetched: int = 0
            while size_fetched < total_size:
                data: bytes = self.media_stream.input_stream.stream().read(chunk)
                if len(data) == 0 and chunk <= skip_at_end:
                    break
                if (total_size - size_fetched) < chunk:
                    chunk = total_size - size_fetched
                if len(data) == 0 and chunk > skip_at_end:
                    media_container.append(b'')
                    raise StreamReadException(
                        f'Failed to stream for media "{self.id}" properly. Might be due to parallel use of session. '
                        f'{total_size - size_fetched} bytes were not read ! Ignorable bytes: {skip_at_end}'
                    )
                size_fetched += len(data)
                media_container.append(data)
            media_container.append(b'')

        container: list[bytes] = []
        index_to_play: int = 0
        player_process = subprocess.Popen(
            ['ffplay' if ffplay_path is None else ffplay_path, '-autoexit', '-nodisp', '-i', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )
        self.reset_stream()
        thread: threading.Thread = threading.Thread(
            target=fetch_thread_worker, args=(
                container,
                self.media_stream,
                chunk_size,
                skip_at_end_bytes
            )
        )
        thread.start()
        while True:
            if len(container) > index_to_play:
                # We have some content that we can play
                playable_bytes: bytes = container[index_to_play]
                if playable_bytes == b'':
                    # Nothing to play
                    break
                player_process.stdin.write(playable_bytes)
                index_to_play += 1
            else:
                # Wait until we have any playable bytes from the thread
                time.sleep(0.1)
        player_process.stdin.close()
        player_process.wait()
        self.reset_stream()

    @property
    def media_stream(self) -> PlayableContentFeeder.LoadedStream:
        """
        Returns the media stream for the current spotify media with current user
        :return: LoadedStream
        """
        return self.media_stream_as_user(user=self._user)

    @property
    def type(self) -> int:
        """
        Returns a type of media this instance holds, Zero for tracks, One for podcast episode
        :return: 0 or 1
        """
        return self.__media_type


class AbstractMediaCollection(SpotifyMediaProperty):
    _items_id: Union[list[str], None] = None
    _items_partial_meta: dict = {}
    _collection_class: Any = None

    def __init__(self, collection_id: str) -> None:
        """
        Base Class for media collection entities like playlist, albums, etc.
        :param collection_id: Spotify ID of the collection
        """
        super().__init__(media_id=collection_id)

    def __len__(self):
        return self.length

    @property
    def items(self) -> list:
        """
        Returns list of items this collection holds
        :return: a list of items: Track, Playlists, Episodes
        """
        if self._items_id is None and self._FULL_METADATA_ACQUIRED is False:
            # If the item list is not yet created and full meta was not fetched, fetch it now
            self._fetch_metadata()
        for item_id in self._items_id:
            item = self._collection_class(item_id, self._user)
            item.set_partial_meta(self._items_partial_meta.get(item_id, {}))
            yield item

    @property
    def length(self) -> int:
        return len(self._items_id)
