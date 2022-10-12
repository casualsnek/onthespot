import time
from PyQt5.QtCore import QObject, pyqtSignal
from otsconfig import config
from runtimedata import session_pool, get_logger
from utils.utils import get_now_playing_local

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
                session = session_pool[config.get("parsing_acc_sn") - 1]
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
            except IndexError:
                logger.warning("Sessions not available yet !")
                time.sleep(5)
        self.finished.emit()

    def stop(self):
        self.__stop = True
