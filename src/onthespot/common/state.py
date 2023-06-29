import os
from typing import Union

CANCEL_LIST: list[str] = []

DOWNLOAD_QUEUE: list = []

TRANSCODE_QUEUE: list[os.PathLike] = []

SUCCESS_LIST: list[str] = []

# [Session, Premium, Status, UUID]
SESSION_POOL: list[list['Session', bool, bool, str]] = []