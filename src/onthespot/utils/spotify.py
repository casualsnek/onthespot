import string
import subprocess
from ..exceptions import *
import requests.adapters
from ..otsconfig import config
import requests
import json
import music_tag
import os
from pathlib import Path
import re
from PIL import Image
from io import BytesIO
from hashlib import md5
from ..runtimedata import get_logger
from librespot.audio.decoders import AudioQuality

logger = get_logger("spotutils")
requests.adapters.DEFAULT_RETRIES = 10

def get_artist_albums(session, artist_id):
    logger.info(f"Get albums for artist by id '{artist_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/artists/{artist_id}/albums', token=access_token)
    return [resp['items'][i]['id'] for i in range(len(resp['items']))]


def get_playlist_data(session, playlist_id):
    logger.info(f"Get playlist dump for '{playlist_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/playlists/{playlist_id}', token=access_token)
    return sanitize_data(resp['name']), sanitize_data(resp['owner']['display_name']), sanitize_data(resp['description']), resp['external_urls']['spotify']


def get_track_lyrics(session, track_id, metadata, forced_synced):
    lyrics = []
    try:
        params = 'format=json&market=from_token'
        access_token = session.tokens().get("user-read-email")
        headers = {'Authorization': f'Bearer {access_token}'}
        lyrics_json_req = requests.get(
            f'https://spclient.wg.spotify.com/lyrics/v1/track/{track_id}',
            params=params,
            headers=headers
        )

        for key in metadata.keys():
            value = metadata[key]
            if key == 'artists':
                artist = conv_artist_format(value)
            elif key in ['name', 'track_title', 'tracktitle']:
                tracktitle = value
            elif key in ['album_name', 'album']:
                album = value
        l_ms = metadata['duration']
        if lyrics_json_req.status_code == 200:
            lyrics_json = lyrics_json_req.json()
            lyrics.append(f'[ti:{tracktitle}]')
            lyrics.append(f'[au:{";".join(writer for writer in metadata["credits"].get("writers", []))}]')
            lyrics.append(f'[ar:{artist}]')
            lyrics.append(f'[al:{album}]')
            lyrics.append(f'[by:{lyrics_json["provider"]}]')
            lyrics.append(f'[ve:{config.version}]')
            lyrics.append(f'[length: {round((l_ms/1000)/60)}:{round((l_ms/1000)%60)}]')
            lyrics.append('[re:casualsnek-onTheSpot]')
            if lyrics_json['kind'].lower() == 'text':
                # It's un synced lyrics, if not forcing synced lyrics return it
                if not forced_synced:
                    lyrics = [line['words'][0]['string'] for line in lyrics_json['lines']]
            elif lyrics_json['kind'].lower() == 'line':
                for line in lyrics_json['lines']:
                    minutes, seconds = divmod(line['time'] / 1000, 60)
                    lyrics.append(f'[{minutes:0>2.0f}:{seconds:05.2f}] {line["words"][0]["string"]}')
        else:
            logger.warning(f'Failed to get lyrics for track id: {track_id}, '
                           f'statucode: {lyrics_json_req.status_code}, Text: {lyrics_json_req.text}')
    except (KeyError, IndexError):
        logger.error(f'Failed to get lyrics for track id: {track_id}, ')
    return None if len(lyrics) <= 2 else '\n'.join(lyrics)


def get_tracks_from_playlist(session, playlist_id):
    logger.info(f"Get tracks from playlist by id '{playlist_id}'")
    songs = []
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    while url:
        resp = make_call(url, token=access_token)
        songs.extend(resp['items'])
        url = resp['next']
    return songs



def sanitize_data(value, allow_path_separators=False, escape_quotes=False):
    logger.info(f'Sanitising string: "{value}"; Allow path separators: {allow_path_separators}')
    if value is None:
        return ''
    sanitize = ['*', '?', '\'', '<', '>', '"', '/'] if os.name == 'nt' else []
    if not allow_path_separators:
        sanitize.append(os.path.sep)
    for i in sanitize:
        value = value.replace(i, '')
    if os.name == 'nt':
        value = value.replace('|', '-')
        drive_letter, tail = None, value
        try:
            if value[0] in string.ascii_letters and value[1:3] == ':\\':
                drive_letter, tail = os.path.splitdrive(value)
        except IndexError:
            logger.warning('String too short..')
        value = os.path.join(
            drive_letter if drive_letter is not None else '',
            tail.replace(':', '-')
        )
        value = value.rstrip('.')
    else:
        if escape_quotes and '"' in value:
            # Since convert uses double quotes, we may need to escape if it exists in path, on windows double quotes is
            # not allowed in path and will be removed
            value = value.replace('"', '\\"')
    return value


def get_album_name(session, album_id):
    logger.info(f"Get album info from album by id ''{album_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/albums/{album_id}', token=access_token)
    if m := re.search(r'(\d{4})', resp['release_date']):
        return resp['artists'][0]['name'], m.group(1), sanitize_data(resp['name']), resp['total_tracks']
    else:
        return sanitize_data(resp['artists'][0]['name']), resp['release_date'], sanitize_data(resp['name']), resp['total_tracks']


def get_album_tracks(session, album_id):
    logger.info(f"Get tracks from album by id '{album_id}'")
    access_token = session.tokens().get("user-read-email")
    songs = []
    offset = 0
    limit = 50
    include_groups = 'album,compilation'

    while True:
        params = {'limit': limit, 'include_groups': include_groups, 'offset': offset}
        resp = make_call(f'https://api.spotify.com/v1/albums/{album_id}/tracks', token=access_token, params=params)
        offset += limit
        songs.extend(resp['items'])

        if len(resp['items']) < limit:
            break
    return songs


def convert_audio_format(filename, quality):
    if os.path.isfile(os.path.abspath(filename)):
        target_path = Path(filename)
        if target_path.suffix == '.ogg':
            # The origin and target formats are same !
            return None
        bitrate = "320k" if quality == AudioQuality.VERY_HIGH else "160k"
        temp_name = os.path.join(target_path.parent, ".~"+target_path.stem+".ogg")
        if os.path.isfile(temp_name):
            os.remove(temp_name)

        os.rename(filename, temp_name)
        # Prepare default parameters
        command = [
            config.get('_ffmpeg_bin_path'),
            '-i', sanitize_data(temp_name, allow_path_separators=True, escape_quotes=False),
            '-ar', '44100', '-ac', '2', '-b:a', bitrate,
        ]
        # Add user defined parameters
        for param in config.get('ffmpeg_args'):
            command.append(param)
        # Add output parameter at last
        command.append( sanitize_data(filename, allow_path_separators=True, escape_quotes=False) )
        logger.info(f'Converting media with ffmpeg. Built commandline {command} ')
        subprocess.check_call(command, shell=False)
        os.remove(temp_name)
    else:
        raise FileNotFoundError


def conv_artist_format(artists):
    formatted = ""
    for artist in artists:
        formatted += artist + config.get('metadata_seperator')+" "
    return formatted[:-2].strip()


def set_audio_tags(filename, metadata, track_id_str):
    logger.info(
        f"Setting tags for audio media at '{filename}', mediainfo -> '{metadata}'")
    type_ = 'track'
    tags = music_tag.load_file(filename)
    for key in metadata.keys():
        value = metadata[key]
        if key == 'artists':
            tags['artist'] = conv_artist_format(value)
        elif key in ['name', 'track_title', 'tracktitle']:
            tags['tracktitle'] = value
        elif key in ['album_name', 'album']:
            tags['album'] = value
        elif key in ['year', 'release_year']:
            tags['year'] = value
        elif key in ['discnumber', 'disc_number', 'disknumber', 'disk_number']:
            tags['discnumber'] = value
        elif key in ['track_number', 'tracknumber']:
            tags['tracknumber'] = value
        elif key == 'lyrics':
            tags['lyrics'] = value
        elif key == 'genre':
            if 'Podcast' in value or 'podcast' in value:
                type_ = 'episode'
            tags['genre'] = conv_artist_format(value)
        elif key in ['total_tracks', 'totaltracks']:
            tags['totaltracks'] = value
        elif key in ['total_discs', 'totaldiscs', 'total_disks', 'totaldisks']:
            tags['totaldiscs'] = value
        elif key == 'isrc':
            tags['isrc'] = value
    tags['comment'] = f'id[spotify.com:{type_}:{track_id_str}]'
    tags.save()


def set_music_thumbnail(filename, image_url):
    logger.info(f"Set thumbnail for audio media at '{filename}' with '{image_url}'")
    img = Image.open(BytesIO(requests.get(image_url).content))
    buf = BytesIO()
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(buf, format='png')
    buf.seek(0)
    tags = music_tag.load_file(filename)
    tags['artwork'] = buf.read()
    tags.save()


def search_by_term(session, search_term, max_results=20, content_types=None) -> dict:
    results = {
        "tracks": [],
        "albums": [],
        "playlists": [],
        "artists": [],
    }
    logger.info(f"Get search result for term '{search_term}', max items '{max_results}'")
    if search_term.strip() == "":
        logger.warning(f"Returning empty data as query is empty !")
        return results
    if content_types is None:
        content_types = ["track", "album", "playlist", "artist"]
    token = session.tokens().get("user-read-email")
    resp = requests.get(
        "https://api.spotify.com/v1/search",
        {
            "limit": max_results,
            "offset": "0",
            "q": search_term,
            "type": ",".join(c_type for c_type in content_types)
        },
        headers={"Authorization": "Bearer %s" % token},
    )
    for c_type in content_types:
        results[c_type + "s"] = resp.json()[c_type + "s"]["items"]
    if len(results["tracks"]) + len(results["albums"]) + len(results["artists"]) + len(results["playlists"]) == 0:
        logger.warning(f"No results for term '{search_term}', max items '{max_results}'")
        raise EmptySearchResultException("No result found for search term '{}' ".format(search_term))
    else:
        return results


def check_premium(session):
    return bool((session.get_user_attribute("type") == "premium") or config.get("force_premium"))


def get_song_info(session, song_id):
    token = session.tokens().get("user-read-email")
    uri = 'https://api.spotify.com/v1/tracks?ids=' + song_id + '&market=from_token'
    uri_credits = f'https://spclient.wg.spotify.com/track-credits-view/v0/experimental/{song_id}/credits'
    info = make_call(uri, token=token)
    credits_json = make_call(uri_credits, token=token)
    credits = {}
    for credit_block in credits_json['roleCredits']:
        try:
            credits[credit_block['roleTitle'].lower()] = [
                artist['name']
                for artist
                in
                credit_block['artists']
                ]
        except KeyError:
            pass
    credits['source'] = credits_json.get('sourceNames', [])
    album_url = info['tracks'][0]['album']['href']
    artist_url = info['tracks'][0]['artists'][0]['href']
    album_data = make_call(album_url, token=token)
    artist_data = make_call(artist_url, token=token)
    artists = []
    for data in info['tracks'][0]['artists']:
        artists.append(sanitize_data(data['name']))
    info = {
        'artists': artists,
        'album_name': sanitize_data(info['tracks'][0]['album']["name"]),
        'name': sanitize_data(info['tracks'][0]['name']),
        'image_url': get_thumbnail(info['tracks'][0]['album']['images'], preferred_size=640000),
        'release_year': info['tracks'][0]['album']['release_date'].split("-")[0],
        'disc_number': info['tracks'][0]['disc_number'],
        'track_number': info['tracks'][0]['track_number'],
        'total_tracks': info['tracks'][0]['album']['total_tracks'],
        'total_discs': sorted([trk['disc_number'] for trk in album_data['tracks']['items']])[-1] if 'tracks' in album_data else 1,
        'scraped_song_id': info['tracks'][0]['id'],
        'is_playable': info['tracks'][0]['is_playable'],
        'popularity': info['tracks'][0]['popularity'],
        'isrc': info['tracks'][0]['external_ids'].get('isrc', ''),
        'genre': artist_data['genres'],
        'duration': info['tracks'][0]['duration_ms'],
        'credits': credits,
        # https://developer.spotify.com/documentation/web-api/reference/get-track
        # List of genre is supposed to be here, genre from album API is deprecated and it always seems to be unavailable
        # Use artist endpoint to get artist's genre instead
        'label': sanitize_data(album_data['label']),
        'copyrights':  [
            sanitize_data(holder['text'])
            for holder
            in album_data['copyrights']
            ],
        'explicit': info['tracks'][0]['explicit']
    }
    return info


def get_episode_info(session, episode_id_str):
    logger.info(f"Get episode info for episode by id '{episode_id_str}'")
    token = session.tokens().get("user-read-email")
    info = make_call("https://api.spotify.com/v1/episodes/" + episode_id_str, token=token)
    if "error" in info:
        return None, None, None
    else:
        return sanitize_data(info["show"]["name"]), sanitize_data(info["name"]), get_thumbnail(info['images']), info['release_date'], info['show']['total_episodes'], sanitize_data(info['show']['publisher'])


def get_show_episodes(session, show_id_str):
    logger.info(f"Get episodes for show by id '{show_id_str}'")
    access_token = session.tokens().get("user-read-email")
    episodes = []
    offset = 0
    limit = 50
    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': limit, 'offset': offset}
        resp = make_call(f'https://api.spotify.com/v1/shows/{show_id_str}/episodes', token=access_token, params=params)
        offset += limit
        for episode in resp["items"]:
            episodes.append(episode["id"])

        if len(resp['items']) < limit:
            break

    return episodes


def get_thumbnail(image_dict, preferred_size=22500):
    images = {}
    for image in image_dict:
        try:
            images[image['height'] * image['width']] = image['url']
        except TypeError:
            # Some playlist and media item do not have cover images
            pass
    available_sizes = sorted(images)
    for size in available_sizes:
        if size >= preferred_size:
            return images[size]
    return images[available_sizes[-1]] if len(available_sizes) > 0 else ""

def make_call(url, token, params=None):
    if params is None:
        params = {}
    request_key = md5(f'{url}-{";".join( str(key)+":"+str(value) for key, value in params.items() )}'.encode()).hexdigest()
    req_cache_file = os.path.join(config.get('_cache_dir'), 'reqcache', request_key+'.otcache')
    os.makedirs(os.path.dirname(req_cache_file), exist_ok=True)
    if os.path.isfile(req_cache_file):
        logger.debug(f'URL "{url}" cache found ! HASH: {request_key}')
        try:
            with open(req_cache_file, 'r', encoding='utf-8') as cf:
                json_data = json.load(cf)
            return json_data
        except json.JSONDecodeError:
            logger.error(f'URL "{url}" cache has invalid data, retring request !')
            pass
    logger.debug(f'URL "{url}" has cache miss ! HASH: {request_key}; Fetching data')
    response = requests.get(url, headers={"Authorization": "Bearer %s" % token}, params=params).text
    with open(req_cache_file, 'w', encoding='utf-8') as cf:
        cf.write(response)
    return json.loads(response)
