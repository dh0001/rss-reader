import sqlite3
import requests
import defusedxml.ElementTree as EleTree
import feed as feedutility
import sched


class FeedManager():

    def __init__(self, settings):
        self.feeds = []
        self.settings = settings
        self.connection = sqlite3.connect(settings.settings["db_file"])
        #self.create_tables()
        self.read_feeds_from_database()

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


    def add_feed_to_database(self, feed:feedutility.WebFeed):
        c = self.connection.cursor()

        # add entry to feeds
        c.execute('''INSERT INTO feeds
            VALUES (? ? ? ? ? ? ? ? ?)''', feed.uri, feed.title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon, feed.subtitle, feed.feed_meta)
        id = c.lastrowid
        #####

        # add articles to entries
        entries = []
        for article in feed.articles:
            entries.append((id, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published, 3))
        #####

        c.executemany('''INSERT INTO entries
            VALUES (? ? ? ? ? ? ? ? ?)''', entries)
        self.connection.commit()


    # read data from database
    def read_feeds_from_database(self):
        c = self.connection.cursor()

        new_feed = feedutility.WebFeed()
        for feed in c.execute('''SELECT * FROM feeds'''):
            new_feed.author = feed[0]
        
        self.feeds.append(new_feed)


    # add feed data to database.
    def _add_atom_file(self, data):
        new_feed = feedutility.WebFeed()
        feedutility.atom_insert(EleTree.fromstring(data), new_feed)
        self.feeds.append(new_feed)


    # add new feed to database from disk.
    def add_file_from_disk(self, location):
        data = load_rss_from_disk(location)
        self._add_atom_file(data)


    # add new feed to database from web.
    def add_file_from_web(self, file):
        data = download_file(file)
        self._add_atom_file(data)


    # returns all the feeds in the database.
    def get_feeds(self):
        return self.feeds


    # refresh all feeds in the database.
    def refresh(self):
        for feed in self.feeds:
            refresh_feed(feed)

    # removes a feed from the database.
    def delete_feed(self):
        return

    
 
# HTTP GET request for file, with headers indicating application.
def download_file(uri):
    headers = {'User-Agent' : 'python-rss-reader-side-project'}
    return requests.get(uri, headers=headers).text

def write_string_to_file(str):
    text_file = open("Output.xml", "w", encoding="utf-8")
    text_file.write(str)
    return

def load_rss_from_disk(f):
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss


# refresh data in feed.  Does not clear existing data.
def refresh_feed(feed:feedutility.WebFeed):
    data = download_file(feed.uri)
    feedutility.atom_insert(EleTree.fromstring(data), feed)