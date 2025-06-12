import asyncio
import platform
import re
import subprocess
from typing import List, Callable
from lmttfy import invoke_in_thread, ThreadedCall
from otslib.core import SpotifyTrackMedia
from src.onthespot.services.configuration import ConfigurationService
from src.onthespot.services.sessions import SessionsService
from otslib.core.search import SearchResult

if platform.system() == "Windows":
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager

class NowPlayingService:
    def __init__(self, config_service: ConfigurationService, session_service: SessionsService):
        self.last_url: str = ''
        self.__stop: bool = False
        self.__config_service: ConfigurationService = config_service
        self.__session_service: SessionsService = session_service
        self.__onchange_handlers: List[Callable] = []
        self.__media_tracker_last_query: str = ''
        self.__config_service.on_change("nowplaying_auto_download", self.__setting_changed)
        self.__watch_call : ThreadedCall|None = None

    def __setting_changed(self, key, old_value, new_value):
        if key == "nowplaying_auto_download" and new_value is False:
            self.__stop = True
            if self.__watch_call is not None:
                self.__watch_call.wait()
        elif key == "nowplaying_auto_download" and new_value is True:
            self.__stop = False
            self.__watch_call = self.__watch()

    @invoke_in_thread(max_concurrent_execs=1)
    def __watch(self) -> None|ThreadedCall:
        while not self.__stop:
            spotify_url: str = ""
            if platform.system() == "Linux":
                try:
                    playerctl_out = subprocess.check_output(["playerctl", "-p", "spotify", "metadata"])
                    found = re.search(r"((spotify xesam:url).*https://open.spotify.*\n)", playerctl_out.decode())
                    if found:
                        spotify_url = found.group(1).replace("spotify xesam:url", "").strip()
                except subprocess.CalledProcessError:
                    pass
            elif platform.system() == "Windows":
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                info_dict = None
                sessions = loop.run_until_complete(MediaManager.request_async())
                current_session = sessions.get_current_session()
                if current_session:
                    if current_session.source_app_user_model_id == "Spotify.exe":
                        info = loop.run_until_complete(current_session.try_get_media_properties_async())
                        info_dict = {song_attr: info.__getattribute__(song_attr) for song_attr in dir(info) if
                                     song_attr[0] != '_'}
                        info_dict['genres'] = list(info_dict['genres'])
                if info_dict:
                    query_str = f"{info_dict['title']} {info_dict['artist']} {info_dict['album_title']}".strip()
                    if self.__media_tracker_last_query != query_str:
                        results_tracks: List[SpotifyTrackMedia] = SearchResult.from_term(
                            query_str,
                            user=self.__session_service.get_parsing_session(),
                            max_results=3
                        ).tracks
                        self.__media_tracker_last_query = query_str
                        if len(results_tracks) > 0:
                            spotify_url = results_tracks[0].meta_url
            if spotify_url != self.last_url and spotify_url.strip() != "":
                self.last_url = spotify_url
                for handler in self.__onchange_handlers:
                    handler(spotify_url)
        return None

    def on_track_change(self, handler: Callable):
        if handler not in self.__onchange_handlers:
            self.__onchange_handlers.append(handler)

    def remove_on_track_change(self, handler: Callable):
        if handler in self.__onchange_handlers:
            self.__onchange_handlers.remove(handler)

    def stop(self):
        self.__stop = True