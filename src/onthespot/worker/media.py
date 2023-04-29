import queue
import time
from PyQt5.QtCore import QObject, pyqtSignal
from urllib3.exceptions import NewConnectionError, MaxRetryError

from ..otsconfig import config
from ..runtimedata import session_pool, get_logger
from ..utils.utils import get_now_playing_local, re_init_session

logger = get_logger("worker.media")


class MediaWatcher(QObject):
    changed_media = pyqtSignal(str, bool)
    finished = pyqtSignal()
    last_url = ''
    __stop = False

    def run(self):
        logger.info('Media watcher thread is running....')
        while not self.__stop:
            try:
                selected_uuid = config.get('accounts')[config.get('parsing_acc_sn') - 1][3]
                session = session_pool[selected_uuid]
                spotify_url = get_now_playing_local(session)
                spotify_url = spotify_url.strip() if spotify_url is not None else ""
                if spotify_url != '' and spotify_url != self.last_url:
                    logger.info(f'Desktop application media changed to: {spotify_url}')
                    self.last_url = spotify_url
                    self.changed_media.emit(spotify_url, True)
                time.sleep(3)
            except FileNotFoundError:
                logger.error('Background monitor failed ! Playerctl not installed')
                break
            except (IndexError, KeyError):
                logger.warning("Sessions not available yet !")
                time.sleep(5)
            except (OSError, queue.Empty, MaxRetryError, NewConnectionError, ConnectionError):
                # Internet disconnected ?
                logger.error('Search failed Connection error ! Trying to re init parsing account session ! ')
                re_init_session(session_pool, selected_uuid, wait_connectivity=True, timeout=30)
        self.finished.emit()

    def stop(self):
        self.__stop = True
