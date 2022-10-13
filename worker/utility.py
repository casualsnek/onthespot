import os
import time
from PyQt5.QtCore import QObject, pyqtSignal
from otsconfig import config
from runtimedata import get_logger, playlist_m3u_queue, downloaded_data, session_pool, unavailable
from utils.spotify import get_album_tracks, get_album_name, get_artist_albums, get_show_episodes, get_episode_info, \
    get_song_info, get_tracks_from_playlist, get_playlist_data

logger = get_logger("worker.utility")


class PlayListMaker(QObject):
    changed_media = pyqtSignal(str, bool)
    finished = pyqtSignal()
    __stop = False

    def run(self):
        logger.info('Playlist m3u8 builder is running....')
        while not self.__stop:
            ddc = set(downloaded_data.keys()).difference(unavailable)
            for play_id in list(playlist_m3u_queue.keys()):
                logger.info(f'Playlist m3u8 checking ID {play_id}')
                if set(playlist_m3u_queue[play_id]['tracks']).intersection(ddc) == set(
                        playlist_m3u_queue[play_id]['tracks']):
                    logger.info(f'Playlist {play_id} has all items ready, making m3u8 playlist at: '
                                f'{{play_queue[play_id]["filename"]}}!')
                    # Write the m3u8 header
                    os.makedirs(os.path.dirname(playlist_m3u_queue[play_id]['filename']), exist_ok=True)
                    with open(playlist_m3u_queue[play_id]['filename'], 'w') as f:
                        f.write('#EXTM3U\n')
                    tid = 1
                    for track_id in playlist_m3u_queue[play_id]['tracks']:
                        logger.info(f'Playlist: {play_id}, adding track: {track_id} to m3u8')
                        if track_id in unavailable:
                            logger.info(f'Playlist: {play_id}, track: {track_id}  unavailable for adding, skipping')
                            continue
                        with open(playlist_m3u_queue[play_id]['filename'], 'a') as f:
                            f.write(
                                f'#EXTINF:{tid}, {downloaded_data[track_id]["media_name"]}\n'
                                f'{downloaded_data[track_id]["media_path"]}\n'
                            )
                        tid = tid + 1
                    logger.info(f'Playlist: {play_id} created, removing fro queue list')
                    playlist_m3u_queue.pop(play_id)
                else:
                    logger.info(f"Playlist {play_id} has some items left to download")
            time.sleep(4)
        self.finished.emit()

    def stop(self):
        self.__stop = True


