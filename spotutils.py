from exceptions import *
import requests
import threading
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

requests.adapters.DEFAULT_RETRIES = 10

def get_artist_albums(session, artist_id):
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        f'https://api.spotify.com/v1/artists/{artist_id}/albums', headers=headers).json()
    return [resp['items'][i]['id'] for i in range(len(resp['items']))]

def get_tracks_from_playlist(session, playlist_id):
    songs = []
    offset = 0
    limit = 100
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
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
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(
        f'https://api.spotify.com/v1/albums/{album_id}', headers=headers).json()
    if m := re.search('(\d{4})', resp['release_date']):
        return resp['artists'][0]['name'], m.group(1),sanitize_data(resp['name']),resp['total_tracks']
    else: return resp['artists'][0]['name'], resp['release_date'],sanitize_data(resp['name']),resp['total_tracks']


def get_album_tracks(session, album_id):
    access_token = session.tokens().get("user-read-email")
    songs = []
    offset = 0
    limit = 50
    include_groups = 'album,compilation'

    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': limit, 'include_groups':include_groups, 'offset': offset}
        resp = requests.get(
            f'https://api.spotify.com/v1/albums/{album_id}/tracks', headers=headers, params=params).json()
        offset += limit
        songs.extend(resp['items'])

        if len(resp['items']) < limit:
            break

    return songs


def convert_audio_format(filename, quality):
    raw_audio = AudioSegment.from_file(filename, format="ogg",
                                       frame_rate=44100, channels=2, sample_width=2)
    if quality == AudioQuality.VERY_HIGH:
        bitrate = "320k"
    else:
        bitrate = "160k"
    raw_audio.export(filename, format=config.get("media_format"), bitrate=bitrate)


def conv_artist_format(artists):
    formatted = ""
    for artist in artists:
        formatted += artist + ", "
    return formatted[:-2]


def set_audio_tags(filename, artists, name, album_name, release_year, disc_number, track_number, track_id_str):
    tags = music_tag.load_file(filename)
    tags['artist'] = conv_artist_format(artists)
    tags['tracktitle'] = name
    tags['album'] = album_name
    tags['year'] = release_year
    tags['discnumber'] = disc_number
    tags['tracknumber'] = track_number
    tags['comment'] = 'id[spotify.com:track:'+track_id_str+']'
    tags.save()


def set_music_thumbnail(filename, image_url):
    img = requests.get(image_url).content
    tags = music_tag.load_file(filename)
    tags['artwork'] = img
    tags.save()


def search_by_term(session, search_term, max_results=20)->dict:
    token = session.tokens().get("user-read-email")
    resp = requests.get(
        "https://api.spotify.com/v1/search",
        {
            "limit": max_results,
            "offset": "0",
            "q": search_term,
            "type": "track,album,playlist,artist"
        },
        headers={"Authorization": "Bearer %s" % token},
    )
    results = {
            "tracks": resp.json()["tracks"]["items"],
            "albums": resp.json()["albums"]["items"],
            "playlists": resp.json()["playlists"]["items"],
            "artists": resp.json()["artists"]["items"],
        }
    if len(results["tracks"]) + len(results["albums"]) + len(results["artists"]) + len(results["playlists"]) == 0:
        raise EmptySearchResultException("No result found for search term '{}' ".format(search_term))
    else:
        return results


def check_premium(session):
    return bool((session.get_user_attribute("type") == "premium") or config.get("force_premium"))


def get_song_info(session, song_id):
    token = session.tokens().get("user-read-email")
    info = json.loads(requests.get("https://api.spotify.com/v1/tracks?ids=" + song_id +
                    '&market=from_token', headers={"Authorization": "Bearer %s" % token}).text)
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
    token = session.tokens().get("user-read-email")
    info = json.loads(requests.get("https://api.spotify.com/v1/episodes/" +
                                   episode_id_str, headers={"Authorization": "Bearer %s" % token}).text)

    if "error" in info:
        return None, None
    else:
        return sanitize_data(info["show"]["name"]), sanitize_data(info["name"])


