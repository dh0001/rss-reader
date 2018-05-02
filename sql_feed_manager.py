import sqlite3
import requests
import defusedxml.ElementTree as EleTree
import feed


class FeedManager():

    feeds = None

    def __init__(self):
        self.feeds = []

    def create_tables(self, connection):
        c = connection.cursor()
        c.execute('''CREATE TABLE feeds (
            uri TEXT,
            title TEXT
            author TEXT,
            author_uri TEXT,
            category TEXT,
            updated INTEGER,
            icon_uri TEXT,
            subtitle TEXT,
            feed_meta TEXT)''')
        c.execute('''CREATE TABLE entries (
            feed_id INTEGER,
            uri TEXT
            title TEXT,
            updated INTEGER,
            author TEXT,
            author_uri TEXT,
            content TEXT,
            published INTEGER)''')
        connection.commit()

    def init(self):
        return

    def add_atom_file(self, file):
        data = download_rss_file(file)
        feed.atom_insert(EleTree.fromstring(data), self.feeds)

    def add_file_from_disk(self, location):
        data = load_rss_from_disk(location)
        new_feed = feed.WebFeed()
        feed.atom_insert(EleTree.fromstring(data), new_feed)
        self.feeds.append(new_feed)

    def get_feeds(self):
        return self.feeds
 
 
def download_rss_file(uri):
    return requests.get(uri)

def write_string_to_file(str):
    text_file = open("Output.xml", "w", encoding="utf-8")
    text_file.write(str)
    return

def load_rss_from_disk(f):
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss