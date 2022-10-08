from PyQt5.QtWidgets import QMainWindow, QHeaderView, QFileDialog, QPushButton, QTableWidgetItem, QApplication, QDialog, QProgressBar, QLabel
from PyQt5 import uic
from config import config
from utils import login_user, remove_user, time, get_url_data, get_now_playing_local
import sys, os
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
from exceptions import *
from spotutils import search_by_term, get_album_name, get_album_tracks, get_artist_albums, DownloadWorker, get_show_episodes, get_tracks_from_playlist, get_song_info
import re, json, queue
from runtimedata import thread_pool, session_pool, download_queue, get_logger


logger = get_logger("onethespot")

class LoadSessions(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)

    def run(self):
        logger.info("Session loader has started !")
        accounts = config.get("accounts")
        t = len(accounts)
        c = 0
        for account in accounts:
            c = c + 1
            logger.info(f"Trying to create session for {account[0][:4]}")
            self.progress.emit("Attempting to create session for:\n"+account[0]+"  [ {c}/{t} ]".format(
                    c=c,
                    t=t
                    ))
            time.sleep(0.2)
            login = login_user(account[0], "", os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "sessions"))
            if login[0]:
                # Login was successful, add to session pool
                self.progress.emit("Session created for:\n"+account[0]+"  [ {c}/{t} ]".format(
                    c=c,
                    t=t
                    ))
                time.sleep(0.2)
                session_pool.append(login[1])
                self.__users.append([ account[0], "Premuim" if login[3] else "Free", "OK"])
            else:
                self.progress.emit("Failed to create session for:\n"+account[0]+"  [ {c}/{t} ]".format(
                    c=c,
                    t=t
                    ))
                self.__users.append([ account[0], "LoginERROR", "ERROR"])
        self.finished.emit()

    def setup(self, users):
        self.__users = users

class MediaWatcher(QObject):
    changed_media = pyqtSignal(str, bool)
    finished = pyqtSignal()
    last_url = ""
    __stop = False

    def run(self):
        logger.info("Media watcher thread is running....")
        while not self.__stop:
            try:
                spotify_url = get_now_playing_local(session_pool[config.get("parsing_acc_sn")-1])
                spotify_url = spotify_url.strip() if spotify_url is not None else ""
                if spotify_url != "" and spotify_url != self.last_url:
                    logger.info(f"Desktop application media changed to: {spotify_url}")
                    self.last_url = spotify_url
                    self.changed_media.emit(spotify_url, True)
                time.sleep(1)
            except FileNotFoundError:
                logger.error("Background monitor failed ! Playerctl not installed")
                break
        self.finished.emit()

    def stop(self):
        self.__stop = True

