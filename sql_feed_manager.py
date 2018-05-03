import sqlite3
import requests
import defusedxml.ElementTree as EleTree
import feed


class FeedManager():

    def __init__(self, settings):
        self.feeds = []
        self.settings = settings
        self.connection = sqlite3.connect(settings.db_file)

    def cleanup(self):
        self.connection.close()

    # create tables in sql
    def create_tables(self):
        c = self.connection.cursor()
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
        self.connection.commit()


    def add_feed_to_database(self, feed:feed.WebFeed):
        c = self.connection.cursor()

        # add entry to feeds
        c.execute('''INSERT INTO feeds
            VALUES (? ? ? ? ? ? ? ? ?)''', feed.uri, feed.title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon, feed.subtitle, feed.feed_meta)
        id = c.lastrowid

        # add articles to entries
        entries = []
        for article in feed.articles:
            entries.append((id, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published, 3))

        c.executemany('''INSERT INTO entries
            VALUES (? ? ? ? ? ? ? ? ?)''', entries)

    # add 
    def add_atom_file(self, data):
        new_feed = feed.WebFeed()
        feed.atom_insert(EleTree.fromstring(data), new_feed)
        self.feeds.append(new_feed)

    # add new feed to feeds from disk.
    def add_file_from_disk(self, location):
        data = load_rss_from_disk(location)
        self.add_atom_file(data)


    # add new feed to feeds from web.
    def add_file_from_web(self, file):
        data = download_rss_file(file)
        self.add_atom_file(data)


    # returns the feeds array.
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


# 
def refresh_feed(feed:feed.WebFeed):
    return