from ..core.mediaitem import SpotifyPlaylist, SpotifyTrackMedia, SpotifyEpisodeMedia, SpotifyArtist
from ..common.utils import pick_thumbnail, GENRES
from typing import Union, TYPE_CHECKING
import importlib
import requests
import os
import json

if TYPE_CHECKING:
    from librespot.core import Session


def media_items_uri(items: list[SpotifyTrackMedia | SpotifyEpisodeMedia], action: str = 'removed from') -> list[str]:
    uris = []
    for item in items:
        if type(item) == SpotifyTrackMedia:
            uris.append(f'spotify:track:{item.id}')
        elif type(item) == SpotifyEpisodeMedia:
            uris.append(f'spotify:episode:{item.id}')
        else:
            raise TypeError(f'Object of type "{type(item)}" cannot be {action} playlist')
    return uris


class SpotifyUser:
    def __init__(self, session_path: str, session: Union['Session', None] = None):
        """
        Creates a Spotify User instance, providing access to basic user profile/playlist and session
        :param session_path: Path to session saved by python-librespot
        """
        self.__session_json_path: str = session_path  # Path where the session is saved
        self.uuid: str = ''
        self.__session = session
        if session is None:
            self.init_session()
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

    def like_tracks(self, tracks: list[SpotifyTrackMedia]) -> bool:
        """
        Add a spotify track to user's liked playlist
        :param tracks: List of SpotifyTrackMedia instances
        :return: bool
        """
        if len(tracks) > 50:
            raise RuntimeError('Only 50 tracks can be liked at a time !')
        liked_add_api: Union[str, None] = 'https://api.spotify.com/v1/me/tracks?ids=' + ','.join(
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
        liked_remove_api: Union[str, None] = 'https://api.spotify.com/v1/me/tracks?ids=' + ','.join(
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

    def follow_playlist(self, playlist: SpotifyPlaylist, make_public: bool = False) -> bool:
        """
        Follow a spotify playlist as a current user
        :param playlist: SpotifyPlaylist instance
        :param make_public: Set true if the followed playlist should be visible on your public profile
        :return: bool
        """
        if (playlist.meta_owner_id != self.userid and not playlist.is_public) or not playlist.is_collaborative:
            raise RuntimeError(
                f'Cannot follow a private playlist by user "{playlist.meta_owner_id}:{playlist.meta_owner_name}" '
            )
        follow_api: str = f'https://api.spotify.com/v1/playlists/{playlist.id}/followers'
        r = requests.put(
            follow_api,
            headers=self.req_header_scoped('playlist-modify-public,playlist-modify-private'),
            json={'public': make_public}
        )
        return r.status_code == 200

    def unfollow_playlist(self, playlist: SpotifyPlaylist) -> bool:
        """
        Unfollow a playlist
        :param playlist: SpotifyPlaylist instance
        :return: bool
        """
        follow_api: str = f'https://api.spotify.com/v1/playlists/{playlist.id}/followers'
        r = requests.delete(
            follow_api,
            headers=self.req_header_scoped('playlist-modify-public,playlist-modify-private'),
        )
        return r.status_code == 200

    def is_following_playlist(self, playlist: SpotifyPlaylist) -> bool:
        """
        Checks if user is following a playlist
        :param playlist: SpotifyPlaylist instances
        :return: bool
        """
        follow_api: str = f'https://api.spotify.com/v1/playlists/{playlist.id}/followers/contains?ids={self.userid}'
        data = json.loads(requests.get(follow_api, headers=self.req_header).content)
        return data[0]

    def new_playlist(self, playlist_name: str, description: str = '',
                     public: bool = True, collaborative: bool = False) -> SpotifyPlaylist:
        """
        Creates a new playlist owned by the user
        :param description: Description of playlist
        :param playlist_name: The name of playlist
        :param public: False if playlist should not be visible in profile
        :param collaborative: True allows other users to modify this playlist contents
        :return: SpotifyPlaylist instance
        """
        new_playlist_api: str = f'https://api.spotify.com/v1/users/{self.userid}/playlists'
        r = requests.post(
            new_playlist_api,
            headers=self.req_header_scoped('playlist-modify-public,playlist-modify-private'),
            json={
                'name': playlist_name,
                'description': description,
                'collaborative': collaborative,
                'public': public if collaborative is False else False
            }
        )
        if r.status_code != 201:
            raise RuntimeError('Error while creating playlist !')
        playlist_info = json.loads(r.content)
        playlist = SpotifyPlaylist(playlist_id=playlist_info['id'], user=self)
        playlist.set_partial_meta(
            {
                'name': playlist_info['name'],
                'description': playlist_info['description'],
                'collaborative': playlist_info.get('collaborative', False),
                'public': playlist_info.get('public', False),
                'total_tracks': int(playlist_info['tracks']['total']),
                'followers': int(playlist_info['followers']['total']),
                'url': playlist_info['external_urls']['spotify'],
                'scraped_id': playlist_info['id'],
                'thumbnail_url': '',  # Just created, so it has no thumbnail
                'snapshot_id': playlist_info['snapshot_id'],
                'owner_name': playlist_info['owner']['display_name'],
                'owner_id': playlist_info['owner']['id'],
                'owner_url': playlist_info['owner']['external_urls']['spotify'],
                '_raw_metadata': playlist_info,
            }
        )
        playlist._items_id = []
        playlist._FULL_METADATA_ACQUIRED = True  # Since we have all we need about playlist
        return playlist

    def add_to_playlist(self, playlist: SpotifyPlaylist, items: list[SpotifyTrackMedia | SpotifyEpisodeMedia],
                        position: int = 0) -> bool:
        """
        Adds SpotifyTrackMedia or SpotifyEpisodeMedia to a playlist
        :param playlist: SpotifyPlaylist instance
        :param items: List containing SpotifyTrackMedia or SpotifyEpisodeMedia
        :param position: Position at which to insert new medias
        :return: bool
        """
        if len(items) > 100:
            raise RuntimeError('Only 100 items can be added to playlist at a time !')
        body = {
            'uris': media_items_uri(items=items, action='added to'),
            'position': position
        }
        add_api = f'https://api.spotify.com/v1/playlists/{playlist.id}/tracks'
        r = requests.post(
            add_api,
            headers=self.req_header_scoped('playlist-modify-public,playlist-modify-private'),
            json=body
        )
        if r.status_code != 201:
            raise RuntimeError('Items could not be added to playlist')
        return True

    def remove_from_playlist(self, playlist: SpotifyPlaylist,
                             items: list[SpotifyTrackMedia | SpotifyEpisodeMedia]) -> bool:
        """
        Removes SpotifyTrackMedia or SpotifyEpisodeMedia from a playlist
        :param playlist: SpotifyPlaylist instance
        :param items: List containing SpotifyTrackMedia or SpotifyEpisodeMedia
        :return: bool
        """
        if len(items) > 100:
            raise RuntimeError('Only 100 items can be added to playlist at a time !')
        body = {
            'uris': media_items_uri(items=items, action='removed from'),
            'snapshot_id': playlist.meta_snapshot_id
        }
        add_api = f'https://api.spotify.com/v1/playlists/{playlist.id}/tracks'
        r = requests.delete(
            add_api,
            headers=self.req_header_scoped('playlist-modify-public,playlist-modify-private'),
            json=body
        )
        if r.status_code != 200:
            raise RuntimeError('Items could not be added to playlist')
        return True

    def get_recommendations(self,
                            limit: int = 10,
                            audio_params_like: list[SpotifyTrackMedia] | None = None,
                            user_audio_params: dict | None = None,
                            seed_artists: list[SpotifyArtist] | None = None,
                            seed_tracks: list[SpotifyTrackMedia] | None = None,
                            seed_genres: list[str] | None = None,
                            ) -> list[SpotifyTrackMedia]:
        """
        Get recommended tracks based on other tracks.
        :param user_audio_params: Audio parameters to use.
        :param limit: Number of recommended tracks to get
        :param seed_genres: Genres that will be used for seeding recommendations.
        :param seed_tracks: Tracks that will be used for seeding recommendations.
        :param audio_params_like: List of SpotifyTrackMedia used for getting audio parameters.
        :param seed_artists: Tracks that will be used for seeding recommendations.
        :return: List of SpotifyTrackMedia
        """
        recommendation_api: str = f'https://api.spotify.com/v1/recommendations?limit={limit}&'
        audio_params_api: str = 'https://api.spotify.com/v1/audio-features?ids='
        if audio_params_like is None:
            audio_params_like = []
        if len(audio_params_like) > 100:
            raise RuntimeError('Maximum of 100 tracks can be used for audio parameters')
        if user_audio_params is None:
            user_audio_params = {}
        if seed_artists is None:
            seed_artists = []
        if seed_genres is None:
            seed_genres = []
        if seed_tracks is None:
            seed_tracks = []

        # Remove duplicates
        seed_genres = list(GENRES.intersection(set(seed_genres)))
        seed_artists_ids = list(set(artist.id for artist in seed_artists))
        seed_tracks_ids = list(set(track.id for track in seed_tracks))

        total_seeds = len(seed_tracks_ids) + len(seed_artists_ids) + len(seed_genres)
        if total_seeds > 5 or total_seeds < 1:
            raise RuntimeError('Any combination of seed can only be 5 items or less! and more than 1')

        if len(seed_artists_ids) > 0:
            recommendation_api += f'seed_artists={",".join(item_id for item_id in seed_artists_ids)}&'
        if len(seed_genres) > 0:
            recommendation_api += f'seed_genres={",".join(item_id for item_id in seed_genres)}&'
        if len(seed_tracks_ids) > 0:
            recommendation_api += f'seed_tracks={",".join(item_id for item_id in seed_tracks_ids)}&'

        auto_audio_params: dict = {}
        audio_params: dict = {}
        if len(audio_params_like) > 0:
            audio_params_api += ','.join(track.id for track in audio_params_like)
            resp = requests.get(
                audio_params_api,
                headers=self.req_header
            )
            if resp.status_code == 200:
                auto_audio_params = json.loads(resp.content)['audio_params']
        valid_params_heads: list[str] = [
            'acousticness',
            'danceability',
            'duration_ms',
            'energy',
            'instrumentalness',
            'key',
            'liveness',
            'loudness',
            'mode',
            'popularity',
            'speechiness',
            'tempo',
            'time_signature',
            'valence'
        ]
        all_valids: list[str] = []
        for key in valid_params_heads:
            all_valids.append(f'min_{key}')
            all_valids.append(f'max_{key}')
            all_valids.append(f'takget_{key}')

        # Fill the auto-fetched values
        for key in auto_audio_params:
            if 'target_'+key in all_valids:
                audio_params['target_'+key] = auto_audio_params[key]
        # Override and fill user set params
        for key in user_audio_params:
            if key in all_valids:
                audio_params[key] = user_audio_params[key]
        for key in audio_params:
            recommendation_api += f'{key}={audio_params[key]}&'
        recommendation_api = recommendation_api.rstrip('&')
        req = requests.get(
            recommendation_api,
            headers=self.req_header
        )
        if req.status_code != 200:
            raise RuntimeError(f'Error with spotify API, "{recommendation_api}", response {req.status_code}: {req.text}')
        for track in json.loads(req.content)['tracks']:
            track_instance = SpotifyTrackMedia(track['id'], user=self)
            date_segments: list = track['album']['release_date'].split("-")
            track_instance.set_partial_meta(
                {
                    'artists': [
                        data['name']
                        for data in
                        track['artists']
                    ],
                    'album_name': track['album']["name"],
                    'name': track['name'],
                    'url': track['external_urls']['spotify'],
                    'artist_url': track['artists'][0]['external_urls']['spotify'],
                    'artist_id': track['artists'][0]['id'],
                    'album_url': track['album']['external_urls']['spotify'],
                    'album_id': track['album']['id'],
                    'thumbnail_url': pick_thumbnail(track['album']['images'], preferred_size=640000),
                    'release_year': int(date_segments[0] if len(date_segments) >= 1 else 0),
                    'release_month': int(date_segments[2] if len(date_segments) >= 2 else 0),
                    'release_day': int(date_segments[0] if len(date_segments) >= 3 else 0),
                    'disc_number': int(track['disc_number']),
                    'track_number': int(track['track_number']),
                    'total_tracks': int(track['album']['total_tracks']),
                    'preview_url': track['preview_url'],
                    'scraped_id': track['id'],
                    'popularity': track['popularity'],
                    'isrc': track['external_ids'].get('isrc', None),
                    'upc': track['external_ids'].get('upc', None),
                    'ean': track['external_ids'].get('ean', None),
                    'duration': track['duration_ms'],
                    'explicit': track['explicit'],
                }
            )
            yield track_instance

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
                requests.get(
                    my_library_api,
                    headers=self.req_header_scoped('playlist-read-private,playlist-read-collaborative')
                ).content
            )
            for playlist_item in my_library_info['items']:
                playlist = SpotifyPlaylist(
                    playlist_id=playlist_item['id'],
                    user=self,
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
                    user=self,  # TODO: Fix http cache

                )
                track._covers = track_item['track']['album']['images']
                date_segments: list = track_item['album']['release_date'].split("-")
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
                    'release_year': int(date_segments[0] if len(date_segments) >= 1 else 0),
                    'release_month': int(date_segments[1] if len(date_segments) >= 2 else 0),
                    'release_day': int(date_segments[2] if len(date_segments) >= 3 else 0),
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
