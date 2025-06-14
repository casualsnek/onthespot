import os
import json
import platform
import shutil
from shutil import which
import uuid


class Config:
    def __init__(self, cfg_path=None):
        if cfg_path is None or not os.path.isfile(cfg_path):
            cfg_path = os.path.join(os.path.expanduser("~"), ".config", "casualOnTheSpot", "config.json")
        self.__cfg_path = cfg_path
        self.platform = platform.system()
        self.ext_ = ".exe" if self.platform == "Windows" else ""
        self.version = 0.5
        self.session_uuid = str(uuid.uuid4())
        print('OTS Version : ', self.version)
        self.__template_data = {
            "version": 0.5, # Application version
            "max_threads": 1, # Maximum number of thread we can spawn
            "parsing_acc_sn": 1, # Serial number of account that will be used for parsing links
            "download_root": os.path.join(os.path.expanduser("~"), "Music", "OnTheSpot"), # Root dir for downloads
            "download_delay": 5, # Seconds to wait before next download
            "track_name_formatter": "{artist} - {album} - {name}", # Track name format string
            "album_name_formatter": "{artist}" + os.path.sep + "[{rel_year}] {album}", # Album name format string
            "playlist_name_formatter": "MyPlaylists" + os.path.sep + "{name} by {owner}", # Playlist name format string
            "playlist_track_force_album_dir": 1, # Use album directory format for tracks
            "watch_bg_for_spotify": 0, # Detect songs playing on spotify desktop client and automatically download the,
            "dl_end_padding_bytes": 167,
            "max_retries": 3, # Number of times to retry before giving up on download
            "max_search_results": 10, # Number of search results to display of each type
            "media_format": "mp3", # Song track media format
            "podcast_media_format": "mp3", # Podcast track media format
            "force_raw": False, # Skip media conversion and metadata writing
            "force_premium": False, # Set premium flag to always return true
            "chunk_size": 50000, # Chunk size in bytes to download in
            "recoverable_fail_wait_delay": 10, # No of seconds to wait before failure that can be retried
            "disable_bulk_dl_notices": True, # Hide popups for bulk download buttons
            "inp_enable_lyrics": True, # Enable lyrics download
            "only_synced_lyrics": False, # Only use synced lyrics
            "create_m3u_playlists": False, # Create m3u based playlist
            "ffmpeg_args": [], # Extra arguments for ffmpeg
            "show_search_thumbnails": 1, # Show thumbnails in search view
            "search_thumb_height": 60, # Thumbnail height ( they are of equal width and height )
            "metadata_seperator": ";", # Seperator used for metadata fields that have multiple values
            "accounts": [], # Saved account information
            "theme": "Light" # Light\Dark
        }
        if os.path.isfile(self.__cfg_path):
            self.__config = json.load(open(cfg_path, "r"))
        else:
            try:
                os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
            except (FileNotFoundError, PermissionError):
                fallback_path = os.path.abspath(
                    os.path.join('.config', 'config.json')
                    )
                print(
                    'Critical error.. Configuration file could not be '
                    'created at "{self.__cfg_path}"; Trying : {fallback_path}'
                    )
                self.__cfg_path = fallback_path
                os.makedirs(os.path.dirname(self.__cfg_path), exist_ok=True)
            with open(self.__cfg_path, "w") as cf:
                cf.write(json.dumps(self.__template_data, indent=4))
            self.__config = self.__template_data
        self.__run_migration()
        print('Config version: ', self.__config['version'])
        try:
            os.makedirs(self.get("download_root"), exist_ok=True)
        except (FileNotFoundError, PermissionError):
            print(
                'Current download root cannot be set up at "',
                self.get("download_root"),
                '"; Falling back to : ',
                self.__template_data.get('download_root')
                )
            self.set_(
                'download_root', self.__template_data.get('download_root')
                )
            os.makedirs(self.get("download_root"), exist_ok=True)
        # Set ffmpeg path
        self.app_root = os.path.dirname(os.path.realpath(__file__))
        if os.path.isfile(os.path.join(self.app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)):
            # Try embedded binary at first
            print('FFMPEG found in package !')
            self.set_('_ffmpeg_bin_path',
                      os.path.abspath(os.path.join(self.app_root, 'bin', 'ffmpeg', 'ffmpeg' + self.ext_)))
        elif os.path.isfile(os.path.join(self.get('ffmpeg_bin_dir', '.'), 'ffmpeg' + self.ext_)):
            # Now try user defined binary path
            print('FFMPEG found at config:ffmpeg_bin_dir !')
            self.set_('_ffmpeg_bin_path',
                      os.path.abspath(os.path.join(self.get('ffmpeg_bin_dir', '.'), 'ffmpeg' + self.ext_)))
        else:
            # Try system binaries as fallback
            print('Attempting to use system ffmpeg binary !')
            self.set_('_ffmpeg_bin_path', os.path.abspath(which('ffmpeg')) if which('ffmpeg') else 'ffmpeg' + self.ext_)
        print("Using ffmpeg binary at: ", self.get('_ffmpeg_bin_path'))
        self.set_('_log_file', os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "logs", self.session_uuid, "onthespot.log"))
        self.set_('_cache_dir', os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot"))
        try:
            os.makedirs(
                os.path.dirname(self.get("_log_file")), exist_ok=True
                )
        except (FileNotFoundError, PermissionError):
            fallback_logdir = os.path.abspath(os.path.join(
                ".logs", self.session_uuid, "onthespot.log"
                )
            )
            print(
                'Current logging dir cannot be set up at "',
                self.get("download_root"),
                '"; Falling back to : ',
                fallback_logdir
                )
            self.set_('_log_file', fallback_logdir)
            os.makedirs(
                os.path.dirname(self.get("_log_file")), exist_ok=True
                )

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
        for key in list(set(self.__template_data).difference(set(self.__config))):
            if not key.startswith('_'):
                self.set_(key, self.__template_data[key])
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__config, indent=4))

    def rollback(self):
        shutil.rmtree(os.path.join(os.path.expanduser("~"), ".cache", "casualOnTheSpot", "sessions"))
        with open(self.__cfg_path, "w") as cf:
            cf.write(json.dumps(self.__template_data, indent=4))
        self.__config = self.__template_data

    def __run_migration(self):
        while self.get('version') < self.version:
            # Migrate v0.4 to v0.5
            if self.get('version') == 0.4:
                print('Curent Config version : ', 0.4)
                accounts = self.__config['accounts'].copy()
                new_accounts = []
                for account in accounts:
                    # Assign UUID
                    acc_uuid = str(uuid.uuid4())
                    session_dir = os.path.join(os.path.expanduser('~'), '.cache', 'casualOnTheSpot', 'sessions')
                    new_accounts.append([account[0], account[1], account[2], acc_uuid])
                    # Move saved sessions
                    try:
                        os.rename(
                            os.path.join(session_dir, f"{account[0]}_GUZpotifylogin.json"),
                            os.path.join(session_dir, f"ots_login_{acc_uuid}.json")
                        )
                    except:
                        print('Sessions could not be moved')
                self.set_('accounts', new_accounts)
                self.set_('version', 0.5)
                print('Config migrated to version : ', 0.5)
                self.update()


config = Config()
