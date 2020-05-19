import json
import os.path
import logging

from shutil import copyfile

settings = {}
_settings_file = "settings.json"
_default_settings_file = "defaultsettings.json"


def init_settings():

    if not os.path.exists(_settings_file):
        copyfile(_default_settings_file, _settings_file)

    try:
        with open(_settings_file, "rb") as f:
            global settings
            s = f.read().decode("utf-8")
            settings.update(json.loads(s))
    except OSError as e:
        logging.exception("Error reading settings file!")
        raise e


def save_settings():
    """Outputs settings to file."""
    with open (_settings_file, "w") as f:
        f.write(json.dumps(settings, indent=4))