class ParsingQueueProcessor(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    enqueue = pyqtSignal(dict)
    __queue = None
    __stop = True

    def enqueue_tracks(self, track_list, enqueue_part_cfg, log_id='', item_type=''):
        for track in track_list:
            logger.info(f'PQP parsing {log_id} <-> track item: {track["name"]}:{track["id"]}')
            exp = '[ 18+ ]' if track['explicit'] else ''
            self.enqueue.emit(
                {
                    'item_id': track['id'],
                    'item_title': f'{exp} {track["name"]}',
                    'item_by_text': f"{','.join([artist['name'] for artist in track['artists']])}",
                    'item_type_text': item_type,
                    'dl_params': {
                        'media_type': 'track',
                        'extra_paths': enqueue_part_cfg.get('extra_paths', ''),
                        'extra_path_as_root': bool(enqueue_part_cfg.get('dl_path_override', False)),
                    }
                }
            )

    def run(self):
        logger.info('Parsing queue processor is active !')
        while not self.__stop:
            item = self.__queue.get()
            parsing_index = item.get('override_parsing_acc_sn', config.get("parsing_acc_sn") - 1)
            session = session_pool[parsing_index]
            logger.debug(f'Got data to parse: {str(item)}')

            if item['media_type'] == 'album':
                artist, album_release_date, album_name, total_tracks = get_album_name(session, item['media_id'])
                item_name = item['data'].get('media_title', album_name)
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(
                        f'Tracks in album "{item_name}" is being parsed and will be added to download queue shortly !'
                    )
                tracks = get_album_tracks(session, item['media_id'])
                logger.info("Passing control to track downloader.py for album tracks downloading !!")
                extra_path = config.get("album_name_formatter").format(artist=artist, rel_year=album_release_date,
                                                                       album=album_name)
                enqueue_part_cfg = {
                    'extra_paths': item['data']['dl_path'] if item['data'].get('dl_path', None) else extra_path,
                    'dl_path_override': True if item['data'].get('dl_path', None) else False
                }
                self.enqueue_tracks(tracks, enqueue_part_cfg=enqueue_part_cfg,
                                    log_id=f'{album_name}:{item["media_id"]}',
                                    item_type=f"Album [{album_release_date}][{album_name}]")
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(
                        f"Added album '[{album_release_date}] [{total_tracks}] {album_name}' to download queue !"
                    )
            elif item['media_type'] == 'artist':
                item_name = item['data'].get('media_title', 'the artist')
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(
                        f"All albums by {item_name} is being parsed and will be added to download queue soon!"
                    )
                albums = get_artist_albums(session, item['media_id'])
                for album_id in albums:
                    artist, album_release_date, album_name, total_tracks = get_album_name(session, album_id)
                    item_name = artist
                    tracks = get_album_tracks(session, album_id)
                    logger.info("Passing control to track downloader.py for album artist downloading !!")
                    extra_path = config.get("album_name_formatter").format(artist=artist, rel_year=album_release_date,
                                                                           album=album_name)
                    enqueue_part_cfg = {
                        'extra_paths': item['data']['dl_path'] if item['data'].get('dl_path', None) else extra_path,
                        'dl_path_override': True if item['data'].get('dl_path', None) else False
                    }
                    self.enqueue_tracks(tracks, enqueue_part_cfg=enqueue_part_cfg,
                                        log_id=f'{artist}:{item["media_id"]}', item_type=f"Artist [{item_name}]")
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Added tracks by artist '{item_name}' to download queue !")
            elif item['media_type'] == 'podcast':
                show_name = ''
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit('Episodes are being parsed and will be added to download queue shortly !')
                for episode_id in get_show_episodes(session, item['media_id']):
                    show_name, episode_name = get_episode_info(session, episode_id)
                    logger.info(
                        f"PQP parsing podcast : {show_name}:{item['media_id']}, "
                        f"episode item: {episode_name}:{episode_id}"
                    )
                    # TODO: Use new enqueue method
                    self.enqueue.emit([[episode_name, "", f"Podcast [{show_name}]"], "episode", episode_id, ""])
                    self.enqueue.emit(
                        {
                            'item_id': episode_id,
                            'item_title': episode_name,
                            'item_by_text': '',
                            'item_type_text': f"Podcast [{show_name}]",
                            'dl_params': {
                                'media_type': 'episode',
                                'extra_paths': '',
                                'extra_path_as_root': bool(enqueue_part_cfg.get('dl_path_override', False)),
                            }
                        }
                    )
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Added show '{show_name}' to download queue!")
            elif item['media_type'] == 'episode':
                podcast_name, episode_name = get_episode_info(session, item['media_id'])
                logger.info(f"PQP parsing podcast episode : {episode_name}:{item['media_id']}")
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Adding episode '{episode_name}' of '{podcast_name}' to download queue !")
                # TODO: Use new enqueue method
                self.enqueue.emit([[episode_name, "", f"Podcast [{podcast_name}]"], "episode", item['media_id'], ""])
                self.enqueue.emit(
                    {
                        'item_id': item['media_id'],
                        'item_title': episode_name,
                        'item_by_text': '',
                        'item_type_text': f"Podcast [{podcast_name}]",
                        'dl_params': {
                            'media_type': 'episode',
                            'extra_paths': '',
                            'extra_path_as_root': bool(enqueue_part_cfg.get('dl_path_override', False)),
                        }
                    }
                )
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Added episode '{episode_name}' of {podcast_name} to download queue!")
            elif item['media_type'] == "playlist":
                enable_m3u = config.get('create_m3u_playlists', False)
                name, owner, description, url = get_playlist_data(session, item["media_id"])
                item_name = item['data'].get('media_title', name)
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(
                        f"Tracks in playlist '{item_name}' by {owner['display_name']} is being parsed and "
                        f"will be added to download queue shortly!"
                    )
                playlist_songs = get_tracks_from_playlist(session_pool[config.get("parsing_acc_sn") - 1],
                                                          item['media_id'])
                enqueue_part_cfg = {'extra_paths': item['data'].get('dl_path', ''),
                                    'dl_path_override': True if item['data'].get('dl_path', None) else False
                                    }
                if enable_m3u:
                    playlist_m3u_queue[item['media_id']] = {
                        'filename': os.path.abspath(
                            os.path.join(
                                config.get('download_root'),
                                config.get('playlist_name_formatter').format(name=name, owner=owner['display_name'],
                                                                             description=description) + ".m3u8")
                        ),
                        'tracks': []
                    }
                for song in playlist_songs:
                    if song['track']['id'] is not None:
                        if enable_m3u:
                            playlist_m3u_queue[item['media_id']]['tracks'].append(song['track']['id'])
                        self.enqueue_tracks([song['track']], enqueue_part_cfg=enqueue_part_cfg,
                                            log_id=f'{item_name}:{item["media_id"]}', item_type=f"Playlist [{name}]")
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Added playlist '{item_name}' by {owner['display_name']} to download queue !")
            elif item['media_type'] == 'track':
                artists, album_name, name, image_url, release_year, disc_number, track_number, scraped_song_id, \
                    is_playable = get_song_info(session, item['media_id'])
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Adding track '{name}' to download queue !")
                enqueue_part_cfg = {
                    'extra_paths': item['data'].get('dl_path', ''),
                    'dl_path_override': True if item['data'].get('dl_path', None) else False
                }
                track_obj = {
                    'id': item['media_id'],
                    'name': name,
                    'explicit': False,
                    'artists': [{'name': name} for name in artists]
                }
                self.enqueue_tracks([track_obj], enqueue_part_cfg=enqueue_part_cfg,
                                    log_id=f'{name}:{item["media_id"]}', item_type="Track")
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Added track '{name}' to download queue !")

    def setup(self, queue):
        self.__queue = queue
        self.__stop = 0
