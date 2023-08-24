import json
import os.path
from typing import Union, TYPE_CHECKING
from ..common.formating import metadata_list_to_string
from ..common.utils import cached_request
from ..core.__base__ import AbstractMediaItem, AbstractMediaCollection
from ..expections import LyricsUnavailableException
import subprocess

if TYPE_CHECKING:
    from ..core.user import SpotifyUser


class SpotifyTrackMedia(AbstractMediaItem):
    def __init__(self, track_id: str, user: 'SpotifyUser', http_cache: Union[str, None] = None) -> None:
        """
        Initialises the spotify track class instance
        :param track_id: Track id
        :param user: SpotifyUser to use
        :param http_cache: Path to directory where http request to spotify are cached
        """
        self.http_cache = os.path.abspath(http_cache) if http_cache is not None else None
        self.set_user(user)
        super().__init__(media_id=track_id, media_type=0)

    def _fetch_metadata(self) -> None:
        """
        Private function: Fetches metadata for the current track
        :return: None
        """
        track_api: str = f'https://api.spotify.com/v1/tracks?ids={self.id}&market=from_token'
        credits_api: str = f'https://spclient.wg.spotify.com/track-credits-view/v0/experimental/{self.id}/credits'

        track_info: dict = json.loads(cached_request(self.http_cache, 0, track_api, headers=self.req_header))
        credits_info: dict = json.loads(cached_request(self.http_cache, 0, credits_api, headers=self.req_header))
        track_credits: dict = {}
        for credit_block in credits_info['roleCredits']:
            try:
                track_credits[credit_block['roleTitle'].lower()] = [
                    artist['name']
                    for artist
                    in
                    credit_block['artists']
                ]
            except KeyError:
                pass
        track_credits['source'] = credits_info.get('sourceNames', [])
        album_info: dict = json.loads(
            cached_request(self.http_cache, 0, track_info['tracks'][0]['album']['href'] + '?market=from_token',
                           headers=self.req_header)
        )
        artist_info: dict = json.loads(
            cached_request(self.http_cache, 0, track_info['tracks'][0]['artists'][0]['href'] + '?market=from_token',
                           headers=self.req_header)
        )
        date_segments: list = track_info['tracks'][0]['album']['release_date'].split("-")
        self._covers = track_info['tracks'][0]['album']['images']
        self._metadata = {
            'artists': [
                data['name']
                for data in
                track_info['tracks'][0]['artists']
            ],
            'album_name': track_info['tracks'][0]['album']["name"],
            'name': track_info['tracks'][0]['name'],
            'url': track_info['tracks'][0]['external_urls']['spotify'],
            'artist_url': track_info['tracks'][0]['artists'][0]['external_urls']['spotify'],
            'artist_id': track_info['tracks'][0]['artists'][0]['id'],
            'album_url': track_info['tracks'][0]['album']['external_urls']['spotify'],
            'album_id': track_info['tracks'][0]['album']['id'],
            'thumbnail_url': self.get_thumbnail_url(preferred_size=640000),
            'release_year': int(date_segments[0] if len(date_segments) >= 1 else 0),
            'release_month': int(date_segments[1] if len(date_segments) >= 2 else 0),
            'release_day': int(date_segments[2] if len(date_segments) >= 3 else 0),
            'disc_number': int(track_info['tracks'][0]['disc_number']),
            'track_number': int(track_info['tracks'][0]['track_number']),
            'total_tracks': int(track_info['tracks'][0]['album']['total_tracks']),
            'preview_url': track_info['tracks'][0]['preview_url'],
            'total_discs': int(sorted(
                [
                    trk['disc_number']
                    for trk in
                    album_info['tracks']['items']
                ]
            )[-1]) if 'tracks' in album_info else 1,
            'scraped_id': track_info['tracks'][0]['id'],
            'is_playable': track_info['tracks'][0]['is_playable'],
            'popularity': track_info['tracks'][0]['popularity'],
            'isrc': track_info['tracks'][0]['external_ids'].get('isrc', None),
            'upc': track_info['tracks'][0]['external_ids'].get('upc', None),
            'ean': track_info['tracks'][0]['external_ids'].get('ean', None),
            'genre': artist_info['genres'],
            'duration': track_info['tracks'][0]['duration_ms'],
            'credits': track_credits,
            # https://developer.spotify.com/documentation/web-api/reference/get-track
            # List of genre is supposed to be here, genre from album API is deprecated, and
            # it always seems to be unavailable
            # to Use artist endpoint to get artist's genre instead
            'label': album_info['label'],
            'copyrights': [
                holder['text']
                for holder
                in album_info['copyrights']
            ],
            'explicit': track_info['tracks'][0]['explicit'],
            '_raw_meta': track_info
        }
        self._FULL_METADATA_ACQUIRED = True

    @property
    def artist(self) -> 'SpotifyArtist':
        """
        Returns SpotifyArtist instance of the track's lead artist
        :return: SpotifyArtist Instance
        """
        return SpotifyArtist(artist_id=self.meta_artist_id, user=self._user)

    @property
    def album(self) -> 'SpotifyAlbum':
        """
        Returns SpotifyAlbum instance of the album the current track is in
        :return: SpotifyAlbum Instance
        """
        return SpotifyAlbum(album_id=self.meta_album_id, user=self._user)

    @property
    def lyrics(self) -> tuple[bool, list[str]]:
        """
        Returns synced or un synced lyrics for the track
        :return: (bool: is_synced_lyrics, list[str]: lyrics_lines
        """
        is_synced: bool = False
        lyrics: list = []
        try:
            lyrics_api = f'https://spclient.wg.spotify.com/lyrics/v1/track/{self.id}?format=json&market=from_token'
            lyrics_req = json.loads(cached_request(self.http_cache, 0, lyrics_api, headers=self.req_header))
            artist = metadata_list_to_string(self.meta_artists)
            track_title = self.meta_name
            album = self.meta_album_name
            l_ms = self.meta_duration
            if lyrics_req.status_code == 200:
                digit: str = '0' if round((l_ms / 1000) / 60) < 10 else ''
                m: int = round((l_ms / 1000) / 60)
                s: int = round((l_ms / 1000) % 60)
                lyrics_json = lyrics_req.json()
                lyrics.append(f'[ti:{track_title}]')
                # TODO: Add song writers from credit
                lyrics.append(f'[au:---]')
                lyrics.append(f'[ar:{artist}]')
                lyrics.append(f'[al:{album}]')
                lyrics.append(f'[by:{lyrics_json["provider"]}]')
                # TODO: Add application version
                lyrics.append(f'[ve:---]')
                lyrics.append('[re:casualsnek-onTheSpot]')
                lyrics.append(f'[length:{digit}{m}:{s}]\n')

                if lyrics_json['kind'].lower() == 'text':
                    lyrics = [
                        line['words'][0]['string']
                        for line in
                        lyrics_json['lines']
                    ]
                elif lyrics_json['kind'].lower() == 'line':
                    for line in lyrics_json['lines']:
                        minutes, seconds = divmod(line['time'] / 1000, 60)
                        lyrics.append(
                            f'[{minutes:0>2.0f}:{seconds:05.2f}] '
                            f'{line["words"][0]["string"]}'
                        )
                    is_synced = True
            else:
                raise LyricsUnavailableException(
                    f'No lyrics available for track - {self.id}'
                )
        except (KeyError, IndexError):
            raise LyricsUnavailableException(
                f'No lyrics available for track - {self.id}'
            )
        return is_synced, lyrics


