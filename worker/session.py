import os
import time
from PyQt5.QtCore import QObject, pyqtSignal
from otsconfig import config
from runtimedata import session_pool, get_logger
from utils.utils import login_user

logger = get_logger("worker.session")


class LoadSessions(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str, bool)
    __users = None

    def run(self):
        logger.info('Session loader has started !')
        accounts = config.get('accounts')
        t = len(accounts)
        c = 0
        for account in accounts:
            c = c + 1
            logger.info(f'Trying to create session for {account[0][:4]}')
            self.progress.emit(f'Attempting to create session for:\n{account[0]}  [{c}/{t}] ', True)
            time.sleep(0.2)
            login = login_user(account[0], "",
                               os.path.join(os.path.expanduser('~'), '.cache', 'casualOnTheSpot', 'sessions'))
            if login[0]:
                # Login was successful, add to session pool
                self.progress.emit(f'Session created for:\n{account[0]}  [{c}/{t}] ', True)
                time.sleep(0.2)
                session_pool.append(login[1])
                self.__users.append([account[0], 'Premium' if login[3] else 'Free', 'OK'])
            else:
                self.progress.emit(f'Failed to create session for:\n{account[0]}  [{c}/{t}] ', True)
                self.__users.append([account[0], "LoginERROR", "ERROR"])
        self.finished.emit()

    def setup(self, users):
        self.__users = users
