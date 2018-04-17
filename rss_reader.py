# packages

# own modules
import sql_feed_manager
import view
import sqlite3


db = sqlite3.connect(':memory:')

sql_feed_manager.create_tables(db)

db.close()

#feed_db = sqlite3.connect('feeds.db')
#
#
#feed_object = WebFeed()
#
#feed_web_data = download_rss_file()
#Atom_Insert(feed_web_data, feed_object)
#
#
#feed_disk_data = None
#feed_array = []