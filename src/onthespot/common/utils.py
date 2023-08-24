import os
import subprocess
from pathlib import Path
import requests
import json
import hashlib
import time
from ..common.formating import sanitize_string
from typing import Union

GENRES = {
    "acoustic", "afrobeat", "alt-rock", "alternative",
    "ambient", "anime", "black-metal", "bluegrass",
    "blues", "bossanova", "brazil", "breakbeat",
    "british", "cantopop", "chicago-house", "children",
    "chill", "classical", "club", "comedy",
    "country", "dance", "dancehall", "death-metal",
    "deep-house", "detroit-techno", "disco", "disney",
    "drum-and-bass", "dub", "dubstep", "edm",
    "electro", "electronic", "emo", "folk",
    "forro", "french", "funk", "garage",
    "german", "gospel", "goth", "grindcore",
    "groove", "grunge", "guitar", "happy",
    "hard-rock", "hardcore", "hardstyle", "heavy-metal",
    "hip-hop", "holidays", "honky-tonk",
    "house", "idm", "indian", "indie",
    "indie-pop", "industrial", "iranian", "j-dance",
    "j-idol", "j-pop", "j-rock", "jazz",
    "k-pop", "kids", "latin", "latino",
    "malay", "mandopop", "metal", "metal-misc",
    "metalcore", "minimal-techno", "movies", "mpb",
    "new-age", "new-release", "opera", "pagode",
    "party", "philippines-opm", "piano", "pop",
    "pop-film", "post-dubstep", "power-pop", "progressive-house",
    "psych-rock", "punk", "punk-rock", "r-n-b",
    "rainy-day", "reggae", "reggaeton", "road-trip",
    "rock", "rock-n-roll", "rockabilly",
    "romance", "sad", "salsa", "samba",
    "sertanejo", "show-tunes", "singer-songwriter",
    "ska", "sleep", "songwriter", "soul",
    "soundtracks", "spanish", "study", "summer",
    "swedish", "synth-pop", "tango", "techno",
    "trance", "trip-hop", "turkish", "work-out", "world-music"
}


def cached_request(cache_dir: Union[str, None], lifetime: int, *args, **kwargs) -> str:
    """
    Call requests.ge() while caching the text response to cache directory
    :param cache_dir:  where cache should be store, None disables the cache
    :param lifetime: Time in seconds up to which cache is valid from now, 0 sets unlimited lifetime
    :param args: Args sent to requests.get()
    :param kwargs: Extra parameters sent to requests.get()
    :return: String response
    """
    cache_file: str = ''
    if cache_dir is not None:
        kwargs_sig: str = json.dumps(kwargs).replace(
            kwargs.get('headers', {}).get('Authorization', None),
            "BEARER USER_TOKEN"
        )
        args_hash: str = hashlib.sha224(
            f'{str(args)}:{kwargs_sig}'.encode()
        ).hexdigest()
        print(
            'Cache HASH : ',
            args_hash,
            '\t',
            f'{str(args)}:{kwargs_sig}'
        )
        cache_dir = os.path.join(os.path.abspath(cache_dir), 'api_cache')
        os.makedirs(cache_dir, exist_ok=True)
        cache_file: str = os.path.abspath(os.path.join(cache_dir, f'{args_hash}.acache'))
        if os.path.isfile(cache_file):
            # Cache exists for the request
            with open(cache_file, 'r', encoding='utf-8') as cache:
                lines: list = cache.readlines()
                if int(lines[0]) == 0 or int(lines[0]) < int(time.time()):
                    # Cache is valid
                    data = '\n'.join(line for line in lines[1:])
                    return data.strip()
        # The cache has expired or does not exist
    request = requests.get(*args, **kwargs)
    if (200 <= request.status_code <= 299) and cache_dir is not None:
        # Request was successful, cache the response
        with open(cache_file, 'w', encoding='utf-8') as cache:
            cache.write(str(int(time.time()) + lifetime) + '\n' + request.text.strip())
    return request.text


def convert_from_ogg(ffmpeg_path: str, source_media: str, bitrate: int,
                     extra_params: Union[list, None] = None) -> os.PathLike:
    """
    Converts spotify ogg vorbis streams to another format via ffmpeg, Note: source media should use the target file
    extension, the source media is assumed ogg vorbis regardless of the source media extension
    :param ffmpeg_path: Path to ffmpeg binary
    :param source_media: Path of media to convert
    :param bitrate: Target bitrate of converted media
    :param extra_params: List of extra parameters passed to ffmpeg
    :return: Absolute path to converted media ( Same as source_media, but now it's converted )
    """
    if extra_params is None:
        extra_params: list = []
    if os.path.isfile(os.path.abspath(source_media)):
        target_path: Path = Path(source_media)
        temp_name: str = os.path.join(target_path.parent, ".~" + target_path.stem + ".ogg")
        if os.path.isfile(temp_name):
            os.remove(temp_name)
        os.rename(source_media, temp_name)
        # Prepare default parameters
        command: list = [
            ffmpeg_path,
            '-i', sanitize_string(
                temp_name,
                skip_path_seps=True,
                escape_quotes=False
            )
        ]
        # If the media format is set to ogg, just correct the downloaded file
        # and add tags
        if target_path.suffix == '.ogg':
            command = command + ['-c', 'copy']
        else:
            command = command + ['-ar', '44100', '-ac', '2', '-b:a', f'{bitrate}k']
        if int(os.environ.get('SHOW_FFMPEG_OUTPUT', 0)) == 0:
            command = command + \
                      ['-loglevel', 'error', '-hide_banner', '-nostats']
        # Add user defined parameters
        for param in extra_params:
            command.append(param)
        # Add output parameter at last
        command.append(
            sanitize_string(
                source_media,
                skip_path_seps=True,
                escape_quotes=False
            )
        )
        subprocess.check_call(command, shell=False)
        os.remove(temp_name)
        return target_path
    else:
        raise FileNotFoundError


def pick_thumbnail(covers: list[dict], preferred_size: int = 640000) -> str:
    """
    Returns url for the artwork from available artworks
    :param covers: list of dict containing artwork/thumbnail info
    :param preferred_size: Size of media (width*height) which will be returned or next available better one
    :return: Url of the cover art for media
    """
    images = {}
    for image in covers:
        try:
            images[image['height'] * image['width']] = image['url']
        except TypeError:
            images[0] = image['url']
            pass
    available_sizes = sorted(images)
    for size in available_sizes:
        if size >= preferred_size:
            return images[size]
    return images[available_sizes[-1]] if len(available_sizes) > 0 else ""


class MutableBool:
    def __init__(self, value: bool = False):
        self.__value = None
        self.set(bool(value))

    def set(self, value: bool):
        self.__value = bool(value)

    def __bool__(self):
        return self.__value

    def __int__(self):
        return 1 if self.__value else 0