def get_show_episodes(session, show_id_str):
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

    def download_track(self, session, track_id_str, extra_paths="", prefix=False, prefix_value='',):
        SKIP_EXISTING_FILES = True
        CHUNK_SIZE = config.get("chunk_size")
        quality = AudioQuality.HIGH
        if check_premium(session):
            quality = AudioQuality.VERY_HIGH
        try:
            artists, album_name, name, image_url, release_year, disc_number, track_number, scraped_song_id, is_playable = get_song_info(session, track_id_str)
            _artist = artists[0]
            if prefix:
                _track_number = str(track_number).zfill(2)
                song_name = f'{_artist} - {album_name} - {_track_number}. {name}.{config.get("media_format")}'
                filename = os.path.join(config.get("download_root"), extra_paths, song_name)
            else:
                song_name = f'{_artist} - {album_name} - {name}.{config.get("media_format")}'
                filename = os.path.join(config.get("download_root"), extra_paths, song_name)
        except Exception as e:
            self.progress.emit([track_id_str, "Get metadata failed", None])
            return False
        try:
            if not is_playable:
                self.progress.emit([track_id_str, "Unavailable", None])
                return False
            else:
                if os.path.isfile(filename) and os.path.getsize(filename) and SKIP_EXISTING_FILES:
                    self.progress.emit([track_id_str, "Already exists", [100, 100]])
                    return False
                else:
                    if track_id_str != scraped_song_id:
                        track_id_str = scraped_song_id

                    track_id = TrackId.from_base62(track_id_str)
                    stream = session.content_feeder().load(
                        track_id, VorbisOnlyAudioQuality(quality), False, None)
                    os.makedirs(os.path.join(config.get("download_root"), extra_paths),exist_ok=True)
                    total_size = stream.input_stream.size
                    downloaded = 0
                    _CHUNK_SIZE = CHUNK_SIZE
                    fail = 0
                    with open(filename, 'wb') as file:
                        while downloaded <= total_size:
                            data = stream.input_stream.stream().read(_CHUNK_SIZE)
                            downloaded += len(data)
                            file.write(data)
                            self.progress.emit([track_id_str, None, [downloaded, total_size]])
                            if (total_size - downloaded) < _CHUNK_SIZE:
                                _CHUNK_SIZE = total_size - downloaded
                            if len(data) == 0 :
                                fail += 1
                            if fail > config.get("max_retries"):
                                self.progress.emit([track_id_str, "RETRY "+str(fail+1), None])
                                break
                            self.progress.emit([track_id_str, None, [downloaded, total_size]])
                    if not config.get("force_raw"):
                        self.progress.emit([track_id_str, "Converting", None])
                        convert_audio_format(filename, quality)
                        self.progress.emit([track_id_str, "Writing metadata", None])
                        set_audio_tags(filename, artists, name, album_name,
                                        release_year, disc_number, track_number, track_id_str)
                        self.progress.emit([track_id_str, "Setting thumbnail", None])
                        set_music_thumbnail(filename, image_url)
                        self.progress.emit([track_id_str, None, [100, 100]])
                        self.progress.emit([track_id_str, "Downloaded", None])
                        return True
        except queue.Empty as e:
            if os.path.exists(filename):
                os.remove(filename)
            self.progress.emit([track_id_str, "Timeout. Will retry", None])
            return None
        except pydub.exceptions.CouldntDecodeError as e:
            if os.path.exists(filename):
                os.remove(filename)
            self.progress.emit([track_id_str, "Decode error. Will retry", None])
            traceback.print_exc()
            return None
        except Exception as e:
            if os.path.exists(filename):
                os.remove(filename)
            self.progress.emit([track_id_str, "Failed", None])
            traceback.print_exc()
            return False

    def download_episode(self, episode_id_str, extra_paths=""):
        ROOT_PODCAST_PATH = os.path.join(config.get("download_root"), "Podcasts")
        quality = AudioQuality.HIGH
        podcast_name, episode_name = get_episode_info(episode_id_str)
        if extra_paths == "":
            extra_paths = os.path.join(extra_paths, podcast_name)

        if podcast_name is None:
            self.progress.emit([episode_id_str, "Not Found", [0, 100]])
            return False
        else:
            try:
                filename = podcast_name + " - " + episode_name

                episode_id = EpisodeId.from_base62(episode_id_str)
                stream = self.__session.content_feeder().load(episode_id, VorbisOnlyAudioQuality(quality), False, None)
                os.makedirs(os.path.join(ROOT_PODCAST_PATH, extra_paths), exist_ok=True)
                total_size = stream.input_stream.size
                data_left = total_size
                downloaded = 0
                _CHUNK_SIZE = config.get("chunk_size")
                fail = 0

                with open(os.path.join(ROOT_PODCAST_PATH, extra_paths, + filename + ".wav"), 'wb') as file:
                    while downloaded <= total_size:
                        data = stream.input_stream.stream().read(_CHUNK_SIZE)
                        downloaded += len(data)
                        bar.update(file.write(data))
                        if (total_size - downloaded) < _CHUNK_SIZE:
                            _CHUNK_SIZE = total_size - downloaded
                        if len(data) == 0 :
                            fail += 1
                        if fail > config.get("max_retries"):
                            self.progress.emit([episode_id_str, "RETRY "+str(fail+1), None])
                            break
                if downloaded >= total_size:
                    self.progress.emit([episode_id_str, "Downloaded", [100, 100]])
                    return True
                else:
                    self.progress.emit([episode_id_str, "Failed", [0, 100]])
                    return False
            except:
                self.progress.emit([episode_id_str, "Failed", [0, 100]])
                return False

    def run(self):
        print("Running ", self.name)
        while not self.__stop:
            item = self.__queue.get()
            attempt = 0
            if item[0] == "track":
                print("Thread ", self.name, " downloading track: ", item[1])
                while attempt < config.get("max_retries"):
                    attempt = attempt + 1
                    self.progress.emit([item[1], "Downloading", None])
                    status = self.download_track(
                        session=self.__session,
                        track_id_str=item[1],
                        extra_paths=item[2],
                        prefix=item[3],
                        prefix_value=item[4]
                        )
                    if status == None:
                        self.progress.emit([item[1], "Retrying in 10 sec", [0, 100]])
                        time.sleep(config.get("recoverable_fail_wait_delay"))
                    else:
                        break
                time.sleep(config.get("download_delay"))

            elif item[0] == "episode":
                print("Thread ", self.name, " downloading episode: ", item[1])
                while attempt < config.get("max_retries"):
                    attempt = attempt + 1
                    self.progress.emit([item[1], "Downloading", None])
                    status = self.download_episode(
                        session=self.__session,
                        episode_id_str=item[1],
                        extra_paths=item[2],
                        )
                    if status == None:
                        self.progress.emit([item[1], "Retrying in 10 sec", [0, 100]])
                        time.sleep(config.get("recoverable_fail_wait_delay"))
                    else:
                        break
                time.sleep(config.get("download_delay"))

    def setup(self, thname, session, queue_tracks):
        self.name = thname
        self.__session = session
        self.__queue = queue_tracks
        self.__stop = False
