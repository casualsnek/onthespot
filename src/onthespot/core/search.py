import json
import requests
from ..core.mediaitem import SpotifyPlaylist, SpotifyArtist, SpotifyAlbum, SpotifyTrackMedia
from ..core.user import SpotifyUser


class SearchResult:
    def __init__(self, search_api_response: dict) -> None:
        """
        Initialises SearchResult class from a search api response.
        :param search_api_response: The Response from search api.
        """
        pass

    @staticmethod
    def from_term(term: str, user: SpotifyUser, max_results: int = 10, playlist: bool = True, tracks: bool = True,
                  album: bool = True, artist=True) -> 'SearchResult':
        search_api: str = ''
        r = requests.get(search_api)
        if r.status_code != 200:
            raise RuntimeError(f'Search could not be performed due to {r.status_code} error from spotify !')
        return SearchResult(search_api_response=json.loads(r.content))

    @property
    def artists(self) -> list[SpotifyArtist]:
        """
        Returns generator for artists in the search result
        :return:
        """
        return []

    @property
    def playlists(self) -> list[SpotifyPlaylist]:
        """
        Returns generator for playlists in the search result
        :return:
        """
        return []

    @property
    def albums(self) -> list[SpotifyAlbum]:
        """
        Returns generator for albums in the search result
        :return:
        """
        return []

    @property
    def tracks(self) -> list[SpotifyTrackMedia]:
        """
        Returns generator for tracks in the search result
        :return:
        """
        return []
