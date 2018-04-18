# packages

# own modules
import sql_feed_manager
import view
import sqlite3
import requests



def download_rss_file():
    text_file = open("Output.xml", "w", encoding="utf-8")
    rss_request = requests.get("http://reddit.com/.rss")
    text_file.write(rss_request.text)
    return text_file

def load_rss_from_disk():
    with open("Output.xml", "rb") as text_file:
        rss = text_file.read().decode("utf-8")
        return rss

db = sqlite3.connect(':memory:')

sql_feed_manager.create_tables(db)

download_rss_file()
rss = load_rss_from_disk()

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