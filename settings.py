import json
import os.path

from shutil import copyfile

class Settings():
    
    def __init__(self, file: str):
        self.settings : dict
        self._settings_file = file

        if not os.path.exists(self.settings_file):
            copyfile("defaultsettings.json", self.settings_file)

        with open(file, "rb") as f:
            s = f.read().decode("utf-8")
            self.settings = json.loads(s)


    def cleanup(self) -> None:
        """
        Outputs settings to file.
        """
        with open (self._settings_file, "w") as f:
            f.write(json.dumps(self.settings, indent=4))