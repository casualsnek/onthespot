import queue
import time
import sys
import os
from PyQt5 import uic
from config import config
from exceptions import *
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from runtimedata import thread_pool, session_pool, download_queue, get_logger, cancel_list, failed_downloads, \
    downloads_status, playlist_m3u_queue, downloaded_data
from utils import login_user, remove_user, get_url_data, get_now_playing_local, name_by_from_sdata
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QFileDialog, QPushButton, QTableWidgetItem, \
    QApplication, QDialog, QProgressBar, QLabel, QHBoxLayout, QWidget
from spotutils import search_by_term, get_album_name, get_album_tracks, get_artist_albums, DownloadWorker, \
    get_show_episodes, get_tracks_from_playlist, get_song_info, get_episode_info, get_playlist_data
from showinfm import show_in_file_manager


logger = get_logger("onethespot")


class LoadSessions(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    users = None

    def run(self):
        logger.info('Session loader has started !')
        accounts = config.get('accounts')
        t = len(accounts)
        c = 0
        for account in accounts:
            c = c + 1
            logger.info(f'Trying to create session for {account[0][:4]}')
            self.progress.emit(f'Attempting to create session for:\n{account[0]}  [{c}/{t}] ')
            time.sleep(0.2)
            login = login_user(account[0], "",
                               os.path.join(os.path.expanduser('~'), '.cache', 'casualOnTheSpot', 'sessions'))
            if login[0]:
                # Login was successful, add to session pool
                self.progress.emit(f'Session created for:\n{account[0]}  [{c}/{t}] ')
                time.sleep(0.2)
                session_pool.append(login[1])
                self.__users.append([account[0], 'Premium' if login[3] else 'Free', 'OK'])
            else:
                self.progress.emit(f'Failed to create session for:\n{account[0]}  [{c}/{t}] ')
                self.__users.append([account[0], "LoginERROR", "ERROR"])
        self.finished.emit()

    def setup(self, users):
        self.__users = users


class MediaWatcher(QObject):
    changed_media = pyqtSignal(str, bool)
    finished = pyqtSignal()
    last_url = ''
    __stop = False

    def run(self):
        logger.info('Media watcher thread is running....')
        while not self.__stop:
            try:
                spotify_url = get_now_playing_local(session_pool[config.get("parsing_acc_sn") - 1])
                spotify_url = spotify_url.strip() if spotify_url is not None else ""
                if spotify_url != '' and spotify_url != self.last_url:
                    logger.info(f'Desktop application media changed to: {spotify_url}')
                    self.last_url = spotify_url
                    self.changed_media.emit(spotify_url, True)
                time.sleep(1)
            except FileNotFoundError:
                logger.error('Background monitor failed ! Playerctl not installed')
                break
        self.finished.emit()

    def stop(self):
        self.__stop = True

class PlayListMaker(QObject):
    changed_media = pyqtSignal(str, bool)
    finished = pyqtSignal()
    __stop = False

    def run(self):
        logger.info('Playlist m3u8 builder is running....')
        while not self.__stop:
            play_queue = playlist_m3u_queue.copy()
            ddc = downloaded_data.copy()
            print(ddc, play_queue)
            for play_id in play_queue:
                logger.info(f'Playlist m3u8 checking ID {play_id}')
                if set(play_queue[play_id]['tracks']).intersection(set(ddc.keys())) == set(
                        play_queue[play_id]['tracks']):
                    logger.info(f'Playlist {play_id} has all items ready, making m3u8 playlist at: '
                                f'{{play_queue[play_id]["filename"]}}!')
                    # Write the m3u8 header
                    os.makedirs(os.path.dirname(play_queue[play_id]['filename']), exist_ok=True)
                    with open(play_queue[play_id]['filename'], 'w') as f:
                        f.write('#EXTM3U\n')
                    tid = 1
                    for track_id in play_queue[play_id]['tracks']:
                        logger.info(f'Playlist: {play_id}, adding track: {track_id} to m3u8')
                        with open(play_queue[play_id]['filename'], 'a') as f:
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

    def enqueue_tracks(self, track_list, enqueue_part_cfg, log_id='', itemtype=''):
        for track in track_list:
            logger.info(f'PQP parsing {log_id} <-> track item: {track["name"]}:{track["id"]}')
            exp = '[ 18+ ]' if track['explicit'] else ''
            self.enqueue.emit(
                {
                    'item_id': track['id'],
                    'item_title': f'{exp} {track["name"]}',
                    'item_by_text': f"{','.join([artist['name'] for artist in track['artists']])}",
                    'item_type_text': itemtype,
                    'dl_params': {
                        'media_type': 'track',
                        'extra_paths': enqueue_part_cfg.get('extra_paths', ''),
                        'extra_path_as_root': bool(enqueue_part_cfg.get('dl_path_override', False)),
                    }
                }
            )

    def run(self):
        logger.info('Parsing queue processor is active !')
        while not self.stop:
            item = self.queue.get()
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
                logger.info("Passing control to track downloader for album tracks downloading !!")
                extra_path = config.get("album_name_formatter").format(artist=artist, rel_year=album_release_date,
                                                                       album=album_name)
                enqueue_part_cfg = {
                    'extra_paths': item['data']['dl_path'] if item['data'].get('dl_path', None) else extra_path,
                    'dl_path_override': True if item['data'].get('dl_path', None) else False
                }
                self.enqueue_tracks(tracks, enqueue_part_cfg=enqueue_part_cfg,
                                    log_id=f'{album_name}:{item["media_id"]}',
                                    itemtype=f"Album [{album_release_date}][{album_name}]")
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
                    logger.info("Passing control to track downloader for album artist downloading !!")
                    extra_path = config.get("album_name_formatter").format(artist=artist, rel_year=album_release_date,
                                                                           album=album_name)
                    enqueue_part_cfg = {
                        'extra_paths': item['data']['dl_path'] if item['data'].get('dl_path', None) else extra_path,
                        'dl_path_override': True if item['data'].get('dl_path', None) else False
                    }
                    self.enqueue_tracks(tracks, enqueue_part_cfg=enqueue_part_cfg,
                                        log_id=f'{artist}:{item["media_id"]}', itemtype=f"Artist [{item_name}]")
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
                item_name = item['data'].get('media_title', '')
                enable_m3u = config.get('create_m3u_playlists', False)
                name, owner, description, url = get_playlist_data(session, item["media_id"])
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
                                                                         description=description)+".m3u8")
                        ),
                        'tracks': [ ]
                    }
                for song in playlist_songs:
                    if song['track']['id'] is not None:
                        if enable_m3u:
                            playlist_m3u_queue[item['media_id']]['tracks'].append(song['track']['id'])
                        self.enqueue_tracks([song['track']], enqueue_part_cfg=enqueue_part_cfg,
                                            log_id=f'{item_name}:{item["media_id"]}', itemtype=f"Playlis [{name}]")
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
                                    log_id=f'{name}:{item["media_id"]}', itemtype="Track")
                if not item['data'].get('hide_dialogs', False):
                    self.progress.emit(f"Added track '{name}' to download queue !")

    def setup(self, queue):
        self.queue = queue
        self.stop = False


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(self.path, "ui", "main.ui"), self)
        logger.info("Initialising main window")
        self.btn_save_config.clicked.connect(self.__update_config)
        self.btn_save_adv_config.clicked.connect(self.__update_config)
        self.btn_login_add.clicked.connect(self.__add_account)
        self.btn_search.clicked.connect(self.__get_search_results)
        self.btn_url_download.clicked.connect(lambda x: self.__download_by_url(self.inp_dl_url.text()))
        self.inp_enable_spot_watch.stateChanged.connect(self.__media_watcher_set)
        self.inp_create_playlists.stateChanged.connect(self.__m3u_maker_set)

        self.btn_search_download_all.clicked.connect(lambda x, cat="all": self.__mass_action_dl(cat))
        self.btn_search_download_tracks.clicked.connect(lambda x, cat="tracks": self.__mass_action_dl(cat))
        self.btn_search_download_albums.clicked.connect(lambda x, cat="albums": self.__mass_action_dl(cat))
        self.btn_search_download_artists.clicked.connect(lambda x, cat="artists": self.__mass_action_dl(cat))
        self.btn_search_download_playlists.clicked.connect(lambda x, cat="playlists": self.__mass_action_dl(cat))
        self.btn_download_root_browse.clicked.connect(self.__select_dir)
        self.btn_toggle_advanced.clicked.connect(self.__toggle_advanced)
        self.btn_progress_clear_complete.clicked.connect(self.__clear_complete_downloads)
        self.btn_progress_cancel_all.clicked.connect(self.__cancel_all_downloads)
        self.btn_progress_retry_all.clicked.connect(self.__retry_all_failed)

        self.__playlist_maker = None
        self.__users = []
        self.__media_watcher = None
        self.__media_watcher_thread = None
        self.__parsing_queue = queue.Queue()
        self.__downloads_status = {}
        self.__last_search_data = None

        logger.info("Loading configurations..")
        # Fill the value from configs
        self.__fill_configs()
        self.__advanced_visible = False
        self.tabview.setTabVisible(1, self.__advanced_visible)
        if not self.__advanced_visible:
            self.group_temp_dl_root.hide()

        self.__splash_dialog = _dialog

        logger.info("Preparing session loader")
        # Try logging in to sessions
        self.__session_builder_thread = QThread()
        self.__session_builder_worker = LoadSessions()
        self.__session_builder_worker.setup(self.__users)
        self.__session_builder_worker.moveToThread(self.__session_builder_thread)
        self.__session_builder_thread.started.connect(self.__session_builder_worker.run)
        self.__session_builder_worker.finished.connect(self.__session_builder_thread.quit)
        self.__session_builder_worker.finished.connect(self.__session_builder_worker.deleteLater)
        self.__session_builder_worker.finished.connect(self.__session_load_done)
        self.__session_builder_thread.finished.connect(self.__session_builder_thread.deleteLater)
        self.__session_builder_worker.progress.connect(self.__show_popup_dialog)
        self.__session_builder_thread.start()

        logger.info("Preparing parsing queue processor")
        # Create media queue processor
        self.__media_parser_thread = QThread()
        self.__media_parser_worker = ParsingQueueProcessor()
        self.__media_parser_worker.setup(self.__parsing_queue)
        self.__media_parser_worker.moveToThread(self.__media_parser_thread)
        self.__media_parser_thread.started.connect(self.__media_parser_worker.run)
        self.__media_parser_worker.finished.connect(self.__media_parser_thread.quit)
        self.__media_parser_worker.finished.connect(self.__media_parser_worker.deleteLater)
        self.__media_parser_worker.finished.connect(self.__session_load_done)
        self.__media_parser_thread.finished.connect(self.__media_parser_thread.deleteLater)
        self.__media_parser_worker.progress.connect(self.__show_popup_dialog)
        self.__media_parser_worker.enqueue.connect(self.__add_item_to_downloads)
        self.__media_parser_thread.start()

        logger.info("Setting table item properties")
        tbl_sessions_header = self.tbl_sessions.horizontalHeader()
        tbl_sessions_header.setSectionResizeMode(0, QHeaderView.Stretch)
        tbl_sessions_header.setSectionResizeMode(1, QHeaderView.Stretch)
        tbl_sessions_header.setSectionResizeMode(2, QHeaderView.Stretch)
        tbl_sessions_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        tbl_search_results_headers = self.tbl_search_results.horizontalHeader()
        tbl_search_results_headers.setSectionResizeMode(0, QHeaderView.Stretch)
        tbl_search_results_headers.setSectionResizeMode(1, QHeaderView.Stretch)
        tbl_search_results_headers.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl_search_results_headers.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        tbl_dl_progress_header = self.tbl_dl_progress.horizontalHeader()
        tbl_dl_progress_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        logger.info("Main window init completed !")

    def __m3u_maker_set (self):
        logger.info("Playlist generator watcher set clicked")
        maker_enabled = self.inp_create_playlists.isChecked()
        if maker_enabled and self.__playlist_maker is None:
            logger.info("Starting media watcher thread, no active watcher")
            self.__playlist_maker = PlayListMaker()
            self.__playlist_maker_thread = QThread(parent=self)
            self.__playlist_maker.moveToThread(self.__playlist_maker_thread)
            self.__playlist_maker_thread.started.connect(self.__playlist_maker.run)
            self.__playlist_maker.finished.connect(self.__playlist_maker_thread.quit)
            self.__playlist_maker.finished.connect(self.__playlist_maker.deleteLater)
            self.__playlist_maker.finished.connect(self.__playlist_maker_stopped)
            self.__playlist_maker_thread.finished.connect(self.__playlist_maker_thread.deleteLater)
            self.__playlist_maker_thread.start()
            logger.info("Playlist thread started")
        if maker_enabled is False and self.__playlist_maker is not None:
            logger.info("Active playlist maker, stopping it")
            self.__playlist_maker.stop()
            time.sleep(2)
            self.__playlist_maker = None
            self.__playlist_maker_thread = None

    def __media_watcher_set(self):
        logger.info("Media watcher set clicked")
        media_watcher_enabled = self.inp_enable_spot_watch.isChecked()
        if media_watcher_enabled and self.__media_watcher is None:
            logger.info("Starting media watcher thread, no active watcher")
            self.__media_watcher = MediaWatcher()
            self.__media_watcher_thread = QThread(parent=self)
            self.__media_watcher.moveToThread(self.__media_watcher_thread)
            self.__media_watcher_thread.started.connect(self.__media_watcher.run)
            self.__media_watcher.finished.connect(self.__media_watcher_thread.quit)
            self.__media_watcher.finished.connect(self.__media_watcher.deleteLater)
            self.__media_watcher.finished.connect(self.__media_watcher_stopped)
            self.__media_watcher.changed_media.connect(self.__download_by_url)
            self.__media_watcher_thread.finished.connect(self.__media_watcher_thread.deleteLater)
            self.__media_watcher_thread.start()
            logger.info("Media watcher thread started")
        if media_watcher_enabled is False and self.__media_watcher is not None:
            logger.info("Active watcher, stopping it")
            self.__media_watcher.stop()
            time.sleep(2)
            self.__media_watcher = None
            self.__media_watcher_thread = None

    def __media_watcher_stopped(self):
        logger.info("Watcher stopped")
        if self.inp_create_playlists.isChecked():
            self.inp_create_playlists.setChecked(False)

    def __playlist_maker_stopped(self):
        logger.info("Watcher stopped")
        if self.inp_enable_spot_watch.isChecked():
            self.inp_enable_spot_watch.setChecked(False)

    def __select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        self.inp_download_root.setText(dir_path)

    def __toggle_advanced(self):
        self.__advanced_visible = False if self.__advanced_visible else True
        self.tabview.setTabVisible(1, self.__advanced_visible)
        if not self.__advanced_visible:
            self.group_temp_dl_root.hide()
        else:
            self.group_temp_dl_root.show()

    def __dl_progress(self, data):
        media_id = data[0]
        status = data[1]
        progress = data[2]
        try:
            if status is not None:
                if 'failed' == status.lower() or 'cancelled' == status.lower():
                    downloads_status[media_id]["btn"]['cancel'].hide()
                    downloads_status[media_id]["btn"]['retry'].show()
                if 'downloading' == status.lower():
                    downloads_status[media_id]["btn"]['cancel'].show()
                    downloads_status[media_id]["btn"]['retry'].hide()
                downloads_status[media_id]["status_label"].setText(status)
                logger.debug(f"Updating status text for download item '{media_id}' to '{status}'")
            if progress is not None:
                percent = int((progress[0] / progress[1]) * 100)
                if percent >= 100:
                    downloads_status[media_id]['btn']['cancel'].hide()
                    downloads_status[media_id]['btn']['retry'].hide()
                    downloads_status[media_id]['btn']['locate'].show()
                    downloaded_data[media_id] = {
                        'media_path': data[3],
                        'media_name': data[4]
                    }
                downloads_status[media_id]["progress_bar"].setValue(percent)
                logger.debug(f"Updating progressbar for download item '{media_id}' to '{percent}'%")
        except KeyError:
            logger.error(f"Why TF we get here ?, Got progressbar update for media_id '{media_id}' "
                         f"which does not seem to exist !!! -> Valid Status items: "
                         f"{str([_media_id for _media_id in downloads_status])} "
                         )

    def __add_item_to_downloads(self, item):
        # Create progress status
        pbar = QProgressBar()
        pbar.setValue(0)
        cancel_btn = QPushButton()
        retry_btn = QPushButton()
        locate_btn = QPushButton()
        retry_btn.setText('Retry')
        cancel_btn.setText('Cancel')
        locate_btn.setText('Locate')
        retry_btn.hide()
        locate_btn.hide()
        pbar.setMinimumHeight(30)
        retry_btn.setMinimumHeight(30)
        cancel_btn.setMinimumHeight(30)
        status = QLabel(self.tbl_dl_progress)
        status.setText("Waiting")
        actions = DownloadActionsButtons(item['item_id'], pbar, cancel_btn, retry_btn, locate_btn)
        download_queue.put(
            {
                'media_type': item['dl_params']['media_type'],
                'media_id': item['item_id'],
                'extra_paths': item['dl_params']['extra_paths'],
                'force_album_format': config.get('playlist_track_force_album_dir'),
                'extra_path_as_root': item['dl_params']['extra_path_as_root'],
                'm3u_filename': ''
            }
        )
        downloads_status[item['item_id']] = {
            "status_label": status,
            "progress_bar": pbar,
            "btn": {
                "cancel": cancel_btn,
                "retry": retry_btn,
                "locate": locate_btn
            }
        }
        logger.info(
            f"Adding item to download queue -> media_type:{item['dl_params']['media_type']}, "
            f"media_id: {item['item_id']}, extra_path:{item['dl_params']['extra_paths']}, "
            f"extra_path_as_root: {item['dl_params']['extra_path_as_root']}, Prefix value: ''")
        rows = self.tbl_dl_progress.rowCount()
        self.tbl_dl_progress.insertRow(rows)
        self.tbl_dl_progress.setItem(rows, 0, QTableWidgetItem(item['item_id']))
        self.tbl_dl_progress.setItem(rows, 1, QTableWidgetItem(item['item_title']))
        self.tbl_dl_progress.setItem(rows, 2, QTableWidgetItem(item['item_by_text']))
        self.tbl_dl_progress.setItem(rows, 3, QTableWidgetItem(item['item_type_text']))
        self.tbl_dl_progress.setCellWidget(rows, 4, status)
        self.tbl_dl_progress.setCellWidget(rows, 5, actions)

    def __show_popup_dialog(self, txt):
        self.__splash_dialog.lb_main.setText(str(txt))
        self.__splash_dialog.show()

    def __session_load_done(self):
        self.__splash_dialog.hide()
        self.__splash_dialog.btn_close.show()
        self.__generate_users_table(self.__users)
        self.show()
        # Build threads
        self.__rebuild_threads()

    def __user_table_remove_click(self):
        button = self.sender()
        index = self.tbl_sessions.indexAt(button.pos())
        logger.debug("Clicked account remove button !")
        if index.isValid():
            logger.info("Removed clicked for valid item ->" + self.tbl_sessions.item(index.row(), 0).text())
            username = self.tbl_sessions.item(index.row(), 0).text()
            removed = remove_user(username,
                                  os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "sessions"),
                                  config)
            if removed:
                self.tbl_sessions.removeRow(index.row())
                self.__users = [user for user in self.__users if user[0] == username]
                self.__splash_dialog.run(
                    "Account '{}' was removed successfully!\n"
                    "This account session will remain used until application restart.".format(username))
            else:
                self.__splash_dialog.run(
                    "Something went wrong while removing account with username '{}' !".format(username))

    def __generate_users_table(self, userdata):
        # Clear the table
        while self.tbl_sessions.rowCount() > 0:
            self.tbl_sessions.removeRow(0)
        sn = 0
        for user in userdata:
            sn = sn + 1
            btn = QPushButton(self.tbl_sessions)
            btn.setText(" Remove ")
            btn.clicked.connect(self.__user_table_remove_click)
            btn.setMinimumHeight(30)
            rows = self.tbl_sessions.rowCount()
            br = "N/A"
            if user[1].lower() == "free":
                br = "160K"
            elif user[1].lower() == "premium":
                br = "320K"
            self.tbl_sessions.insertRow(rows)
            self.tbl_sessions.setItem(rows, 0, QTableWidgetItem(user[0]))
            self.tbl_sessions.setItem(rows, 1, QTableWidgetItem(user[1]))
            self.tbl_sessions.setItem(rows, 2, QTableWidgetItem(br))
            self.tbl_sessions.setItem(rows, 3, QTableWidgetItem(user[2]))
            self.tbl_sessions.setCellWidget(rows, 4, btn)
        logger.info("Accounts table was populated !")

    def __rebuild_threads(self):
        # Wait for all threads to close then rebuild threads
        logger.info("Building downloader threads")
        if len(session_pool) > 0:
            logger.warning("Session pool not empty ! Reset not implemented")
            if len(thread_pool) == 0:
                # Build threads now
                logger.info(f"Spawning {config.get('max_threads')} downloaders !")
                for i in range(0, config.get("max_threads")):
                    session_index = None
                    t_index = i
                    while session_index is None:
                        if t_index >= len(session_pool):
                            t_index = t_index - len(session_pool)
                        else:
                            session_index = t_index
                    item = [DownloadWorker(), QThread()]
                    logger.info(f"Spawning DL WORKER {str(i + 1)} using session_index: {t_index}")
                    item[0].setup(thread_name="DL WORKER " + str(i + 1), session=session_pool[t_index],
                                  queue_tracks=download_queue)
                    item[0].moveToThread(item[1])
                    item[1].started.connect(item[0].run)
                    item[0].finished.connect(item[1].quit)
                    item[0].finished.connect(item[0].deleteLater)
                    item[1].finished.connect(item[1].deleteLater)
                    item[0].progress.connect(self.__dl_progress)
                    item[1].start()
                    thread_pool.append(item)
            else:
                # Signal and wait for threads to terminate and clear pool and call self

                pass
        else:
            # Display notice that no session is available and threads are not built
            self.__splash_dialog.run(
                "No session available, login to at least one account and click reinit threads button !")

    def __fill_configs(self):
        self.inp_max_threads.setValue(config.get("max_threads"))
        self.inp_parsing_acc_sn.setValue(config.get("parsing_acc_sn"))
        self.inp_download_root.setText(config.get("download_root"))
        self.inp_download_delay.setValue(config.get("download_delay"))
        self.inp_max_search_results.setValue(config.get("max_search_results"))
        self.inp_max_retries.setValue(config.get("max_retries"))
        self.inp_chunk_size.setValue(config.get("chunk_size"))
        self.inp_media_format.setText(config.get("media_format"))
        self.inp_track_formatter.setText(config.get("track_name_formatter"))
        self.inp_alb_formatter.setText(config.get("album_name_formatter"))
        self.inp_playlist_name_formatter.setText(config.get("playlist_name_formatter"))
        self.inp_max_recdl_delay.setValue(config.get("recoverable_fail_wait_delay"))
        self.inp_dl_endskip.setValue(config.get("dl_end_padding_bytes"))
        if config.get("force_raw"):
            self.inp_raw_download.setChecked(True)
        else:
            self.inp_raw_download.setChecked(False)
        if config.get("watch_bg_for_spotify"):
            self.inp_enable_spot_watch.setChecked(True)
        else:
            self.inp_enable_spot_watch.setChecked(False)
        if config.get("force_premium"):
            self.inp_force_premium.setChecked(True)
        else:
            self.inp_force_premium.setChecked(False)
        if config.get("disable_bulk_dl_notices"):
            self.inp_disable_bulk_popup.setChecked(True)
        else:
            self.inp_disable_bulk_popup.setChecked(False)
        if config.get("playlist_track_force_album_dir"):
            self.inp_force_track_dir.setChecked(True)
        else:
            self.inp_force_track_dir.setChecked(False)
        if config.get("inp_enable_lyrics"):
            self.inp_enable_lyrics.setChecked(True)
        else:
            self.inp_enable_lyrics.setChecked(False)
        if config.get("only_synced_lyrics"):
            self.inp_only_synced_lyrics.setChecked(True)
        else:
            self.inp_only_synced_lyrics.setChecked(False)
        if config.get('create_m3u_playlists'):
            self.inp_create_playlists.setChecked(True)
        else:
            self.inp_create_playlists.setChecked(False)

        logger.info('Config filled to UI')

    def __update_config(self):
        if config.get('max_threads') != self.inp_max_threads.value():
            self.__splash_dialog.run(
                'Thread config was changed ! \n Application needs to be restarted for changes to take effect.'
            )
        config.set_('max_threads', self.inp_max_threads.value())
        if self.inp_parsing_acc_sn.value() > len(session_pool):
            config.set_('parsing_acc_sn', 1)
            self.inp_parsing_acc_sn.setValue(1)
        else:
            config.set_('parsing_acc_sn', self.inp_parsing_acc_sn.value())
        config.set_('download_root', self.inp_download_root.text())
        config.set_('track_name_formatter', self.inp_track_formatter.text())
        config.set_('album_name_formatter', self.inp_alb_formatter.text())
        config.set_('playlist_name_formatter', self.inp_playlist_name_formatter.text())
        config.set_('download_delay', self.inp_download_delay.value())
        config.set_('chunk_size', self.inp_chunk_size.value())
        config.set_('recoverable_fail_wait_delay', self.inp_max_recdl_delay.value())
        config.set_('dl_end_padding_bytes', self.inp_dl_endskip.value())
        config.set_('max_retries', self.inp_max_retries.value())
        config.set_('disable_bulk_dl_notices', self.inp_disable_bulk_popup.isChecked())
        config.set_('playlist_track_force_album_dir', self.inp_force_track_dir.isChecked())
        if 0 < self.inp_max_search_results.value() <= 50:
            config.set_('max_search_results', self.inp_max_search_results.value())
        else:
            config.set_('max_search_results', 5)
        config.set_('media_format', self.inp_media_format.text())
        if self.inp_raw_download.isChecked():
            config.set_('force_raw', True)
        else:
            config.set_('force_raw', False)
        if self.inp_force_premium.isChecked():
            config.set_('force_premium', True)
        else:
            config.set_('force_premium', False)
        if self.inp_enable_spot_watch.isChecked():
            config.set_('watch_bg_for_spotify', True)
        else:
            config.set_('watch_bg_for_spotify', False)
        if self.inp_enable_lyrics.isChecked():
            config.set_('inp_enable_lyrics', True)
        else:
            config.set_('inp_enable_lyrics', False)
        if self.inp_only_synced_lyrics.isChecked():
            config.set_('only_synced_lyrics', True)
        else:
            config.set_('only_synced_lyrics', False)
        if self.inp_create_playlists.isChecked():
            config.set_('create_m3u_playlists', True)
        else:
            config.set_('create_m3u_playlists', False)
        config.update()
        logger.info('Config updated !')

    def __add_account(self):
        logger.info('Add account clicked ')
        if self.inp_login_username.text().strip() in [user[0] for user in config.get('accounts')]:
            self.__splash_dialog.run(
                'The account "{}" is already added !'.format(self.inp_login_username.text().strip()))
            logger.warning('Account already exists ' + self.inp_login_username.text().strip())
        if self.inp_login_username.text().strip() != '' and self.inp_login_password.text() != '':
            logger.debug('Credentials are not empty !')
            login = login_user(self.inp_login_username.text().strip(), self.inp_login_password.text(),
                               os.path.join(os.path.expanduser('~'), '.cache', 'casualOnTheSpot', 'sessions'))
            if login[0]:
                # Save to config and add to session list then refresh tables
                cfg_copy = config.get('accounts').copy()
                new_user = [
                    self.inp_login_username.text().strip(),
                    login[3],
                    int(time.time())
                ]
                cfg_copy.append(new_user)
                config.set_('accounts', cfg_copy)
                config.update()
                session_pool.append(login[1])
                self.__splash_dialog.run(
                    'Logged in successfully ! \n You need to restart application to be able to use this account.'
                )
                logger.info(f"Account {self.inp_login_username.text().strip()} added successfully")
                self.__users.append([self.inp_login_username.text().strip(), 'Premium' if login[3] else 'Free', 'OK'])
                self.__generate_users_table(self.__users)
            else:
                logger.error(f"Account add failed for : {self.inp_login_username.text().strip()}")
                self.__splash_dialog.run('Login failed ! Probably invalid username or password.')
        else:
            logger.info('Credentials are empty >-< ')
            self.__splash_dialog.run('Please enter username/password to log in !')

    def __get_search_results(self):
        search_term = self.inp_search_term.text().strip()
        logger.info(f"Search clicked with value {search_term}")
        if len(session_pool) <= 0:
            self.__splash_dialog.run('You need to login to at least one account to use this feature !')
            return None
        try:
            filters = []
            if self.inp_enable_search_playlists.isChecked():
                filters.append('playlist')
            if self.inp_enable_search_albums.isChecked():
                filters.append('album')
            if self.inp_enable_search_tracks.isChecked():
                filters.append('track')
            if self.inp_enable_search_artists.isChecked():
                filters.append('artist')
            results = search_by_term(session_pool[config.get('parsing_acc_sn') - 1], search_term,
                                     config.get('max_search_results'), content_types=filters)
            self.__populate_search_results(results)
            self.__last_search_data = results
        except EmptySearchResultException:
            self.__last_search_data = []
            while self.tbl_search_results.rowCount() > 0:
                self.tbl_search_results.removeRow(0)
            self.__splash_dialog.run(f"No result found for term '{search_term}' !")
            return None

    def __download_by_url(self, url=None, hide_dialog=False):
        logger.info(f"URL download clicked with value {url}")
        media_type, media_id = get_url_data(url)
        if media_type is None:
            logger.error(f"The type of url could not be determined ! URL: {url}")
            if not hide_dialog:
                self.__splash_dialog.run('Unable to determine the type of URL !')
            return False
        if len(session_pool) <= 0:
            logger.error('User needs to be logged in to download from url')
            if not hide_dialog:
                self.__splash_dialog.run('You need to login to at least one account to use this feature !')
            return False
        queue_item = {
            "media_type": media_type,
            "media_id": media_id,
            "data": {
                "hide_dialogs": hide_dialog,
            }
        }
        tmp_dl_val = self.inp_tmp_dl_root.text().strip()
        if self.__advanced_visible and tmp_dl_val != "" and os.path.isdir(tmp_dl_val):
            queue_item['data']['dl_path'] = tmp_dl_val
        self.__parsing_queue.put(queue_item)
        if not hide_dialog:
            self.__splash_dialog.run(
                f"The {media_type.title()} is being parsed and will be added to download queue shortly ! !")
        return True

    def __insert_search_result_row(self, btn_text, item_name, item_by, item_type, queue_data):
        btn = QPushButton(self.tbl_search_results)
        btn.setText(btn_text.strip())
        btn.clicked.connect(lambda x, q_data=queue_data: self.__parsing_queue.put(q_data))
        btn.setMinimumHeight(30)
        rows = self.tbl_search_results.rowCount()
        self.tbl_search_results.insertRow(rows)
        self.tbl_search_results.setItem(rows, 0, QTableWidgetItem(item_name.rstrip()))
        self.tbl_search_results.setItem(rows, 1, QTableWidgetItem(item_by.strip()))
        self.tbl_search_results.setItem(rows, 2, QTableWidgetItem(item_type.strip()))
        self.tbl_search_results.setCellWidget(rows, 3, btn)
        return True

    def __populate_search_results(self, data):
        # Clear the table
        self.__last_search_data = data
        logger.debug('Populating search results table ')
        while self.tbl_search_results.rowCount() > 0:
            self.tbl_search_results.removeRow(0)
        for d_key in data.keys():  # d_key in ['Albums', 'Artists', 'Tracks', 'Playlists']
            for item in data[d_key]:  # Item is Data for Albums, Artists, etc.
                # Set item name
                item_name, item_by = name_by_from_sdata(d_key, item)
                if item_name is None and item_by is None:
                    continue
                queue_data = {'media_type': d_key[0:-1], 'media_id': item['id'],
                              'data': {
                                  'media_title': item_name.replace("[ 18+ ]", "")
                              }}
                tmp_dl_val = self.inp_tmp_dl_root.text().strip()
                if self.__advanced_visible and tmp_dl_val != "" and os.path.isdir(tmp_dl_val):
                    queue_data['data']['dl_path'] = tmp_dl_val
                btn_text = f"Download {d_key[0:-1]}".replace('artist', 'discography').title()
                self.__insert_search_result_row(btn_text=btn_text, item_name=item_name, item_by=item_by,
                                                item_type=d_key[0:-1].title(), queue_data=queue_data)

    def __mass_action_dl(self, result_type):
        data = self.__last_search_data
        downloaded_types = []
        logger.info(f"Mass download for {result_type} was clicked.. Here hangs up the application")
        if data is None:
            self.__splash_dialog.run('No search results to download !')
        else:
            hide_dialog = config.get('disable_bulk_dl_notices')
            for d_key in data.keys():  # d_key in ['Albums', 'Artists', 'Tracks', 'Playlists']
                if d_key == result_type or result_type == "all":
                    for item in data[d_key]:  # Item is Data for Albums, Artists, etc.
                        item_name, item_by = name_by_from_sdata(d_key, item)
                        if item_name is None and item_by is None:
                            continue
                        queue_data = {'media_type': d_key[0:-1], 'media_id': item['id'],
                                      'data': {
                                          'media_title': item_name.replace('[ 18+ ]', ''),
                                          "hide_dialogs": hide_dialog
                                      }}
                        self.__parsing_queue.put(queue_data)
                    downloaded_types.append(d_key)
            if len(downloaded_types) != 0:
                self.__splash_dialog.run(
                    f"All all results of types {','.join(x for x in downloaded_types)} added to queue"
                )

    def __clear_complete_downloads(self):
        logger.info('Clearing complete downloads')
        complete_ids = []
        for id in downloads_status.keys():
            try:
                logger.info(f"Checking download status for media id: {id}, "
                            f"{downloads_status[id]['progress_bar'].value()}")
                if downloads_status[id]['progress_bar'].value() == 100:
                    logger.info(f'ID: {id} is complete')
                    complete_ids.append(id)
                rows = self.tbl_dl_progress.rowCount()
                for i in range(rows):
                    if self.tbl_dl_progress.item(i, 0).text() in complete_ids:
                        self.tbl_dl_progress.removeRow(i)
                for id in complete_ids:
                    downloads_status.pop(id)
            except (RuntimeError, AttributeError):
                logger.info(f"Checking download status for media id: {id}, Runtime error->Removing")
                complete_ids.append(id)

    def __cancel_all_downloads(self):
        for id in downloads_status:
            if downloads_status[id]['progress_bar'].value() < 95:
                if id not in cancel_list:
                    cancel_list[id] = {}

    def __retry_all_failed(self):
        for id in failed_downloads.keys():
            downloads_status[id]["status_label"].setText("Waiting")
            downloads_status[id]["btn"]['cancel'].show()
            downloads_status[id]["btn"]['retry'].hide()
            download_queue.put(failed_downloads[id].copy())
            failed_downloads.pop(id)


class MiniDialog(QDialog):
    def __init__(self, parent=None):
        super(MiniDialog, self).__init__(parent)
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(self.path, 'ui', 'notice.ui'), self)
        self.btn_close.clicked.connect(self.hide)
        logger.debug('Dialog item is ready..')

    def run(self, content, btn_hidden=False):
        if btn_hidden:
            self.btn_close.hide()
        else:
            self.btn_close.show()
        self.show()
        logger.debug(f"Displaying dialog with text '{content}'")
        self.lb_main.setText(str(content))


class DownloadActionsButtons(QWidget):
    def __init__(self, id, pbar, cbtn, rbtn, lbtn, parent=None):
        super(DownloadActionsButtons, self).__init__(parent)
        self.__id = id
        self.cbtn = cbtn
        self.rbtn = rbtn
        self.lbtn = lbtn
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        cbtn.clicked.connect(self.cancel_item)
        rbtn.clicked.connect(self.retry_item)
        lbtn.clicked.connect(self.locate_file)
        layout.addWidget(pbar)
        layout.addWidget(cbtn)
        layout.addWidget(rbtn)
        layout.addWidget(lbtn)
        self.setLayout(layout)

    def locate_file(self):
        if self.__id in downloaded_data:
            if downloaded_data[self.__id].get('media_path', None):
                show_in_file_manager(os.path.abspath(downloaded_data[self.__id]['media_path']))

    def cancel_item(self):
        cancel_list[self.__id] = {}
        self.cbtn.hide()

    def retry_item(self):
        if self.__id in failed_downloads:
            downloads_status[self.__id]["status_label"].setText("Waiting")
            self.rbtn.hide()
            download_queue.put(failed_downloads[self.__id])
            self.cbtn.show()


if __name__ == '__main__':
    logger.info('Starting application in 3...2....1')
    app = QApplication(sys.argv)
    _dialog = MiniDialog()
    window = MainWindow()
    app.exec_()
    logger.info('Good bye ..')