class SpotifyEpisodeMedia(AbstractMediaItem):

    def __init__(self, episode_id: str, user: 'SpotifyUser', http_cache: Union[str, None] = None) -> None:
        """
        Initialises the spotify podcast episode class instance
        :param episode_id: Episode id
        :param user:  SpotifyUser to use
        :param http_cache: Path to directory where http request to spotify are cached
        """
        self.http_cache = os.path.abspath(http_cache) if http_cache is not None else None
        self.set_user(user)
        super().__init__(media_id=episode_id, media_type=1)

    def _fetch_metadata(self) -> None:
        """
        Private function: Fetches metadata for the current episode
        :return: None
        """
        episode_api: str = f'https://api.spotify.com/v1/tracks?ids={self.id}&market=from_token'
        episode_info: dict = json.loads(cached_request(self.http_cache, 0, episode_api, headers=self.req_header))
        self._covers = episode_info['tracks'][0]['album']['images']
        self._metadata = {
            'name': episode_info['name'],
            'podcast_name': episode_info['show']['name'],
            'url': episode_info['external_urls']['spotify'],
            'podcast_url': episode_info['show']['external_urls']['spotify'],
            'thumbnail_url': self.get_thumbnail_url(preferred_size=640000),
            'podcast_id': episode_info['show']['id'],
            'description': episode_info['description'],
            'podcast_description': episode_info['show']['description'],
            'language': episode_info['language'],
            'languages': [lang for lang in episode_info['language']],
            'release_year': int(episode_info['release_date'][0]),
            'release_month': int(episode_info['release_date'][1]),
            'release_day': int(episode_info['release_date'][2]),
            'is_playable': episode_info['is_playable'],
            'explicit': episode_info['explicit'],
            'scraped_id': episode_info['id'],
            'publisher': episode_info['show']['publisher'],
            'copyrights': [
                holder['text']
                for holder
                in episode_info['show']['copyrights']
            ],
            '_raw_meta': episode_info
        }
        self._FULL_METADATA_ACQUIRED = True

    # TODO: Add Podcast and show properties as well
    @property
    def podcast(self) -> 'SpotifyPodcast':
        """
        Returns SpotifyPodcast instance of the podcast the current episode is in
        :return: SpotifyPodcast Instance
        """
        return SpotifyPodcast(podcast_id=self.meta_podcast_id, user=self._user)

    @property
    def show(self) -> 'SpotifyPodcast':
        """
        Returns SpotifyPodcast instance of the podcast the current episode is in
        :return: SpotifyPodcast Instance
        """
        return self.podcast


