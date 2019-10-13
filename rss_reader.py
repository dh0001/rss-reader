# packages
import sqlite3
import requests
import PySide2.QtWidgets as qtw

# own modules
import feed_manager
import view as view_class
import settings as settings_class


# initialization
app = qtw.QApplication([])

settings = settings_class.Settings("settings.json")
feed_manager = feed_manager.FeedManager(settings)
view = view_class.View(feed_manager, settings)


# start program
# view.refresh_all()
app.exec_()


# cleanup
feed_manager.cleanup()
view.cleanup()
settings.cleanup()
