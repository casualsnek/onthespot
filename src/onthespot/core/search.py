import requests
from ..common.utils import pick_thumbnail
from ..core.mediaitem import *
from ..core.user import SpotifyUser


class SearchResult:
    def __init__(self, search_api_response: dict, user: SpotifyUser, media_instance_params: dict | None = None) -> None:
        """
        Initialises SearchResult class from a search api response.
        :param search_api_response: The Response from search api.
        """
        self.api_resp: dict = search_api_response
        self.__user: SpotifyUser = user
        self.__map: dict = media_instance_params
        pass

    @staticmethod
    def from_term(term: str, user: SpotifyUser, max_results: int = 10, playlists: bool = False, tracks: bool = True,
                  albums: bool = False, artists: bool = False, podcasts: bool = False,
                  episodes: bool = False, media_instance_params: dict | None = None) -> 'SearchResult':
        if media_instance_params is None:
            media_instance_params = {}
        t: str = ''
        if not (playlists or tracks or albums or artists or podcasts or episodes):
            raise RuntimeError('At least one media type should be selected for search')
        if playlists:
            t += 'playlist,'
        if tracks:
            t += 'track,'
        if albums:
            t += 'album,'
        if artists:
            t += 'artist,'
        if podcasts:
            t += 'show,'
        if episodes:
            t += 'episode,'
        t = t.rstrip(',')
        search_api: str = f'https://api.spotify.com/v1/search?q={term}&type={t}&limit={max_results}'
        r = requests.get(
            search_api,
            headers=user.req_header
        )
        if r.status_code != 200:
            raise RuntimeError(f'Search could not be performed due to {r.status_code} error from spotify !')
        return SearchResult(
            search_api_response=json.loads(r.content),
            user=user,
            media_instance_params=media_instance_params
        )

    @property
    def artists(self) -> list[SpotifyArtist]:
        """
        Returns generator for artists in the search result
        :return:
        """
        artists_list: list[dict] = []
        if 'artists' in self.api_resp:
            artists_list = self.api_resp['artists']['items']
        for artist in artists_list:
            artist_instance: SpotifyArtist = SpotifyArtist(artist['id'], user=self.__user, **self.__map)
            artist_instance.set_partial_meta(
                {
                    'name': artist['name'],
                    'popularity': int(artist['popularity']),
                    'followers': int(artist['followers']['total']),
                    'url': artist['external_urls']['spotify'],
                    'scraped_id': artist['id'],
                    'genres': artist['genres'],
                    'thumbnail_url': pick_thumbnail(artist['images'], preferred_size=640000),
                }
            )
            yield artist_instance

    @property
    def playlists(self) -> list[SpotifyPlaylist]:
        """
        Returns generator for playlists in the search result
        :return:
        """
        playlist_list: list[dict] = []
        if 'playlists' in self.api_resp:
            playlist_list = self.api_resp['playlists']['items']
        for playlist in playlist_list:
            playlist_instance: SpotifyPlaylist = SpotifyPlaylist(playlist['id'], user=self.__user, **self.__map)
            playlist_instance.set_partial_meta(
                {
                    'name': playlist['name'],
                    'description': playlist['description'],
                    'collaborative': playlist.get('collaborative', False),
                    'public': playlist.get('public', False),
                    'total_tracks': int(playlist['tracks'].get('total', 0)),
                    'url': playlist['external_urls']['spotify'],
                    'scraped_id': playlist['id'],
                    'thumbnail_url': pick_thumbnail(playlist['images'], preferred_size=640000),
                    'snapshot_id': playlist.get('snapshot_id', None),
                    'owner_name': playlist['owner']['display_name'],
                    'owner_id': playlist['owner']['id'],
                    'owner_url': playlist['owner']['external_urls']['spotify'],
                }
            )
            yield playlist_instance

    @property
    def albums(self) -> list[SpotifyAlbum]:
        """
        Returns generator for albums in the search result
        :return: Generator[SpotifyAlbum]
        """
        album_list: list[dict] = []
        if 'albums' in self.api_resp:
            album_list = self.api_resp['albums']['items']
        for album in album_list:
            album_instance: SpotifyAlbum = SpotifyAlbum(album['id'], user=self.__user, **self.__map)
            date_segments: list = album['release_date'].split("-")
            album_instance.set_partial_meta(
                {
                    'name': album['name'],
                    'total_tracks': int(album['total_tracks']),
                    'url': album['external_urls']['spotify'],
                    'scraped_id': album['id'],
                    'release_year': int(date_segments[0] if len(date_segments) >= 1 else 0),
                    'release_month': int(date_segments[1] if len(date_segments) >= 2 else 0),
                    'release_day': int(date_segments[2] if len(date_segments) >= 3 else 0),
                    'thumbnail_url': pick_thumbnail(album['images'], preferred_size=640000),
                    'artists_id': [artist['id'] for artist in album['artists'] if artist['type'] == 'artist'],
                }
            )
            yield album_instance

    @property
    def tracks(self) -> list[SpotifyTrackMedia]:
        """
        Returns generator for tracks in the search result
        :return: Generator[SpotifyTrackMedia]
        """
        track_list: list[dict] = []
        if 'tracks' in self.api_resp:
            track_list = self.api_resp['tracks']['items']
        for track in track_list:
            track_instance: SpotifyTrackMedia = SpotifyTrackMedia(track['id'], user=self.__user, **self.__map)
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
                    'release_month': int(date_segments[1] if len(date_segments) >= 2 else 0),
                    'release_day': int(date_segments[2] if len(date_segments) >= 3 else 0),
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
    def podcasts(self) -> list[SpotifyPodcast]:
        """
        Returns generator for podcasts in the search result
        :return: Generator[SpotifyPodcast]
        """
        podcast_list: list[dict] = []
        if 'shows' in self.api_resp:
            podcast_list = self.api_resp['shows']['items']
        for podcast in podcast_list:
            podcast_instance: SpotifyPodcast = SpotifyPodcast(podcast['id'], user=self.__user, **self.__map)
            podcast_instance.set_partial_meta(
                {
                    'name': podcast['name'],
                    'publisher': podcast['publisher'],
                    'description': podcast['description'],
                    'scraped_id': podcast['id'],
                    'url': podcast['external_urls']['spotify'],
                    'thumbnail_url': pick_thumbnail(podcast['images'], preferred_size=640000),
                    'explicit': bool(podcast['explicit']),
                    'total_episodes': int(podcast['total_episodes']),
                }
            )
            yield podcast_instance

    @property
    def episodes(self) -> list[SpotifyEpisodeMedia]:
        """
        Returns generator for episodes in the search result
        :return: Generator[SpotifyEpisodeMedia]
        """
        episode_list: list[dict] = []
        if 'shows' in self.api_resp:
            episode_list = self.api_resp['shows']['items']
        for episode in episode_list:
            episode_instance: SpotifyEpisodeMedia = SpotifyEpisodeMedia(episode['id'], user=self.__user, **self.__map)
            episode_instance.set_partial_meta(
                {
                    'name': episode['name'],
                    'url': episode['external_urls']['spotify'],
                    'thumbnail_url': pick_thumbnail(episode['images'], preferred_size=640000),
                    'description': episode['description'],
                    'language': episode['language'],
                    'languages': [lang for lang in episode['language']],
                    'release_year': int(episode['release_date'][0]),
                    'release_month': int(episode['release_date'][1]),
                    'release_day': int(episode['release_date'][2]),
                    'is_playable': episode['is_playable'],
                    'explicit': episode['explicit'],
                    'scraped_id': episode['id'],
                    'duration': episode['duration_ms']
                }
            )
            yield episode_instance
