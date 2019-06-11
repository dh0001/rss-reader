# packages
import sqlite3
import requests

# own modules
import feed_manager
import view as view_class
import settings as settings_class


# initialization
settings = settings_class.Settings("settings.json")
feed_manager = feed_manager.FeedManager(settings)
view = view_class.View(feed_manager, settings)


# start program
view.gui()


# cleanup
feed_manager.cleanup()
view.cleanup()
settings.cleanup()