class SpotifyAlbum(AbstractMediaCollection):
    _items_id: Union[list[str], None] = None
    _collection_class: SpotifyTrackMedia = SpotifyTrackMedia

    def __init__(self, album_id: str, user: 'SpotifyUser', http_cache: Union[str, None] = None) -> None:
        """
        Initializes instance of SpotifyAlbum class representing a spotify album
        :param album_id: Spotify ID of the Album
        :param user: SpotifyUser to use
        :param http_cache: Path to directory where http request to spotify are cached
        :return: None
        """
        self.http_cache = os.path.abspath(http_cache) if http_cache is not None else None
        self.set_user(user)
        super().__init__(collection_id=album_id)

    def _fetch_metadata(self) -> None:
        """
        Private function: Fetches metadata for the current album
        :return: None
        """
        album_api: str = f'https://api.spotify.com/v1/albums/{self.id}?market=from_token'
        album_info: dict = json.loads(cached_request(self.http_cache, 0, album_api, headers=self.req_header))
        self._covers = album_info['images']
        date_segments: list = album_info['release_date'].split("-")
        self._metadata = {
            'name': album_info['name'],
            'total_tracks': int(album_info['total_tracks']),
            'url': album_info['external_urls']['spotify'],
            'scraped_id': album_info['id'],
            'release_year': int(date_segments[0] if len(date_segments) >= 1 else 0),
            'release_month': int(date_segments[1] if len(date_segments) >= 2 else 0),
            'release_day': int(date_segments[2] if len(date_segments) >= 3 else 0),
            'thumbnail_url': self.get_thumbnail_url(preferred_size=640000),
            '_raw_metadata': album_info,
            'label': album_info['label'],
            'isrc': album_info['external_ids'].get('isrc', None),
            'upc': album_info['external_ids'].get('isrc', None),
            'ean': album_info['external_ids'].get('isrc', None),
            'popularity': int(album_info['popularity']),
            'artists_id': [artist['id'] for artist in album_info['artists'] if artist['type'] == 'artist'],
            'copyrights': [
                holder['text']
                for holder
                in album_info['copyrights']
            ],
        }
        self._items_id: list[str] = []
        while True:
            for track in album_info['tracks']['items']:
                # TODO: Maybe add support for loading partial metadata from this API to reduce calls
                self._items_id.append(track['id'])
            if album_info['tracks']['next']:
                album_info: dict = json.loads(
                    cached_request(self.http_cache, 0, album_info['tracks']['next'], headers=self.req_header)
                )
            else:
                break
        self._FULL_METADATA_ACQUIRED = True

    @property
    def tracks(self) -> list[SpotifyTrackMedia]:
        """
        Returns list containing SpotifyTrackMedia instance of tracks within this album
        :return: list[SpotifyTrackMedia]
        """
        return self.items

    @property
    def artist(self) -> 'SpotifyArtist':
        """
        Returns SpotifyArtist instance of the lead artist this album is from
        :return:
        """
        return SpotifyArtist(artist_id=self.meta_artists_id[0], user=self._user)

    @property
    def artists(self) -> list['SpotifyArtist']:
        """
        Returns SpotifyArtist instance of all the artists involved with this album
        :return:
        """
        return [
            SpotifyArtist(artist_id=artist_id, user=self._user)
            for artist_id in
            self.meta_artists_id
        ]


class SpotifyArtist(AbstractMediaCollection):
    _items_id: Union[list[str], None] = None
    _collection_class: SpotifyAlbum = SpotifyAlbum

    def __init__(self, artist_id: str, user: 'SpotifyUser', http_cache: Union[str, None] = None) -> None:
        """
        Initializes instance of SpotifyArtist class representing a spotify artist
        :param artist_id: Spotify ID of the Artist
        :param user: SpotifyUser to use
        :param http_cache: Path to directory where http request to spotify are cached
        :return: None
        """
        self.http_cache = os.path.abspath(http_cache) if http_cache is not None else None
        self.set_user(user)
        super().__init__(collection_id=artist_id)

    def _fetch_metadata(self) -> None:
        """
        Private function: Fetches metadata for the current artist
        :return: None
        """
        artist_api: str = f'https://api.spotify.com/v1/artists/{self.id}?market=from_token'
        artist_info: dict = json.loads(cached_request(self.http_cache, 0, artist_api, headers=self.req_header))
        self._covers = artist_info['images']
        self._metadata = {
            'name': artist_info['name'],
            'popularity': int(artist_info['popularity']),
            'followers': int(artist_info['followers']['total']),
            'url': artist_info['external_urls']['spotify'],
            'scraped_id': artist_info['id'],
            'genres': artist_info['genres'],
            'thumbnail_url': self.get_thumbnail_url(preferred_size=640000),
            '_raw_metadata': artist_info,
        }
        self._items_id: list[str] = []
        artist_album_api: str = f'https://api.spotify.com/v1/artists/{self.id}/albums?' \
                                f'include_groups=album,single&market=from_token&limit=20&offset=0'
        while True:
            artist_album_info: dict = json.loads(
                cached_request(self.http_cache, 0, artist_album_api, headers=self.req_header))
            for album in artist_album_info['items']:
                self._items_id.append(album['id'])
            if artist_album_info['next']:
                artist_album_api = artist_album_info['next']
            else:
                break
        self._FULL_METADATA_ACQUIRED = True

    @property
    def albums(self) -> list[SpotifyAlbum]:
        """
        Returns list containing SpotifyAlbum instance of albums by this artist
        :return: list[SpotifyAlbum]
        """
        return self.items


