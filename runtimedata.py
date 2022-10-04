from queue import Empty, Queue
import logging
from config import config
import logging
import sys, os
import logging
from logging.handlers import RotatingFileHandler


log_formatter = logging.Formatter('[%(asctime)s :: %(pathname)s -> %(lineno)s:%(funcName)20s() :: %(levelname)s] -> %(message)s')
log_handler = RotatingFileHandler(config.get("log_file"), mode='a', maxBytes=5*1024*1024,
                                 backupCount=2, encoding=None, delay=0)
stdout_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)
download_queue = Queue()
thread_pool = []
session_pool = []
loglevel = int(os.environ.get("LOGLEVEL", 20))
def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(log_handler)
    logger.addHandler(stdout_handler)
    logger.setLevel(loglevel)
    return logger

logger_ = get_logger("runtimedata")
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger_.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception