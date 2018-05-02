
# packages
import sqlite3
import requests

# own modules
import sql_feed_manager
import view as view_class
import settings as settings_class




settings = settings_class.Settings()
feed_manager = sql_feed_manager.FeedManager()
view = view_class.View(feed_manager)


db = sqlite3.connect(':memory:')

feed_manager.create_tables(db)
feed_manager.add_file_from_disk("Output.xml")
view.output()

db.close()