
# packages
import sqlite3
import requests

# own modules
import sql_feed_manager
import view as view_class
import settings as settings_class



# initialization
settings = settings_class.Settings("settings.json")
feed_manager = sql_feed_manager.FeedManager(settings)
view = view_class.View(feed_manager, settings)

#feed_manager.add_file_from_web("http://reddit.com/.rss")

# start program
view.console_ui()


# cleanup
feed_manager.cleanup()
settings.cleanup()