class SpotifyPlaylist(AbstractMediaCollection):
    _items_id: Union[list[str], None] = None
    _collection_class: SpotifyTrackMedia = SpotifyTrackMedia

    def __init__(self, playlist_id: str, user: 'SpotifyUser', http_cache: Union[str, None] = None) -> None:
        """
        Initializes instance of SpotifyPlaylist class representing a spotify playlist
        :param playlist_id: Spotify ID of the Playlist
        :param user: SpotifyUser to use
        :param http_cache: Path to directory where http request to spotify are cached
        :return: None
        """
        self.http_cache = os.path.abspath(http_cache) if http_cache is not None else None
        self.set_user(user)
        super().__init__(collection_id=playlist_id)

    def _fetch_metadata(self) -> None:
        """
        Private function: Fetches metadata for the current playlist
        :return: None
        """
        fields = "name,description,followers,images,id,external_urls," \
                 "name,owner(id,display_name,external_urls),tracks.items(track(id)),tracks.next"
        playlist_api: str = f'https://api.spotify.com/v1/playlists/{self.id}?fields={fields}&market=from_token'
        playlist_info: dict = json.loads(cached_request(self.http_cache, 0, playlist_api, headers=self.req_header))
        self._covers = playlist_info['images']
        self._metadata = {
            'name': playlist_info['name'],
            'description': playlist_info['description'],
            'collaborative': playlist_info.get('collaborative', False),
            'public': playlist_info.get('public', False),
            'total_tracks': int(playlist_info['tracks'].get('total', 0)),
            'followers': int(playlist_info['followers']['total']),
            'url': playlist_info['external_urls']['spotify'],
            'scraped_id': playlist_info['id'],
            'thumbnail_url': self.get_thumbnail_url(preferred_size=640000),
            'snapshot_id': playlist_info.get('snapshot_id', None),
            'owner_name': playlist_info['owner']['display_name'],
            'owner_id': playlist_info['owner']['id'],
            'owner_url': playlist_info['owner']['external_urls']['spotify'],
            '_raw_metadata': playlist_info,
        }
        self._items_id: list[str] = []
        while True:
            for item in playlist_info['tracks']['items']:
                self._items_id.append(item['track']['id'])
            if playlist_info['tracks']['next']:
                playlist_info = json.loads(
                    cached_request(self.http_cache, 0, playlist_info['tracks']['next'], headers=self.req_header)
                )
            else:
                break
        self._FULL_METADATA_ACQUIRED = True

    @property
    def tracks(self) -> list[SpotifyTrackMedia]:
        """
        Returns list containing SpotifyTrackMedia instance of the tracks in this playlist
        :return: list[SpotifyAlbum]
        """
        return self.items

    @property
    def is_collaborative(self) -> bool:
        """
        Returns if the playlist is collaborative
        :return: bool
        """
        return self._metadata['collaborative']

    @property
    def is_public(self) -> bool:
        """
        Returns if the playlist is public
        :return: bool
        """
        return self._metadata['public']


class SpotifyPodcast(AbstractMediaCollection):
    _items_id: Union[list[str], None] = None
    _collection_class: SpotifyEpisodeMedia = SpotifyEpisodeMedia

    def __init__(self, podcast_id: str, user: 'SpotifyUser', http_cache: Union[str, None] = None) -> None:
        """
        Initializes instance of SpotifyPodcast class representing a spotify podcast
        :param podcast_id: Spotify ID of the Podcast
        :param user: SpotifyUser to use
        :param http_cache: Path to directory where http request to spotify are cached
        :return: None
        """
        self.http_cache = os.path.abspath(http_cache) if http_cache is not None else None
        self.set_user(user)
        super().__init__(collection_id=podcast_id)

    def _fetch_metadata(self) -> None:
        """
        Private function: Fetches metadata for the current podcast
        :return: None
        """
        podcast_api: str = f'https://api.spotify.com/v1/shows/{self.id}?market=from_token'
        podcast_info: dict = json.loads(cached_request(self.http_cache, 0, podcast_api, headers=self.req_header))
        self._covers = podcast_info['images']
        self._metadata = {
            'name': podcast_info['name'],
            'publisher': podcast_info['publisher'],
            'description': podcast_info['description'],
            'scraped_id': podcast_info['id'],
            'url': podcast_info['external_urls']['spotify'],
            'thumbnail_url': self.get_thumbnail_url(preferred_size=640000),
            'explicit': bool(podcast_info['explicit']),
            'copyrights': [
                holder['text']
                for holder
                in podcast_info['copyrights']
            ],
            'total_episodes': int(podcast_info['total_episodes']),
            '_raw_metadata': podcast_info,
        }
        self._items_id: list[str] = []
        while True:
            for item in podcast_info['episodes']['items']:
                self._items_id.append(item['id'])
            if podcast_info['episodes']['next']:
                podcast_info = json.loads(
                    cached_request(self.http_cache, 0, podcast_info['episodes']['next'], headers=self.req_header)
                )
            else:
                break
        self._FULL_METADATA_ACQUIRED = True

    @property
    def episodes(self) -> list[SpotifyEpisodeMedia]:
        """
        Returns list containing SpotifyEpisodeMedia instance of the episodes in this show/podcast
        :return: list[SpotifyEpisodeMedia]
        """
        return self.items
