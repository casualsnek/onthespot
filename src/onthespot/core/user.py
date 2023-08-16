from ..core.mediaitem import SpotifyPlaylist, SpotifyTrackMedia
from ..common.utils import pick_thumbnail
from typing import Union
import importlib
import requests
import os
import json


class SpotifyUser:
    def __init__(self, session_path: str, session: Union['Session', None] = None):
        """
        Creates a Spotify User instance, providing access to basic user profile/playlist and session
        :param session_path: Path to session saved by python-librespot
        """
        self.__session_json_path: str = session_path  # Path where the session is saved
        self.uuid: str = ''
        if session is None:
            self.init_session()
        else:
            self.__session = session
        self_api: str = 'https://api.spotify.com/v1/me'
        self_info: dict = json.loads(
            requests.get(self_api, headers=self.req_header_scoped('user-read-private')).content
        )
        self.__userid: str = self_info['id']
        self.display_name: str = self_info.get('display_name')
        self.country: str = self_info.get('country')
        self.email: str = self_info.get('email')
        self.follower_count: int = self_info['followers']['total']
        self.explicit_filter_enabled: bool = self_info['explicit_content']['filter_enabled']
        self.explicit_filter_locked: bool = self_info['explicit_content']['filter_locked']
        self._type: str = self_info['type']
        self.__covers: list[dict] = self_info['images']

    def init_session(self):
        """
        Inits/Re-Inits a librespot session from the set session path
        :return: None
        """
        if not os.path.isfile(self.__session_json_path):
            raise FileNotFoundError('The saved session could not be found !')
        del self.__session

        py_librespot = importlib.import_module('librespot.core')
        config = py_librespot.Session.Configuration.Builder().set_stored_credential_file(
            self.__session_json_path
        ).build()
        self.__session = py_librespot.Session.Builder(
            conf=config
        ).stored_file(
            self.__session_json_path
        ).create()

    @staticmethod
    def from_user_pass(username: str, password: str, session_path: Union[str, None] = None, uuid: str = '', ) \
            -> 'SpotifyUser':
        """
        Create a SpotifyUser instance from username, password combination
        :param username: Spotify username/email
        :param password: Spotify password
        :param uuid: UUID, Optional for tracking
        :param session_path: Path where the created session will be saved
        :return: SpotifyUser Instance
        """
        session_path = f'{username.split("@")[0]}_ots.json' if session_path is None else session_path
        py_librespot = importlib.import_module('librespot.core')
        config = py_librespot.Session.Configuration.Builder().set_stored_credential_file(
            session_path
        ).build()
        session = py_librespot.Session.Builder(conf=config).user_pass(username, password).create()
        profile = SpotifyUser(session_path=session_path, session=session)
        profile.uuid = uuid
        return profile

    def auth_token_scoped(self, scope: str = "user-read-email") -> str:
        """
        Returns auth token with particular scope access
        :param scope: name of scope
        :return: str
        """
        return self.__session.tokens().get(scope)

    def req_header_scoped(self, scope: str = "user-read-email") -> dict:
        """
        Returns basic authorization header with auth scoped auth token for use with spotify API requests
        :return: dict
        """
        return {"Authorization": "Bearer %s" % self.auth_token_scoped(scope)}

    def like_track(self, tracks: list[SpotifyTrackMedia]) -> bool:
        """
        Add a spotify track to user's liked playlist
        :param tracks: List of SpotifyTrackMedia instances
        :return: bool
        """
        if len(tracks) > 50:
            raise RuntimeError('Only 50 tracks can be liked at a time !')
        liked_add_api: Union[str, None] = 'https://api.spotify.com/v1/me/tracks?ids='+','.join(
            track.id for track in tracks
        )
        r = requests.put(liked_add_api, headers=self.req_header_scoped('user-library-modify'))
        return r.status_code == 200

    def unlike_track(self, tracks: list[SpotifyTrackMedia]) -> bool:
        """
        Removes spotify tracks from user's liked playlist
        :param tracks: List of SpotifyTrackMedia instances
        :return: bool
        """
        if len(tracks) > 50:
            raise RuntimeError('Only 50 tracks can be unliked at a time !')
        liked_remove_api: Union[str, None] = 'https://api.spotify.com/v1/me/tracks?ids='+','.join(
            track.id for track in tracks
        )
        r = requests.delete(liked_remove_api, headers=self.req_header_scoped('user-library-modify'))
        return r.status_code == 200

    def has_liked_track(self, tracks: list[SpotifyTrackMedia]) -> list[bool]:
        """
        Checks if user has liked specified spotify tracks
        :param tracks: List of SpotifyTrackMedia instances
        :return: bool
        """
        if len(tracks) > 50:
            raise RuntimeError('Only 50 tracks can be checked at a time !')
        like_check_api: Union[str, None] = 'https://api.spotify.com/v1/me/tracks/contains?ids=' + ','.join(
            track.id for track in tracks
        )
        return json.loads(
            requests.get(like_check_api, headers=self.req_header_scoped('user-library-read')).content
        )

    @property
    def session(self) -> 'Session':
        """
        Returns the assigned librespot session
        :return:
        """
        return self.__session

    @property
    def auth_token(self) -> str:
        """
        Returns the auth token for the account
        :return:
        """
        return self.auth_token_scoped()

    @property
    def playlists(self) -> list[SpotifyPlaylist]:
        """
        Returns list of user's playlist
        :return:
        """
        my_library_api: Union[str, None] = 'https://api.spotify.com/v1/me/playlists'
        while True:
            my_library_info: dict = json.loads(
                requests.get(my_library_api, headers=self.req_header_scoped('playlist-read-private')).content
            )
            for playlist_item in my_library_info['items']:
                playlist = SpotifyPlaylist(
                    playlist_id=playlist_item['id'],
                    session=self,
                )
                playlist._covers = playlist_item['images']
                playlist.set_partial_meta(
                    {
                        'name': playlist_item['name'],
                        'collaborative': playlist_item['collaborative'],
                        'public': playlist_item['public'],
                        'total_tracks': int(playlist_item['tracks']['total']),
                        'description': playlist_item['description'],
                        'url': playlist_item['external_urls']['spotify'],
                        'scraped_id': playlist_item['id'],
                        'thumbnail_url': pick_thumbnail(playlist_item['images'], preferred_size=640000),
                        'owner_name': playlist_item['owner']['display_name'],
                        'owner_id': playlist_item['owner']['id'],
                        'owner_url': playlist_item['owner']['external_urls']['spotify'],
                    }
                )
                yield playlist
            my_library_api = my_library_info.get('next', '')
            if my_library_api is None or my_library_api == '':
                break

    @property
    def liked(self) -> list[SpotifyTrackMedia]:
        """
        Returns list of songs liked by user
        :return: list[SpotifyTrackMedia]
        """
        my_liked_api: Union[str, None] = 'https://api.spotify.com/v1/me/tracks'
        while True:
            my_liked_info: dict = json.loads(
                requests.get(my_liked_api, headers=self.req_header_scoped('user-library-read')).content
            )
            for track_item in my_liked_info['items']:
                track = SpotifyTrackMedia(
                    track_id=track_item['track']['id'],
                    session=self,  # TODO: Fix http cache

                )
                track._covers = track_item['track']['album']['images']
                track.set_partial_meta({
                    'artists': [
                        data['name']
                        for data in
                        track_item['track']['artists']
                    ],
                    'album_name': track_item['track']['album']['name'],
                    'name': track_item['track']['name'],
                    'url': track_item['track']['external_urls']['spotify'],
                    'artist_url': track_item['track']['artists'][0]['external_urls']['spotify'],
                    'artist_id': track_item['track']['artists'][0]['id'],
                    'album_url': track_item['track']['album']['external_urls']['spotify'],
                    'album_id': track_item['track']['album']['id'],
                    'thumbnail_url': pick_thumbnail(track_item['track']['album']['images'], preferred_size=640000),
                    'release_year': int(track_item['track']['album']['release_date'].split("-")[0]),
                    'release_month': int(track_item['track']['album']['release_date'].split("-")[1]),
                    'release_day': int(track_item['track']['album']['release_date'].split("-")[2]),
                    'disc_number': int(track_item['track']['disc_number']),
                    'track_number': int(track_item['track']['track_number']),
                    'total_tracks': int(track_item['track']['album']['total_tracks']),
                    'preview_url': track_item['track']['preview_url'],
                    'scraped_id': track_item['track']['id'],
                    'popularity': track_item['track']['popularity'],
                    'isrc': track_item['track']['external_ids'].get('isrc', None),
                    'upc': track_item['track']['external_ids'].get('upc', None),
                    'ean': track_item['track']['external_ids'].get('ean', None),
                    'duration': track_item['track']['duration_ms'],
                    'explicit': track_item['track']['explicit'],
                })
                yield track
            my_liked_api = my_liked_info.get('next', '')
            if my_liked_api is None or my_liked_api == '':
                break

    @property
    def userid(self) -> str:
        """
        Returns current user's spotify ID
        :return:
        """
        return self.__userid

    @property
    def is_premium(self) -> bool:
        """
        Returns spotify premium status of current user
        :return: bool
        """
        if int(os.environ.get('OTS_DEBUG_ASSUME_PREMIUM', 0)) or \
                self.__session.get_user_attribute("type") == "premium":
            return True
        return False

    def get_pfp_url(self, preferred_size: int = 640000) -> str:
        """
        Returns url for the profile picture
        :param preferred_size: Size of media (width*height) which will be returned or next available better one
        :return: Url of the cover art for media
        """
        return pick_thumbnail(self.__covers, preferred_size=preferred_size)

    @property
    def hq_profile_image_url(self) -> str:
        """
        Returns HQ profile image URL
        :return: string|URL
        """
        return self.get_pfp_url(preferred_size=99999999)

    @property
    def req_header(self) -> dict:
        """
        Returns basic authorization header for use with spotify API requests
        :return: dict
        """
        return self.req_header_scoped()

    def __eq__(self, other) -> bool:
        """
        Returns true if two SpotifyUser instance belong to same spotify user
        :param other: Another SpotifyUser instance to check against
        :return: Bool
        """
        return self.userid == other.userid