class ParsingQueueProcessor(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    enqueue = pyqtSignal(list)

    def run(self):
        logger.info("Parsing queue processor is active !")
        while not self.stop:
            entry = self.queue.get()
            # a="album", b=album, c=itemname, d=Silent
            #            b = { "id": "" }
            logger.debug("Got data to parse: "+str(entry))
            if entry[0] == "album":
                if not entry[3]:
                    self.progress.emit("Tracks in album '{itemname}' is being parsed and will be added to download queue shortly !".format(
                        itemname=entry[2].strip()
                        ))
                artist, album_release_date, album_name, total_tracks = get_album_name(session_pool[config.get("parsing_acc_sn")-1], entry[1]["id"])
                tracks = get_album_tracks(session_pool[config.get("parsing_acc_sn")-1], entry[1]["id"])
                for track in tracks:
                    logger.info(f"PQP parsing album : {album_name}:{entry[1]['id']}, track item: {track['name']}:{track['id']}")
                    exp = ""
                    if track["explicit"]:
                        exp = "[ 18+ ]"
                    self.enqueue.emit([[f"{exp} {track['name']}", f"{','.join([_artist['name'] for _artist in track['artists']])}", f"Album [{album_release_date}][{album_name}]"], "track", track["id"], os.path.join(config.get("album_name_formatter").format(artist=artist, rel_year=album_release_date, album=album_name)), False])
                if not entry[3]:
                    self.progress.emit(f"Added album '[{album_release_date}] [{total_tracks}] {album_name}' to download queue !")
               # Add to downloads table
            elif entry[0] == "artist":
                if not entry[3]:
                    self.progress.emit("All albumbs by atrist '{itemname}' is being parsed and will be added to download queue shortly !".format(
                        itemname=entry[2].strip()
                        ))
                albums = get_artist_albums(session_pool[config.get("parsing_acc_sn")-1], entry[1]["id"])
                for album_id in albums:
                    artist, album_release_date, album_name, total_tracks = get_album_name(session_pool[config.get("parsing_acc_sn")-1], album_id)
                    tracks = get_album_tracks(session_pool[config.get("parsing_acc_sn")-1], album_id)
                    for track in tracks:
                        logger.info(f"PQP parsing artist : {artist}:{entry[1]['id']}, album item: {album_name}:{album_id} ,track item: {track['name']}:{track['id']}")
                        exp = ""
                        if track["explicit"]:
                            exp = "[ 18+ ]"
                        self.enqueue.emit([[f"{exp} {track['name']}", f"{','.join([_artist['name'] for _artist in track['artists']])}", f"Album [{album_release_date}][{album_name}]"], "track", track["id"], os.path.join(config.get("album_name_formatter").format(artist=artist, rel_year=album_release_date, album=album_name)), False])
                if not entry[3]:
                    self.progress.emit("Added tracks by artist '{itemname}' to download queue !".format(itemname=entry[2].strip()))
            elif entry[0] == "podcast":
                showname = ""
                if not entry[3]:
                    self.progress.emit("Episodes are being parsed and will be added to download queue shortly !")
                for episode_id in get_show_episodes(session_pool[config.get("parsing_acc_sn")-1], entry[1]["id"]):
                    podcast_name, episode_name = get_episode_info(session_pool[config.get("parsing_acc_sn")-1], episode_id)
                    logger.info(f"PQP parsing podcast : {podcast_name}:{entry[1]['id']}, epiode item: {episode_name}:{episode_id}")
                    showname = podcast_name
                    self.enqueue.emit([[name, name, f"Podcast [{podcast_name}]"], "episode", episode_id, ""])
                if not entry[3]:
                    self.progress.emit(f"Added show '{showname}' to download queue!")
            elif entry[0] == "episode":
                podcast_name, episode_name = get_episode_info(session_pool[config.get("parsing_acc_sn")-1], entry[1]["id"])
                logger.info(f"PQP parsing podcast episode : {episode_name}:{entry[1]['id']}")
                if not entry[3]:
                    self.progress.emit(f"Adding episode '{episode_name}' of '{podcast_name}' to download queue !")
                self.enqueue.emit([[name, name, f"Podcast [{podcast_name}]"], "episode", entry[1]["id"], ""])
                if not entry[3]:
                    self.progress.emit(f"Added episode '{episode_name}' of {podcast_name} to download queue!")
            elif entry[0] == "playlist":
                if not entry[3]:
                    self.progress.emit("Tracks in playlist '{itemname}' is being parsed and will be added to download queue shortly !".format(
                    itemname=entry[2].strip()
                    ))
                playlist_songs = get_tracks_from_playlist(session_pool[config.get("parsing_acc_sn")-1], entry[1]['id'])
                for song in playlist_songs:
                    if song['track']['id'] is not None:
                        logger.info(f"PQP parsing playlist : {entry[1]['id']}, track item: {song['track']['name']}:{song['track']['id']}")
                        exp = ""
                        if song['track']["explicit"]:
                            exp = "[ 18+ ]"
                        #artists, album_name, name, image_url, release_year, disc_number, track_number, scraped_song_id, is_playable = get_song_info(session_pool[0], song['track']['id'])
                        self.enqueue.emit([[f"{exp} {song['track']['name']}", f"{','.join([artist['name'] for artist in song['track']['artists']])}", "Playlist"], "track", song['track']['id'], "", config.get("playlist_track_force_album_dir")])
                if not entry[3]:
                    self.progress.emit("Added playlist '{itemname}' to download queue !".format(
                    itemname=entry[2].strip()
                    ))
            elif entry[0] == "track":
                if not entry[3]:
                    self.progress.emit("Adding track '{itemname}' to download queue !".format(
                    itemname=entry[2].strip()
                    ))
                logger.info(f"PQP parsinf track : {entry[2].strip()}:{entry[1]['id']}")
                self.enqueue.emit([[entry[2].strip(), f"{','.join([artist['name'] for artist in entry[1]['artists']])}", "Track"], "track", entry[1]["id"], "", config.get("playlist_track_force_album_dir")])
                if not entry[3]:
                    self.progress.emit("Added track '{itemname}' to download queue !".format(
                    itemname=entry[2].strip()
                ))


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

        self.btn_search_download_all.clicked.connect(lambda x, cat="all": self.__mass_action_dl(cat))
        self.btn_search_download_tracks.clicked.connect(lambda x, cat="tracks": self.__mass_action_dl(cat))
        self.btn_search_download_albums.clicked.connect(lambda x, cat="albums": self.__mass_action_dl(cat))
        self.btn_search_download_artists.clicked.connect(lambda x, cat="artists": self.__mass_action_dl(cat))
        self.btn_search_download_playlists.clicked.connect(lambda x, cat="playlists": self.__mass_action_dl(cat))
        self.btn_download_root_browse.clicked.connect(self.__select_dir)
        self.btn_toggle_advanced.clicked.connect(self.__toggle_advanced)

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
        if self.inp_enable_spot_watch.isChecked():
            self.inp_enable_spot_watch.setChecked(False)


    def __select_dir(self):
        dir_path = QFileDialog.getExistingDirectory(None, 'Select a folder:', os.path.expanduser("~"))
        self.inp_download_root.setText(dir_path)

    def __toggle_advanced(self):
        self.__advanced_visible = False if self.__advanced_visible else True
        self.tabview.setTabVisible(1, self.__advanced_visible)

    def __dl_progress(self, data):
        media_id = data[0]
        status = data[1]
        progress = data[2]
        try:
            if status is not None:
                self.__downloads_status[media_id]["status_label"].setText(status)
                logger.debug(f"Updating status text for download item '{media_id}' to '{status}'")
            if progress is not None:
                percent = int((progress[0]/progress[1])*100)
                self.__downloads_status[media_id]["progress_bar"].setValue(percent)
                logger.debug(f"Updating progresbar for download item '{media_id}' to '{percent}'%")
        except KeyError:
            logger.error(f"Why TF we get here ?, Got progressbar update for media_id '{media_id}' which does not seem to exist !!! -> Valid Status items: {str( [_media_id for _media_id in self.__downloads_status] )} ")
        except Exception:
            logger.error(f"Unexpected exception while updating status for download items: {traceback.format_exc()}")

    def __add_item_to_downloads(self, item):
        # Create progress status
        pbar = QProgressBar(self.tbl_dl_progress)
        pbar.setValue(0)
        pbar.setMinimumHeight(30)
        status = QLabel(self.tbl_dl_progress)
        status.setText("Waiting")
        # Submit to download queue
        #                  [ media_type, Media_id, extra_path, Prefix, Prefixvalue ]
        try:
            pfix_enable = item[4]
        except IndexError:
            pfix_enable = False
        download_queue.put([item[1], item[2], item[3], pfix_enable, ""])
        self.__downloads_status[item[2]] = {
                "status_label": status,
                "progress_bar": pbar
            }
        logger.info(f"Adding item to download queue -> media_type:{item[1]}, media_id: {item[2]}, extra_path:{item[3]}, prefix: {pfix_enable}, Prefixvalue: ''")
        rows = self.tbl_dl_progress.rowCount()
        self.tbl_dl_progress.insertRow(rows)
        self.tbl_dl_progress.setItem(rows, 0, QTableWidgetItem(item[2]))
        self.tbl_dl_progress.setItem(rows, 1, QTableWidgetItem(item[0][0]))
        self.tbl_dl_progress.setItem(rows, 2, QTableWidgetItem(item[0][1]))
        self.tbl_dl_progress.setItem(rows, 3, QTableWidgetItem(item[0][2]))
        self.tbl_dl_progress.setCellWidget(rows, 4, status)
        self.tbl_dl_progress.setCellWidget(rows, 5, pbar)

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
            logger.info("Removed cicked for valid item ->"+self.tbl_sessions.item(index.row(), 0).text())
            username = self.tbl_sessions.item(index.row(), 0).text()
            removed = remove_user(username, os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "sessions"), config)
            if removed:
                self.tbl_sessions.removeRow(index.row())
                self.__users = [user for user self.__users if user[0] == username]
                self.__splash_dialog.run("Account '{}' was removed successfully!\nThis account session will remain used until application restart.".format(username))
            else:
                self.__splash_dialog.run("Something went wrong while removing account with username '{}' !".format(username))

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
                logger.info(f"Spwaning {config.get('max_threads')} downloaders !")
                for i in range(0, config.get("max_threads")):
                    session_index = None
                    t_index = i
                    while session_index is None:
                        if t_index >= len(session_pool):
                            t_index = t_index - len(session_pool)
                        else:
                            session_index = t_index
                    item = [DownloadWorker(), QThread()]
                    logger.info(f"Spwaning DL WORKER {str(i+1)} using session_index: {t_index}")
                    item[0].setup(thname="DL WORKER "+str(i+1), session=session_pool[t_index], queue_tracks=download_queue)
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
            self.__splash_dialog.run("No session available, login to at least one account and click reinit threads button !")

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
        logger.info("Config filled to UI")

    def __update_config(self):
        if config.get("max_threads") != self.inp_max_threads.value():
            self.__splash_dialog.run("Thread config was changed ! \n Application needs to be restarted for changes to take effect.")
        config.set_("max_threads", self.inp_max_threads.value())
        if self.inp_parsing_acc_sn.value() > len(session_pool):
            config.set_("parsing_acc_sn", 1)
            self.inp_parsing_acc_sn.setValue(1)
        else:
            config.set_("parsing_acc_sn", self.inp_parsing_acc_sn.value())
        config.set_("download_root", self.inp_download_root.text())
        config.set_("track_name_formatter", self.inp_track_formatter.text())
        config.set_("album_name_formatter", self.inp_alb_formatter.text())
        config.set_("download_delay", self.inp_download_delay.value())
        config.set_("chunk_size", self.inp_chunk_size.value())
        config.set_("recoverable_fail_wait_delay", self.inp_max_recdl_delay.value())
        config.set_("dl_end_padding_bytes", self.inp_dl_endskip.value())
        config.set_("max_retries", self.inp_max_retries.value())
        config.set_("disable_bulk_dl_notices", self.inp_disable_bulk_popup.isChecked())
        config.set_("playlist_track_force_album_dir", self.inp_force_track_dir.isChecked())
        if self.inp_max_search_results.value() > 0 and self.inp_max_search_results.value() <= 50:
            config.set_("max_search_results", self.inp_max_search_results.value())
        else:
            config.set_("max_search_results", 5)
        config.set_("media_format", self.inp_media_format.text())
        if self.inp_raw_download.isChecked():
            config.set_("force_raw", True)
        else:
            config.set_("force_raw", False)
        if self.inp_force_premium.isChecked():
            config.set_("force_premium", True)
        else:
            config.set_("force_premium", False)
        if self.inp_enable_spot_watch.isChecked():
            config.set_("watch_bg_for_spotify", True)
        else:
            config.set_("watch_bg_for_spotify", False)
        config.update()
        logger.info("Config updated !")

    def __add_account(self):
        logger.info("Add account clicked ")
        if self.inp_login_username.text().strip() in [ user[0] for user in config.get('accounts')]:
            self.__splash_dialog.run("The account '{}' is already added !".format(self.inp_login_username.text().strip()))
            logger.warning("Account already exists "+self.inp_login_username.text().strip())
        if self.inp_login_username.text().strip() != "" and self.inp_login_password.text() != "":
            logger.debug("Credentials are not empty ! ")
            login = login_user(self.inp_login_username.text().strip(), self.inp_login_password.text(), os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "sessions"))
            if login[0]:
                # Save to config and add to session list then refresh tables
                cfg_copy = config.get("accounts").copy()
                new_user = [
                    self.inp_login_username.text().strip(),
                    login[3],
                    int(time.time())
                    ]
                cfg_copy.append(new_user)
                config.set_("accounts", cfg_copy)
                config.update()
                session_pool.append(login[1])
                self.__splash_dialog.run("Loggedin successfully ! \n You need to restart application to be able to use this account. ")
                logger.info(f"Account {self.inp_login_username.text().strip()} added successfully")
                self.__users.append([ self.inp_login_username.text().strip(), "Premuim" if login[3] else "Free", "OK"])
                self.__generate_users_table(self.__users)
            else:
                logger.error(f"Accouunt add failed for : {self.inp_login_username.text().strip()}")
                self.__splash_dialog.run("Login failed ! Probably invalid username or passowrd.")
        else:
            logger.info("Credentials are empty >-< ")
            self.__splash_dialog.run("Please enter username/password to log in !")

    def __get_search_results(self):
        search_term = self.inp_search_term.text().strip()
        logger.info(f"Search clicked with value {search_term}")
        if len(session_pool) <= 0:
            self.__splash_dialog.run("You need to login to at least one account to use this feature !")
            return None
        try:
            results = search_by_term(session_pool[config.get("parsing_acc_sn")-1], search_term, config.get("max_search_results"))
            self.__populate_search_results(results)
        except EmptySearchResultException:
            self.__last_search_data = []
            while self.tbl_search_results.rowCount() > 0:
                self.tbl_search_results.removeRow(0)
            self.__splash_dialog.run("No result found for term '{}' !".format(search_term))
            return None

    def __download_by_url(self, url=None, hide_dialog=False):
        logger.info(f"URL download clicked with value {url}")
        media_type, media_id = get_url_data(url)
        if media_type is None:
            logger.error(f"The type of url could not be determined ! URL: {url}")
            if not hide_dialog:
                self.__splash_dialog.run("Unable to determine the type of URL !")
            return False
        if len(session_pool) <= 0:
            logger.info(f"LMAO user needs to login before downloading or making search query")
            logger.warning("User needs to be logged in to download from url")
            if not hide_dialog:
                self.__splash_dialog.run("You need to login to at least one account to use this feature !")
            return False
        data = {
            "id": media_id
        }
        title = ""
        if media_type == "track":
            artists, album_name, name, image_url, release_year, disc_number, track_number, scraped_song_id, is_playable = get_song_info(session_pool[config.get("parsing_acc_sn")-1], media_id)
            data["artists"] = [{'name': name} for name in artists]
            # GET TITLE
            title = name
        self.__parsing_queue.put([media_type, data, title, hide_dialog])
        if not hide_dialog:
                self.__splash_dialog.run(f"The {media_type.title()} is being parsed and will be added to download queue shortly ! !")
        return False


    def __populate_search_results(self, data):
        # Clear the table
        self.__last_search_data = data
        logger.debug("Populating search results table ")
        while self.tbl_search_results.rowCount() > 0:
                self.tbl_search_results.removeRow(0)
        for track in data["tracks"]:
            if track["explicit"]:
                exp = "[ 18+ ]"
            else:
                exp = "       "

            itemname = f"{exp} {track['name']}"
            by = f"{','.join([artist['name'] for artist in track['artists']])}"
            btn = QPushButton(self.tbl_search_results)
            btn.setText(" Download Track")
            # d = Silent Mode
            btn.clicked.connect(lambda x, a="track", b=track, c=itemname.replace("[ 18+ ]", ""): self.__parsing_queue.put([a, b, c, False]))
            btn.setMinimumHeight(30)
            rows = self.tbl_search_results.rowCount()
            self.tbl_search_results.insertRow(rows)
            self.tbl_search_results.setItem(rows, 0, QTableWidgetItem(itemname))
            self.tbl_search_results.setItem(rows, 1, QTableWidgetItem(by))
            self.tbl_search_results.setItem(rows, 2, QTableWidgetItem("Track"))
            self.tbl_search_results.setCellWidget(rows, 3, btn)

        for album in data["albums"]:
            rel_year = re.search('(\d{4})', album['release_date']).group(1)
            itemname = f"[Y:{rel_year}] [T:{album['total_tracks']}] {album['name']}"
            by = f"{','.join([artist['name'] for artist in album['artists']])}"
            btn = QPushButton(self.tbl_search_results)
            btn.setText(" Download Album")
            btn.clicked.connect(lambda x, a="album", b=album, c=itemname: self.__parsing_queue.put([a, b, c, False]))
            btn.setMinimumHeight(30)
            rows = self.tbl_search_results.rowCount()
            self.tbl_search_results.insertRow(rows)
            self.tbl_search_results.setItem(rows, 0, QTableWidgetItem(itemname))
            self.tbl_search_results.setItem(rows, 1, QTableWidgetItem(by))
            self.tbl_search_results.setItem(rows, 2, QTableWidgetItem("Album"))
            self.tbl_search_results.setCellWidget(rows, 3, btn)

        for playlist in data["playlists"]:
            itemname = f"{playlist['name']}"
            by = f"{playlist['owner']['display_name']}"
            btn = QPushButton(self.tbl_search_results)
            btn.setText(" Download Playlist")
            btn.clicked.connect(lambda x, a="playlist", b=playlist, c=itemname: self.__parsing_queue.put([a, b, c, False]))
            btn.setMinimumHeight(30)
            rows = self.tbl_search_results.rowCount()
            self.tbl_search_results.insertRow(rows)
            self.tbl_search_results.setItem(rows, 0, QTableWidgetItem(itemname))
            self.tbl_search_results.setItem(rows, 1, QTableWidgetItem(by))
            self.tbl_search_results.setItem(rows, 2, QTableWidgetItem("Playlist"))
            self.tbl_search_results.setCellWidget(rows, 3, btn)

        for artist in data["artists"]:
            itemname = f"{artist['name']}"
            if f"{'/'.join(artist['genres'])}" != "":
                itemname = itemname + f"  |  GENERES: {'/'.join(artist['genres'])}"
            by = f"{artist['name']}"
            btn = QPushButton(self.tbl_search_results)
            btn.setText(" Download Discography")
            btn.clicked.connect(lambda x, a="artist", b=artist, c=itemname: self.__parsing_queue.put([a, b, c, False]))
            btn.setMinimumHeight(30)
            rows = self.tbl_search_results.rowCount()
            self.tbl_search_results.insertRow(rows)
            self.tbl_search_results.setItem(rows, 0, QTableWidgetItem(itemname))
            self.tbl_search_results.setItem(rows, 1, QTableWidgetItem(by))
            self.tbl_search_results.setItem(rows, 2, QTableWidgetItem("Artist"))
            self.tbl_search_results.setCellWidget(rows, 3, btn)

    def __mass_action_dl(self, result_type):
        data = self.__last_search_data
        downloaded_types = []
        logger.info(f"Mass download for {result_type} was clicked.. Here hangs up the applicationn")
        if data is None:
            self.__splash_dialog.run("No search results to download !")
        else:
            if result_type == "tracks" or result_type == "all":
                # Download all track types
                for track in data["tracks"]:
                    self.__parsing_queue.put(["track", track, f"{track['name']}", config.get("disable_bulk_dl_notices")])
                downloaded_types.append("tracks")
            if result_type == "albums" or result_type == "all":
                for album in data["albums"]:
                    self.__parsing_queue.put(["artist", album, f"[YEAR: {rel_year} ] [ TRACKS: {album['total_tracks']} ] {album['name']}", config.get("disable_bulk_dl_notices")])
                downloaded_types.append("albums")
            if result_type == "artists" or result_type == "all":
                for artist in data["artists"]:
                    self.__parsing_queue.put(["artist", artist, f"{artist['name']}", config.get("disable_bulk_dl_notices")])
                downloaded_types.append("artists")
            if result_type == "playlists" or result_type == "all":
                for playlist in data["playlists"]:
                    self.__parsing_queue.put(["playlist", playlist, f"{playlist['name']}", config.get("disable_bulk_dl_notices")])
                downloaded_types.append("playlists")
            if len(downloaded_types) != 0:
                self.__splash_dialog.run(f"All all results of types {','.join(x for x in downloaded_types)} added to queue")


class MiniDialog(QDialog):
    def __init__(self, parent=None):
        super(MiniDialog, self).__init__(parent)
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(self.path, "ui", "notice.ui"), self)
        self.btn_close.clicked.connect(self.hide)
        logger.debug("Dialog item is ready..")

    def run(self, content):
        self.show()
        logger.debug(f"Displaying dialog with text '{content}'")
        self.lb_main.setText(str(content))

if __name__ == "__main__":
    logger.info("Starting application in 3...2....1")
    app = QApplication(sys.argv)
    _dialog = MiniDialog()
    window = MainWindow()
    app.exec_()
    logger.info("Goodbyee..")
