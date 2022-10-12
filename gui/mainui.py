import os
import queue
import time
from PyQt5 import uic
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMainWindow, QHeaderView, QLabel, QPushButton, QProgressBar, QTableWidgetItem, QFileDialog

from exceptions import EmptySearchResultException
from utils.spotify import search_by_term
from utils.utils import name_by_from_sdata, login_user, remove_user, get_url_data
from worker import LoadSessions, ParsingQueueProcessor, MediaWatcher, PlayListMaker, DownloadWorker
from .dl_progressbtn import DownloadActionsButtons
from .minidialog import MiniDialog
from otsconfig import config
from runtimedata import get_logger, download_queue, downloads_status, downloaded_data, failed_downloads, cancel_list, \
    session_pool, thread_pool

logger = get_logger('gui.main_ui')


def dl_progress_update(data):
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


def retry_all_failed_downloads():
    for dl_id in failed_downloads.keys():
        downloads_status[dl_id]["status_label"].setText("Waiting")
        downloads_status[dl_id]["btn"]['cancel'].show()
        downloads_status[dl_id]["btn"]['retry'].hide()
        download_queue.put(failed_downloads[dl_id].copy())
        failed_downloads.pop(dl_id)


def cancel_all_downloads():
    for did in downloads_status.keys():
        try:
            if downloads_status[did]['progress_bar'].value() < 95:
                if did not in cancel_list:
                    cancel_list[did] = {}
        except (KeyError, RuntimeError):
            pass


class MainWindow(QMainWindow):

    def __init__(self, _dialog):
        super(MainWindow, self).__init__()
        self.path = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(self.path, "qtui", "main.ui"), self)
        logger.info("Initialising main window")

        # Bind button click
        self.bind_button_inputs()

        # Create required variables to store configuration state about other threads/objects
        self.__playlist_maker = None
        self.__media_watcher_thread = None
        self.__media_watcher = None
        # Variable to store data for class use
        self.__users = []
        self.__parsing_queue = queue.Queue()
        self.__last_search_data = None

        # Fill the value from configs
        logger.info("Loading configurations..")
        self.__fill_configs()

        # Hide the advanced tab on initial startup
        self.__advanced_visible = False
        self.tabview.setTabVisible(1, self.__advanced_visible)
        if not self.__advanced_visible:
            self.group_temp_dl_root.hide()

        self.__splash_dialog = _dialog

        # Start/create session builder and queue processor
        logger.info("Preparing session loader")
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

        # Set the table header properties
        self.set_table_props()
        logger.info("Main window init completed !")

    def bind_button_inputs(self):
        # Connect button click signals
        self.btn_search.clicked.connect(self.__get_search_results)
        self.btn_login_add.clicked.connect(self.__add_account)
        self.btn_save_config.clicked.connect(self.__update_config)
        self.btn_seset_config.clicked.connect(self.reset_app_config)
        self.btn_url_download.clicked.connect(lambda x: self.__download_by_url(self.inp_dl_url.text()))
        self.btn_save_adv_config.clicked.connect(self.__update_config)
        self.btn_toggle_advanced.clicked.connect(self.__toggle_advanced)
        self.btn_progress_retry_all.clicked.connect(retry_all_failed_downloads)
        self.btn_search_download_all.clicked.connect(lambda x, cat="all": self.__mass_action_dl(cat))
        self.btn_progress_cancel_all.clicked.connect(cancel_all_downloads)
        self.btn_download_root_browse.clicked.connect(self.__select_dir)
        self.btn_search_download_tracks.clicked.connect(lambda x, cat="tracks": self.__mass_action_dl(cat))
        self.btn_search_download_albums.clicked.connect(lambda x, cat="albums": self.__mass_action_dl(cat))
        self.btn_search_download_artists.clicked.connect(lambda x, cat="artists": self.__mass_action_dl(cat))
        self.btn_progress_clear_complete.clicked.connect(self.rem_complete_from_table)
        self.btn_search_download_playlists.clicked.connect(lambda x, cat="playlists": self.__mass_action_dl(cat))

        # Connect checkbox state change signals
        self.inp_create_playlists.stateChanged.connect(self.__m3u_maker_set)
        self.inp_enable_spot_watch.stateChanged.connect(self.__media_watcher_set)

    def set_table_props(self):
        logger.info("Setting table item properties")
        # Sessions table
        tbl_sessions_header = self.tbl_sessions.horizontalHeader()
        tbl_sessions_header.setSectionResizeMode(0, QHeaderView.Stretch)
        tbl_sessions_header.setSectionResizeMode(1, QHeaderView.Stretch)
        tbl_sessions_header.setSectionResizeMode(2, QHeaderView.Stretch)
        tbl_sessions_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # Search results table
        tbl_search_results_headers = self.tbl_search_results.horizontalHeader()
        tbl_search_results_headers.setSectionResizeMode(0, QHeaderView.Stretch)
        tbl_search_results_headers.setSectionResizeMode(1, QHeaderView.Stretch)
        tbl_search_results_headers.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tbl_search_results_headers.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # Download progress table
        tbl_dl_progress_header = self.tbl_dl_progress.horizontalHeader()
        tbl_dl_progress_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        tbl_dl_progress_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        return True

    def __m3u_maker_set(self):
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
            self.__media_watcher.finished.connect(self.sig_media_track_end)
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

    def sig_media_track_end(self):
        logger.info("Watcher stopped")
        if self.inp_create_playlists.isChecked():
            self.inp_create_playlists.setChecked(False)

    def reset_app_config(self):
        config.rollback()
        self.__show_popup_dialog("The application setting was cleared successfully !\n Please restart the application.")

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

    def __show_popup_dialog(self, txt, btn_hide=False):
        self.__splash_dialog.lb_main.setText(str(txt))
        if btn_hide:
            self.__splash_dialog.btn_close.hide()
        else:
            self.__splash_dialog.btn_close.show()
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
        logger.info("Building downloader.py threads")
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
                    item[0].progress.connect(dl_progress_update)
                    item[1].start()
                    thread_pool.append(item)
            else:
                # Signal and wait for threads to terminate and clear pool and call sel
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

    def rem_complete_from_table(self):
        logger.info('Clearing complete downloads')
        complete_ids = []
        for dl_id in downloads_status.keys():
            try:
                logger.info(f"Checking download status for media id: {dl_id}, "
                            f"{downloads_status[dl_id]['progress_bar'].value()}")
                if downloads_status[dl_id]['progress_bar'].value() == 100 or \
                        downloads_status[dl_id]['status_label'].text().lower() == 'cancelled':
                    logger.info(f'ID: {dl_id} is complete or cancelled')
                    complete_ids.append(dl_id)
            except (RuntimeError, AttributeError):
                logger.info(f"Checking download status for media id: {dl_id}, Runtime error->Removing")
                complete_ids.append(dl_id)
        rows = self.tbl_dl_progress.rowCount()
        for i in range(rows):
            id_val = self.tbl_dl_progress.item(i, 0).text()
            if id_val in complete_ids:
                self.tbl_dl_progress.removeRow(i)
            downloads_status.pop(id_val)
