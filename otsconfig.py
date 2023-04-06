import os
import json
import platform
import shutil
import sys
import time
from shutil import which


class Config:
    def __init__(self, cfg_path=None):
        if cfg_path is None:
            cfg_path = os.path.join(os.path.expanduser("~"), ".config", "casualOnTheSpot", "config.json")
        self.__cfg_path = cfg_path
        self.platform = platform.system()
        self.ext_ = ".exe" if self.platform == "Windows" else ""
        def_ff_path = os.path.dirname(os.path.abspath(which('ffmpeg'))) if which('ffmpeg') else ''
        self.__template_data = {
            "version": 0.4,
            "max_threads": 1,
            "parsing_acc_sn": 1,
            "download_root": os.path.join(os.path.expanduser("~"), "Music", "OnTheSpot"),
            "log_file": os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "logs", "onthespot.log"),
            "download_delay": 5,
            "track_name_formatter": "{artist} - {album} - {name}",
            "album_name_formatter": "{artist}" + os.path.sep + "[{rel_year}] {album}",
            "playlist_name_formatter": "MyPlaylists" + os.path.sep + "{name} by {owner}",
            "playlist_track_force_album_dir": 1,
            "watch_bg_for_spotify": 0,
            "dl_end_padding_bytes": 167,
            "max_retries": 3,
            "max_search_results": 10,
            "media_format": "mp3",
            "force_raw": False,
            "force_premium": False,
            "chunk_size": 50000,
            "ffmpeg_bin_dir": def_ff_path,
            "recoverable_fail_wait_delay": 10,
            "disable_bulk_dl_notices": True,
            "inp_enable_lyrics": True,
            "only_synced_lyrics": False,
            "create_m3u_playlists": False,
            "ffmpeg_args": "",
            "show_search_thumbails": 1,
            "search_thumb_height": 60,
            "accounts": []
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
        # Look up and try to fix ffmpeg issues
        if not os.path.isfile(os.path.join(self.get('ffmpeg_bin_dir'), 'ffmpeg' + self.ext_)):
            print('FFMPEG not found in default path: ', os.path.join(self.get('ffmpeg_bin_dir'), 'ffmpeg' + self.ext_))
            app_root = os.path.dirname(os.path.realpath(__file__))
            local_ff_path = os.path.join(app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)
            print('Trying to use local/embedded ffmpeg at: ', app_root)
            if os.path.isfile(local_ff_path):
                print('Using binaries at : ', local_ff_path)
                os.environ['PATH'] = os.path.dirname(local_ff_path) + os.pathsep + os.environ['PATH']
            else:
                print('Local ffmpeg not found at: ', local_ff_path)
        else:
            print('Using ffmpeg at :', os.path.join(self.get('ffmpeg_bin_dir'), 'ffmpeg' + self.ext_))

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

    def rollback(self):
        shutil.rmtree(os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "sessions"))
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__template_data))
        self.__config = self.__template_data


config = Config()
