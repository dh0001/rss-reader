# packages
import sqlite3
import requests

# own modules
import sql_feed_manager as feeds
import view
import settings



def download_rss_file():
    text_file = open("Output.xml", "w", encoding="utf-8")
    rss_request = requests.get("http://reddit.com/.rss")
    text_file.write(rss_request.text)
    return text_file

def load_rss_from_disk(f):
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss


settings.init()

db = sqlite3.connect(':memory:')

feeds.create_tables(db)
feeds.()

# download_rss_file()
rss = load_rss_from_disk("Output.xml")




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