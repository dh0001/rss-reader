
# packages
import sqlite3
import requests

# own modules
import sql_feed_manager
import view as view_class
import settings as settings_class




settings = settings_class.Settings("abc")

feed_manager = sql_feed_manager.FeedManager(settings)

view = view_class.View(feed_manager)


feed_manager.create_tables()
feed_manager.add_file_from_disk("Output.xml")
view.std_output()