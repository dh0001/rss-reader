# packages
import sqlite3
import requests

# own modules
import sql_feed_manager as feeds
import view
import settings




settings.init()
feeds.init()
view.init()

db = sqlite3.connect(':memory:')

feeds.create_tables(db)
feeds.add_atom_file("http://reddit.com/.rss")

db.close()