from exceptions import *
import requests.adapters
import time
from config import config
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.metadata import TrackId, EpisodeId
from pydub import AudioSegment
import requests
import json
import music_tag
import os
import re
import queue
from PyQt5.QtCore import QObject, pyqtSignal
import traceback
import pydub.exceptions
from runtimedata import get_logger, cancel_list, failed_downloads

logger = get_logger("spotutils")
requests.adapters.DEFAULT_RETRIES = 10
ext_ = ".exe" if config.platform == "Windows" else ""
AudioSegment.converter = os.path.join(config.get("ffmpeg_bin_dir"), "ffmpeg" + ext_)
AudioSegment.ffmpeg = os.path.join(config.get("ffmpeg_bin_dir"), "ffmpeg" + ext_)
AudioSegment.ffprobe = os.path.join(config.get("ffmpeg_bin_dir"), "ffprobe" + ext_)

logger.info(f"AudioSegment Config: {AudioSegment.converter}, {AudioSegment.ffprobe}")


def get_artist_albums(session, artist_id):
    logger.info(f"Get albums for artist by id '{artist_id}'")
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        f'https://api.spotify.com/v1/artists/{artist_id}/albums', headers=headers).json()
    return [resp['items'][i]['id'] for i in range(len(resp['items']))]


def get_playlist_data(session, playlist_id):
    logger.info(f"Get playlist dump for '{playlist_id}'")
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers).json()
    return resp['name'], resp['owner'], resp['description'], resp['external_urls']['spotify']


def get_track_lyrics(session, track_id, forced_synced):
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
        if lyrics_json_req.status_code == 200:
            lyrics_json = lyrics_json_req.json()
            lyrics.append(f'[au:{lyrics_json["provider"]}]')
            lyrics.append('[by:casualsnek-onTheSpot]')
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
        logger.error(f'Failed to get lyrics for track id: {track_id}, '
                     f'statucode: {lyrics_json_req.status_code}, Text: {lyrics_json_req.text}')
    return None if len(lyrics) <= 2 else '\n'.join(lyrics)


def get_tracks_from_playlist(session, playlist_id):
    logger.info(f"Get tracks from playlist by id '{playlist_id}'")
    songs = []
    offset = 0
    limit = 100
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    while True:
        params = {'limit': limit, 'offset': offset}
        resp = requests.get(
            f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks', headers=headers, params=params).json()
        offset += limit
        songs.extend(resp['items'])

        if len(resp['items']) < limit:
            break

    return songs


def sanitize_data(value):
    sanitize = ["\\", "/", ":", "*", "?", "'", "<", ">", '"']
    for i in sanitize:
        value = value.replace(i, "")
    return value.replace("|", "-")


def get_album_name(session, album_id):
    logger.info(f"Get album info from album by id ''{album_id}'")
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        f'https://api.spotify.com/v1/albums/{album_id}', headers=headers).json()
    if m := re.search(r'(\d{4})', resp['release_date']):
        return resp['artists'][0]['name'], m.group(1), sanitize_data(resp['name']), resp['total_tracks']
    else:
        return resp['artists'][0]['name'], resp['release_date'], sanitize_data(resp['name']), resp['total_tracks']


def get_album_tracks(session, album_id):
    logger.info(f"Get tracks from album by id '{album_id}'")
    access_token = session.tokens().get("user-read-email")
    songs = []
    offset = 0
    limit = 50
    include_groups = 'album,compilation'

    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': limit, 'include_groups': include_groups, 'offset': offset}
        resp = requests.get(
            f'https://api.spotify.com/v1/albums/{album_id}/tracks', headers=headers, params=params).json()
        offset += limit
        songs.extend(resp['items'])

        if len(resp['items']) < limit:
            break

    return songs


