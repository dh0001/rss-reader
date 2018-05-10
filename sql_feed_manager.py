import sqlite3
import requests
import defusedxml.ElementTree as EleTree
import feed as feedutility
import sched


class FeedManager():

    def __init__(self, settings):
        """
        initialization.
        """
        self.settings = settings
        self.connection = sqlite3.connect(settings.settings["db_file"])

        if self.settings.settings["first-run"] == "true":
            self.create_tables()


    def cleanup(self):
        """
        Should be called to clean up.
        """
        self.connection.close()


    def create_tables(self):
        """
        Creates all the tables used in rss-reader.
        """
        c = self.connection.cursor()
        c.execute('''CREATE TABLE feeds (
            uri TEXT,
            title TEXT,
            author TEXT,
            author_uri TEXT,
            category TEXT,
            updated INTEGER,
            icon_uri TEXT,
            subtitle TEXT,
            feed_meta TEXT)''')
        c.execute('''CREATE TABLE entries (
            feed_id INTEGER,
            uri TEXT,
            title TEXT,
            updated INTEGER,
            author TEXT,
            author_uri TEXT,
            content TEXT,
            published INTEGER)''')
        self.connection.commit()


    def _add_feed_to_database(self, feed:feedutility.WebFeed) -> int:
        """
        Add a feed entry into the database. Returns the row id of the inserted entry.
        """
        c = self.connection.cursor()
        c.execute('''INSERT INTO feeds
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', [feed.uri, feed.title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon, feed.subtitle, feed.feed_meta])
        self.connection.commit()
        return c.lastrowid


    def _add_articles_to_database(self, articles, id):
        """
        Add multiple articles to database. articles should be a list.
        """
        c = self.connection.cursor()
        entries = []
        for article in articles:
            entries.append((id, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published))
        c.executemany('''INSERT INTO entries
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', entries)
        self.connection.commit()


    def _read_feeds_from_database(self):
        """
        Returns a list containing all the feeds in the database.
        """
        c = self.connection.cursor()
        feeds = []
        for feed in c.execute('''SELECT * FROM feeds'''):
            new_feed = feedutility.WebFeed()
            new_feed.uri = feed[0]
            new_feed.title = feed[1]
            new_feed.author = feed[2]
            new_feed.author_uri = feed[3]
            new_feed.category = feed[4]
            new_feed.updated = feed[5]
            feeds.append(new_feed)
        return feeds


    def _read_articles_from_database(self, id):
        """
        Returns a list containing all the articles with feed_id "id".
        """
        c = self.connection.cursor()
        articles = []
        for article in c.execute('''SELECT * FROM articles WHERE feed_id = ?''', id):
            new_article = feedutility.Article()
            new_article.title = article[1]
            articles.append(new_article)
        return articles


    def _add_atom_file(self, data, location):
        """
        Add atom feed data to database.
        """
        new_feed = feedutility.WebFeed()
        new_articles = []
        feedutility.atom_insert(EleTree.fromstring(data), new_feed)
        new_feed.uri = location
        id = self._add_feed_to_database(new_feed)
        self._add_articles_to_database(new_articles, id)


    def add_file_from_disk(self, location):
        """
        add new feed to database from disk.
        """
        data = load_rss_from_disk(location)
        self._add_atom_file(data, location)


    def add_feed_from_web(self, file):
        """
        add new feed to database from web.
        """
        data = download_file(file)
        self._add_atom_file(data, file)


    def get_feeds(self):
        """
        returns all the feeds in the database.
        """
        return self._read_feeds_from_database()


    def refresh(self):
        """
        refresh all feeds in the database.
        """
        return

    def delete_feed(self):
        """
        removes a feed from the database.
        """
        return

    
def download_file(uri):
    """
    HTTP GET request for file, with headers indicating application.
    """
    headers = {'User-Agent' : 'python-rss-reader-side-project'}
    return requests.get(uri, headers=headers).text

def write_string_to_file(str):
    """
    Write string to a file Output.xml.
    """
    text_file = open("Output.xml", "w", encoding="utf-8")
    text_file.write(str)
    return

def load_rss_from_disk(f):
    """
    Returns content in file "f".
    """
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss


def refresh_feed(feed:feedutility.WebFeed):
    """
    Refresh data in feed. Does not clear existing data.
    """
    data = download_file(feed.uri)
    feedutility.atom_insert(EleTree.fromstring(data), feed)