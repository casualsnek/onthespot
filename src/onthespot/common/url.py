import re
from typing import Tuple
from ..core.mediaitem import *
from ..expections import UnknownURLTypeException

URL_TYPES: dict = {
    'TRACK':    [
        [
            '^https://.*.spotify.com/.*(track)/([^\\?]*).*$',
            '^spotify:(track):([^\\?]*).*$'
        ],
        0, SpotifyTrackMedia
    ],
    'PLAYLIST': [
        [
            '^https://.*.spotify.com/.*(playlist)/([^\\?]*).*$',
            '^spotify:(playlist):([^\\?]*).*$'
        ],
        1, SpotifyPlaylist
    ],
    'ALBUM':    [
        [
            '^https://.*.spotify.com/.*(album)/([^\\?]*).*$',
            '^spotify:(album):([^\\?]*).*$'
        ],
        2, SpotifyAlbum
    ],
    'ARTIST':   [
        [
            '^https://.*.spotify.com/.*(artist)/([^\\?]*).*$',
            '^spotify:(artist):([^\\?]*).*$'
        ],
        3, SpotifyArtist
    ],
    'PODCAST':  [
        [
            '^https://.*.spotify.com/.*(show)/([^\\?]*).*$',
            '^spotify:(show):([^\\?]*).*$'
        ],
        4, SpotifyPodcast
    ],
    'EPISODE':  [
        [
            '^https://.*.spotify.com/.*(episode)/([^\\?]*).*$',
            '^spotify:(episode):([^\\?]*).*$'
        ],
        5, SpotifyEpisodeMedia
    ],
}


def classify(url, return_media_obj=False, **kwargs) -> \
        Tuple[int, str, Union[None, AbstractMediaItem, AbstractMediaCollection]]:
    """
    Classify url into their media type, and return a respective media object if necessary
    :param url: Url to classify
    :param return_media_obj: True if a media object is needed
    Keyword Args:
        session (Session): librespot session to use
        http_cache (str): Directory to use it for http cache
    :return: (MEDIA_TYPE, MEDIA_OBJ)
    """
    for url_type in URL_TYPES:
        for pattern in URL_TYPES[url_type][0]:
            match = re.match(pattern, url)
            if match:
                return (
                    URL_TYPES[url_type][1],  # Int indicating the type of media
                    match.group(2),  # ID of the media
                    URL_TYPES[url_type][2](match.group(2), **kwargs) if
                    return_media_obj
                    else None  # Media object if required
                )
    raise UnknownURLTypeException(f'The media type for url "{url}" could not be determined !')
