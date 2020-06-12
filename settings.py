import json
import os.path
import logging

from shutil import copyfile

settings = {}
_settings_file = "settings.json"
_default_settings_file = "defaultsettings.json"


def init_settings():
    """Initializes settings for the application.

    Creates a settings file if it does not exist.
    """
    if not os.path.exists(_settings_file):
        copyfile(_default_settings_file, _settings_file)

    try:
        with open(_settings_file, "rb") as settings_file:
            global settings
            contents = settings_file.read().decode("utf-8")
            settings.update(json.loads(contents))
    except OSError as error:
        logging.exception("Error reading settings file!")
        raise error


def save_settings():
    """Outputs settings to file."""
    with open(_settings_file, "w") as settings_file:
        settings_file.write(json.dumps(settings, indent=4))
