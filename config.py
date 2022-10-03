import os
import json


class Config:
    def __init__(self, cfg_path=None):
        if cfg_path is None:
            cfg_path = config_file_path = os.path.join(os.path.expanduser("~"), ".config", "casualOnTheSpot", "config.json")
        self.__cfg_path = cfg_path
        self.__template_data = {
            "max_threads": 1,
            "parsing_acc_sn": 1,
            "download_root": os.path.join(os.path.expanduser("~"), "Music", "OnTheSpot"),
            "log_file": os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "logs", "onthespot.log"),
            "download_delay": 5,
            "track_name_formatter": "{artist} - {album} - {name}",
            "album_name_formatter": "{artist}/[{rel_year}] {album}",
            "playlist_track_force_album_dir": 1,
            "dl_end_padding_bytes": 167,
            "max_retries": 3,
            "max_search_results": 10,
            "media_format": "mp3",
            "force_raw": False,
            "force_premium": False,
            "chunk_size": 50000,
            "recoverable_fail_wait_delay": 10,
            "disable_bulk_dl_notices": True,
            "accounts": [  ]
        }
        if os.path.isfile(self.__cfg_path):
            self.__config = json.load(open(cfg_path, "r"))
        else:
            os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
            with open(self.__cfg_path, "w") as cf:
                cf.write(json.dumps(self.__template_data))
            self.__config = self.__template_data
        os.makedirs(self.get("download_root"), exist_ok=True)
        os.makedirs(os.path.dirname(self.get("log_file")), exist_ok=True)

    def get(self, key, default=None):
        if key in self.__config:
            return self.__config[key]
        elif key in self.__template_data:
            return self.__template_data[key]
        else:
            return default

    def set_(self, key, value):
        if type(value) in [list, dict]:
            self.__config[key] = value.copy()
        else:
            self.__config[key] = value
        return value

    def update(self):
        os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__config))

config = Config()