def convert_audio_format(filename, quality):
    logger.info(f"Audiosegment media at '{filename}'")
    if os.path.isfile(os.path.abspath(filename)):
        raw_audio = AudioSegment.from_file(os.path.abspath(filename), format="ogg",
                                           frame_rate=44100, channels=2, sample_width=2)
        if quality == AudioQuality.VERY_HIGH:
            bitrate = "320k"
        else:
            bitrate = "160k"
        logger.info(f"Export media at '{filename}'")
        out_file = raw_audio.export(os.path.abspath(filename), format=config.get("media_format"), bitrate=bitrate)
        out_file.close()
    else:
        raise FileNotFoundError


def conv_artist_format(artists):
    formatted = ""
    for artist in artists:
        formatted += artist + ", "
    return formatted[:-2]


def set_audio_tags(filename, artists, name, album_name, release_year, disc_number, track_number, track_id_str):
    logger.info(
        f"Setting tags for audio media at '{filename}', mediainfo -> '{str(artists)}, {name}, {album_name}, "
        f"{release_year}, {disc_number}, {track_number}, {track_id_str}' ")
    tags = music_tag.load_file(filename)
    tags['artist'] = conv_artist_format(artists)
    tags['tracktitle'] = name
    tags['album'] = album_name
    tags['year'] = release_year
    tags['discnumber'] = disc_number
    tags['tracknumber'] = track_number
    tags['comment'] = 'id[spotify.com:track:' + track_id_str + ']'
    tags.save()


def set_music_thumbnail(filename, image_url):
    logger.info(f"Set thumbnail for audio media at '{filename}' with '{image_url}'")
    img = requests.get(image_url).content
    tags = music_tag.load_file(filename)
    tags['artwork'] = img
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
    info = json.loads(requests.get(uri, headers={"Authorization": "Bearer %s" % token}).text)
    artists = []
    for data in info['tracks'][0]['artists']:
        artists.append(sanitize_data(data['name']))
    album_name = sanitize_data(info['tracks'][0]['album']["name"])
    name = sanitize_data(info['tracks'][0]['name'])
    image_url = info['tracks'][0]['album']['images'][0]['url']
    release_year = info['tracks'][0]['album']['release_date'].split("-")[0]
    disc_number = info['tracks'][0]['disc_number']
    track_number = info['tracks'][0]['track_number']
    scraped_song_id = info['tracks'][0]['id']
    is_playable = info['tracks'][0]['is_playable']
    return artists, album_name, name, image_url, release_year, disc_number, track_number, scraped_song_id, is_playable


def get_episode_info(session, episode_id_str):
    logger.info(f"Get episode info for episode by id '{episode_id_str}'")
    token = session.tokens().get("user-read-email")
    info = json.loads(requests.get("https://api.spotify.com/v1/episodes/" +
                                   episode_id_str, headers={"Authorization": "Bearer %s" % token}).text)

    if "error" in info:
        return None, None
    else:
        return sanitize_data(info["show"]["name"]), sanitize_data(info["name"])


def get_show_episodes(session, show_id_str):
    logger.info(f"Get episodes for show by id '{show_id_str}'")
    access_token = session.tokens().get("user-read-email")
    episodes = []
    offset = 0
    limit = 50

    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': limit, 'offset': offset}
        resp = requests.get(
            f'https://api.spotify.com/v1/shows/{show_id_str}/episodes', headers=headers, params=params).json()
        offset += limit
        for episode in resp["items"]:
            episodes.append(episode["id"])

        if len(resp['items']) < limit:
            break

    return episodes


class DownloadWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(list)

    name = None
    __session = None
    __queue = None
    __stop = True

    def download_track(self, session, track_id_str, extra_paths="", force_album_format=False, extra_path_as_root=False):
        trk_track_id_str = track_id_str
        logger.debug(
            f"Downloading track by id '{track_id_str}', extra_paths: '{extra_paths}', "
            f"extra_path_as_root: '{extra_path_as_root}' ")
        if trk_track_id_str in cancel_list:
            self.progress.emit([trk_track_id_str, "Cancelled", [0, 100]])
            cancel_list.pop(trk_track_id_str)
            failed_downloads[trk_track_id_str] = {}
            return False
        skip_existing_file = True
        chunk_size = config.get("chunk_size")
        quality = AudioQuality.HIGH
        if check_premium(session) or config.get('force_premium'):
            quality = AudioQuality.VERY_HIGH
        try:
            artists, album_name, name, image_url, release_year, disc_number, track_number, \
            scraped_song_id, is_playable = get_song_info(session, track_id_str)
            _artist = artists[0]
            if force_album_format and extra_path_as_root is False:
                # If prefix is true use artist / album directory formatter
                extra_paths = os.path.join(config.get("album_name_formatter").format(artist=_artist,
                                                                                     rel_year=release_year,
                                                                                     album=album_name
                                                                                     ))
            song_name = config.get("track_name_formatter").format(artist=_artist,
                                                                  album=album_name,
                                                                  name=name,
                                                                  rel_year=release_year,
                                                                  disc_number=disc_number,
                                                                  track_number=track_number,
                                                                  spotid=scraped_song_id
                                                                  ) + "." + config.get("media_format")
            if not extra_path_as_root:
                filename = os.path.join(config.get("download_root"), extra_paths, song_name)
            else:
                filename = os.path.join(os.path.abspath(extra_paths), song_name)
        except Exception:
            logger.error(f"Metadata fetching failed for track by id '{trk_track_id_str}', {traceback.format_exc()}")
            self.progress.emit([trk_track_id_str, "Get metadata failed", None])
            return False
        try:
            if not is_playable:
                self.progress.emit([trk_track_id_str, "Unavailable", None])
                logger.error(f"Track is unavailable, track id '{trk_track_id_str}'")
                return False
            else:
                if os.path.isfile(filename) and os.path.getsize(filename) and skip_existing_file:
                    self.progress.emit([trk_track_id_str, "Already exists", [100, 100],
                                        filename, f'{name} [{_artist} - {album_name}:{release_year}].mp3'])
                    logger.info(f"File already exists, Skipping download for track by id '{trk_track_id_str}'")
                    return True
                else:
                    if track_id_str != scraped_song_id:
                        track_id_str = scraped_song_id

                    track_id = TrackId.from_base62(track_id_str)
                    stream = session.content_feeder().load(
                        track_id, VorbisOnlyAudioQuality(quality), False, None)
                    os.makedirs(os.path.join(config.get("download_root"), extra_paths), exist_ok=True)
                    total_size = stream.input_stream.size
                    downloaded = 0
                    _CHUNK_SIZE = chunk_size
                    fail = 0
                    with open(filename, 'wb') as file:
                        while downloaded < total_size:
                            if trk_track_id_str in cancel_list:
                                self.progress.emit([trk_track_id_str, "Cancelled", [0, 100]])
                                cancel_list.pop(trk_track_id_str)
                                failed_downloads[trk_track_id_str] = {}
                                return False
                            data = stream.input_stream.stream().read(_CHUNK_SIZE)
                            logger.debug(f"Reading chunk of {_CHUNK_SIZE} bytes for track by id '{trk_track_id_str}'")
                            downloaded += len(data)
                            if len(data) != 0:
                                file.write(data)
                                self.progress.emit([trk_track_id_str, None, [downloaded, total_size]])
                            if len(data) == 0 and _CHUNK_SIZE > config.get("dl_end_padding_bytes"):
                                logger.error(
                                    f"PD Error for track by id '{trk_track_id_str}', "
                                    f"while reading chunk size: {_CHUNK_SIZE}"
                                )
                                fail += 1
                            elif len(data) == 0 and _CHUNK_SIZE <= config.get("dl_end_padding_bytes"):
                                break
                            if (total_size - downloaded) < _CHUNK_SIZE:
                                _CHUNK_SIZE = total_size - downloaded
                            if fail > config.get("max_retries"):
                                self.progress.emit([trk_track_id_str, "RETRY " + str(fail + 1), None])
                                logger.error(f"Max retries exceed for track by id '{trk_track_id_str}'")
                                self.progress.emit([trk_track_id_str, "PD error. Will retry", None])
                                if os.path.exists(filename):
                                    os.remove(filename)
                                return None
                            self.progress.emit([trk_track_id_str, None, [downloaded, total_size]])
                    if not config.get("force_raw"):
                        logger.warning(
                            f"Force raw is disabled for track by id '{trk_track_id_str}', "
                            f"media converting and tagging will be done !"
                        )
                        self.progress.emit([trk_track_id_str, "Converting", None])
                        convert_audio_format(filename, quality)
                        self.progress.emit([trk_track_id_str, "Writing metadata", None])
                        set_audio_tags(filename, artists, name, album_name,
                                       release_year, disc_number, track_number, trk_track_id_str)
                        self.progress.emit([trk_track_id_str, "Setting thumbnail", None])
                        set_music_thumbnail(filename, image_url)

                        self.progress.emit([trk_track_id_str, "Downloaded", [100, 100],
                                            filename, f'{name} [{_artist} - {album_name}:{release_year}].mp3'])

                        logger.info(f"Downloaded track by id '{trk_track_id_str}'")
                        if config.get('inp_enable_lyrics'):
                            logger.info(f'Fetching lyrics for track id: {trk_track_id_str}, '
                                        f'{config.get("only_synced_lyrics")}')
                            try:
                                lyrics = get_track_lyrics(session, trk_track_id_str, config.get('only_synced_lyrics'))
                                if lyrics:
                                    logger.info(f'Found lyrics for: {trk_track_id_str}, writing...')
                                    with open(filename[0:-len(config.get('media_format'))] + 'lrc', 'w') as f:
                                        f.write(lyrics)
                                    logger.info(f'lyrics saved for: {trk_track_id_str}')
                            except:
                                logger.error(f'Could not get lyrics for {trk_track_id_str}, '
                                             f'unexpected error: {traceback.format_exc()}')
                        return True
                    else:
                        logger.info(f"Downloaded track by id '{trk_track_id_str}', in raw mode")
                        self.progress.emit([trk_track_id_str, "Downloaded", [100, 100],
                                            filename, f'{name} [{_artist} - {album_name}:{release_year}].mp3'])
                        return True
        except queue.Empty:
            if os.path.exists(filename):
                os.remove(filename)
            logger.error(
                f"Network timeout from spotify for track by id '{trk_track_id_str}', download will be retried !")
            self.progress.emit([trk_track_id_str, "Timeout. Will retry", None])
            return None
        except pydub.exceptions.CouldntDecodeError:
            if os.path.exists(filename):
                os.remove(filename)
            logger.error(
                f"Decoding error for track by id '{trk_track_id_str}', "
                f"possibly due to use of rate limited spotify account !"
            )
            self.progress.emit([trk_track_id_str, "Decode error. Will retry", None])
            traceback.print_exc()
            return None
        except Exception:
            if os.path.exists(filename):
                os.remove(filename)
            self.progress.emit([trk_track_id_str, "Failed", None])
            logger.error(
                f"Download failed for track by id '{trk_track_id_str}', Unexpected error: {traceback.format_exc()} !")
            return False

    def download_episode(self, session, episode_id_str, extra_paths=""):
        logger.info(f"Downloading episode by id '{episode_id_str}'")
        podcast_path = os.path.join(config.get("download_root"), config.get("podcast_subdir", "Podcasts"))
        quality = AudioQuality.HIGH
        podcast_name, episode_name = get_episode_info(session, episode_id_str)
        if extra_paths == "":
            extra_paths = os.path.join(extra_paths, podcast_name)
        if podcast_name is None:
            self.progress.emit([episode_id_str, "Not Found", [0, 100]])
            logger.error(f"Downloading failed for episode by id '{episode_id_str}', Not found")
            return False
        else:
            try:
                filename = podcast_name + " - " + episode_name

                episode_id = EpisodeId.from_base62(episode_id_str)
                stream = session.content_feeder().load(episode_id, VorbisOnlyAudioQuality(quality), False, None)
                os.makedirs(os.path.join(podcast_path, extra_paths), exist_ok=True)
                total_size = stream.input_stream.size
                downloaded = 0
                _CHUNK_SIZE = config.get("chunk_size")
                fail = 0

                with open(os.path.join(podcast_path, extra_paths, + filename + ".wav"), 'wb') as file:
                    while downloaded <= total_size:
                        data = stream.input_stream.stream().read(_CHUNK_SIZE)
                        downloaded += len(data)
                        file.write(data)
                        self.progress.emit([episode_id_str, None, [downloaded, total_size]])
                        if (total_size - downloaded) < _CHUNK_SIZE:
                            _CHUNK_SIZE = total_size - downloaded
                        if len(data) == 0:
                            fail += 1
                        if fail > config.get("max_retries"):
                            self.progress.emit([episode_id_str, "RETRY " + str(fail + 1), None])
                            break
                if downloaded >= total_size:
                    logger.info(f"Episode by id '{episode_id_str}', downloaded")
                    self.progress.emit([episode_id_str, "Downloaded", [100, 100]])
                    return True
                else:
                    logger.error(f"Downloading failed for episode by id '{episode_id_str}', partial download failed !")
                    self.progress.emit([episode_id_str, "Failed", [0, 100]])
                    return False
            except Exception:
                logger.error(
                    f"Downloading failed for episode by id "
                    f"'{episode_id_str}', Unexpected Exception: {traceback.format_exc()}"
                )
                self.progress.emit([episode_id_str, "Failed", [0, 100]])
                return False

    def run(self):
        logger.info(f"Download worker {self.name} is running ")
        while not self.__stop:
            item = self.__queue.get()
            attempt = 0
            last_cancelled = False
            if item['media_type'] == "track":
                while attempt < config.get("max_retries"):  # Let it be 2
                    logger.info(f"Processing download for track by id '{item['media_id']}', Attempt: {attempt}")
                    attempt = attempt + 1
                    self.progress.emit([item['media_id'], "Downloading", None])
                    status = self.download_track(
                        session=self.__session,
                        track_id_str=item['media_id'],
                        extra_paths=item['extra_paths'],
                        force_album_format=item['force_album_format'],
                        extra_path_as_root=item['extra_path_as_root']
                    )
                    if status is None and attempt < config.get("max_retries"):  # 2 < 2
                        self.progress.emit([item['media_id'], "Retrying in 10 sec", [0, 100]])
                        time.sleep(config.get("recoverable_fail_wait_delay"))
                    elif status is None and attempt >= config.get("max_retries"):
                        status = False
                    if status is False:
                        logger.error(f"Download process returned false: {item['media_id']}")
                        logger.error(f"Attempt for: {item['media_id']}, {attempt}, {config.get('max_retries')}")
                        if attempt >= config.get("max_retries"):  # 2 < 2
                            logger.error(f"Marking failed for: {item['media_id']}, "
                                         f"{attempt}, {config.get('max_retries')}")
                            self.progress.emit([item['media_id'], "Failed", [0, 100]])
                            logger.error(f'Marking failed Attempts higher than max retries: {attempt},'
                                         f' {config.get("max_retries")}')
                            failed_downloads[item['media_id']] = item
                            break
                        elif item['media_id'] in failed_downloads:
                            logger.info('Media id: {item["media_id"]}, was probably cancelled by user')
                            failed_downloads[item['media_id']] = item
                            last_cancelled = True
                            break
                    if status is True:
                        break
                if not last_cancelled:
                    time.sleep(config.get("download_delay"))

            elif item['media_type'] == "episode":
                while attempt < config.get("max_retries"):
                    logger.info(f"Processing download for episode by id '{item['media_id']}', Attempt: {attempt}")
                    attempt = attempt + 1
                    self.progress.emit([item['media_id'], "Downloading", None])
                    status = self.download_episode(
                        session=self.__session,
                        episode_id_str=item['media_id'],
                        extra_paths=item['extra_paths'],
                    )
                    if status is None:
                        self.progress.emit([item['media_id'], "Retrying in 10 sec", [0, 100]])
                        time.sleep(config.get("recoverable_fail_wait_delay"))
                    else:
                        break
                time.sleep(config.get("download_delay"))

    def setup(self, thread_name, session, queue_tracks):
        self.name = thread_name
        self.__session = session
        self.__queue = queue_tracks
        self.__stop = False
