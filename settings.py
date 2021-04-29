import json
import os.path
import logging

from shutil import copyfile

_settings_file = "settings.json"
_default_settings_file = "defaultsettings.json"


class Settings():
    def __init__(self):
        """Initializes settings for the application.

        Creates a settings file if it does not exist.
        """
        self.settings = {}

        if not os.path.exists(_settings_file):
            copyfile(_default_settings_file, _settings_file)

        try:
            with open(_settings_file, "rb") as settings_file:
                contents = settings_file.read().decode("utf-8")
                self.settings.update(json.loads(contents))
        except OSError as error:
            logging.exception("Error reading settings file!")
            raise error


    def __getitem__(self, key):
        return self.settings[key]


    def __setitem__(self, key, value):
        self.settings[key] = value
        self.save_settings()


    def save_settings(self):
        """Outputs settings to file."""
        with open(_settings_file, "w") as settings_file:
            settings_file.write(json.dumps(self.settings, indent=4))


settings = Settings()
