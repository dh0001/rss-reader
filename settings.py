import json
import os.path
import logging

from shutil import copyfile, move
from typing import Any


_settings_file = "settings.json"
_writing_settings_file = "temp_settings"
_default_settings_file = "defaultsettings.json"


class Settings():

    def __init__(self):
        """Initializes settings for the application.

        Creates a settings file if it does not exist.
        """

        if not os.path.exists(_settings_file):
            copyfile(_default_settings_file, _settings_file)

        try:
            with open(_settings_file, "rb") as settings_file:
                contents = settings_file.read().decode("utf-8")
                settings = json.loads(contents)

        except OSError as error:
            logging.exception("Error reading settings file!")
            raise error

        self.db_file: str = settings["db_file"]
        self.refresh_time: int = settings["refresh_time"]
        self.default_delete_time: int = settings["default_delete_time"]
        self.global_refresh_rate: int = settings["global_refresh_rate"]
        self.feed_counter: int = settings["feed_counter"]
        self.font_size: int = settings["font_size"]
        self.startup_update: bool = settings["startup_update"]
        self.geometry: str = settings["geometry"]
        self.splitter1: str = settings["splitter1"]
        self.splitter2: str = settings["splitter2"]
        self.article_view_headers: str = settings["article_view_headers"]
        self.feed_view_headers: str = settings["feed_view_headers"]
        self.state: str = settings["state"]


    def __setattr__(self, name: str, value: Any):
        super().__setattr__(name, value)
        self.save_settings()


    def save_settings(self):
        """Outputs settings to file."""
        value = json.dumps(vars(self), indent=4)
        with open(_writing_settings_file, "w") as settings_file:
            settings_file.write(value)
        move(_writing_settings_file, _settings_file)


settings = Settings()
