import json
import os.path
import shutil
from os import PathLike
import logging
from typing import Any, Callable, Tuple


class ConfigurationService:

    DEFAULT: dict[str, Any] = {
        "version": "1.0.0",
        "max_concurrent_sessions_use": 5,
        "max_concurrent_transcoders": 5,
        "download_directory": os.path.join(os.path.expanduser("~"), "Music"),
        "file_name_format": "{artist} - {title}",
        "target_format": "mp3",
        "ffmpeg_path": shutil.which("ffmpeg") if shutil.which("ffmpeg") else "ffmpeg",
        "embed_metadata": True,
        "download_synced_lyrics": True,
        "download_unsynced_art": True,
        "max_retries": 3,
        "enable_m3u_playlist": True,
        "m3u_playlist_directory": os.path.join(os.path.expanduser("~"), "Music", "Playlists"),  # TODO: Allow custom formatter for Meu files
        "m3u_playlist_formatter": "{playlist_name} by {author_name)", #TODO: Use valid formatter by default
        "use_alternate_formatter_for_playlist": False,
        "playlist_alternate_formatter": "{artist} - {title}",
        "download_chunk_size": 1024,
        "ffmpeg_extra_args": "",
        "preferred_parsing_account": None,
        "skip_bytes_at_the_end": 167,
        "nowplaying_auto_download": False,
        "raw_download_enabled": False,
        "DEBUG_FORCE_OTSLIB_MEDIA_STREAM": False,
        "audio_tags_seperator": ";",
        "accounts": {
                # "uuid": {
                #       "username": "username",
                #       "session_path": "/path/to/session",
                #   }
        },

    }
    
    def __init__(self, config_path: str | PathLike):
        self.__config_path = config_path
        self.__config: None | dict[str, Any] = None
        self.__onchange_handlers: dict[str, list[Callable]] = {}
        if not os.path.isfile(config_path):
            logging.warn(f"Creating default config at \"{config_path}\"")
            with open(config_path, "w") as cfp:
                cfp.write(json.dumps(ConfigurationService.DEFAULT))
        self.reload()
        logging.info(f"Config loaded from \"{config_path}\"")

    def get(self, key: str, default: Any = None) -> str|Any:
        return self.__config[key] if key in self.__config else ConfigurationService.DEFAULT[key]

    def set(self, key: str, new_value: Any) -> Tuple[str, Any]:
        old_value = self.__config.get(key)
        # Trigger on change event handlers
        if key in self.__onchange_handlers and old_value != new_value:
            for handler in self.__onchange_handlers[key]:
                handler(key, old_value, new_value)
        self.__config[key] = new_value
        return key, self.__config[key]

    def on_change(self, key: str, handler: Callable) -> None:
        if key not in self.__onchange_handlers:
            self.__onchange_handlers[key] = []
        if handler not in self.__onchange_handlers[key]:
            self.__onchange_handlers[key].append(handler)

    def remove_on_change(self, key: str, handler: Callable) -> None:
        if key in self.__onchange_handlers and handler in self.__onchange_handlers[key]:
            self.__onchange_handlers[key].remove(handler)

    def save(self):
        with open(self.__config_path, "w") as cfp:
            cfp.write(json.dumps(self.__config))

    def reload(self):
        with open(self.__config_path, "r") as cfp:
            self.__config = json.loads(cfp.read())
        logging.info(f"Config reloaded from \"{self.__config_path}\"")