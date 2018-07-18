import sqlite3
import requests
import defusedxml.ElementTree as defusxml
import feed as feedutility
import sched
import datetime
import dateutil.parser
import time
import threading
from typing import List


class FeedManager():

    def __init__(self, settings):
        """
        initialization.
        """
        self.settings = settings
        self.connection = sqlite3.connect(settings.settings["db_file"], check_same_thread=False)

        if self.settings.settings["first-run"] == "true":
            self.create_tables()
            self.settings.settings["first-run"] == "false"

        self.db_lock = threading._allocate_lock()
        
        self.refresh_schedule = sched.scheduler(time.time, time.sleep)
        self.refresh_schedule.enter(settings.settings["refresh_time"], 1, self.scheduled_refresh)
        self.refresh_schedule_thread = threading.Thread(target = self.refresh_schedule.run, daemon=True).start()


    def cleanup(self) -> None:
        """
        Should be called before program exit.
        """
        self.connection.close()


    def create_tables(self) -> None:
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
        c.execute('''CREATE TABLE articles (
            feed_id INTEGER,
            uri TEXT,
            title TEXT,
            updated INTEGER,
            author TEXT,
            author_uri TEXT,
            content TEXT,
            published INTEGER,
            unread INTEGER)''')
        self.connection.commit()


    def _add_feed_to_database(self, feed:feedutility.WebFeed) -> int:
        """
        Add a feed entry into the database. Returns the row id of the inserted entry.
        """
        c = self.connection.cursor()
        c.execute('''INSERT INTO feeds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            [feed.uri, feed.title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon, feed.subtitle, feed.feed_meta])
        self.connection.commit()
        return c.lastrowid


    def _add_articles_to_database(self, articles: List[feedutility.Article], feed_id: int) -> None:
        """
        Add multiple articles to database. articles should be a list.
        """
        c = self.connection.cursor()
        entries = []
        for article in articles:
            entries.append((feed_id, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published, 1))
        c.executemany('''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', entries)
        self.connection.commit()


    def _read_feeds_from_database(self) -> List[feedutility.WebFeed]:
        """
        Returns a list containing all the feeds in the database.
        """
        c = self.connection.cursor()
        feeds = []
        for feed in c.execute('''SELECT rowid, * FROM feeds'''):
            new_feed = feedutility.WebFeed()
            new_feed.db_id = feed[0]
            new_feed.uri = feed[1]
            new_feed.title = feed[2]
            new_feed.author = feed[3]
            new_feed.author_uri = feed[4]
            new_feed.category = feed[5]
            new_feed.updated = feed[6]
            feeds.append(new_feed)
        return feeds


    def get_articles(self, feed_id: int) -> List[feedutility.Article]:
        """
        Returns a list containing all the articles with feed_id "id".
        """
        c = self.connection.cursor()
        articles = []
        for article in c.execute('''SELECT rowid, * FROM articles WHERE feed_id = ?''', [feed_id]):
            return_article = feedutility.Article()
            return_article.db_id = article[0]
            return_article.feed_id = article[1]
            return_article.uri = article[2]
            return_article.title = article[3]
            return_article.updated = article[4]
            return_article.author = article[5]
            return_article.author_uri = article[6]
            return_article.content = article[7]
            return_article.unread = article[9]
            articles.append(return_article)
        return articles


    def _add_atom_file(self, data, location) -> None:
        """
        Add atom feed data to database.
        """
        output = feedutility.atom_parse(data)
        new_articles = output.articles
        new_feed = output.feed
        new_feed.uri = location
        row_id = self._add_feed_to_database(new_feed)
        self._add_articles_to_database(new_articles, row_id)


    def add_file_from_disk(self, location) -> None:
        """
        add new feed to database from disk.
        """
        data = load_rss_from_disk(location)
        self._add_atom_file(data, location)


    def add_feed_from_web(self, file) -> None:
        """
        add new feed to database from web.
        """
        data = _download_xml(file)
        self._add_atom_file(data, file)


    def get_all_feeds(self) -> List[feedutility.WebFeed]:
        """
        returns all the feeds in the database.
        """
        return self._read_feeds_from_database()


    def _update_feed(self, feed: feedutility.WebFeed) -> None:
        """
        Update the corresponding feed in the database. Uses db_id to find the database entry.
        """
        c = self.connection.cursor()
        c.execute('''UPDATE feeds SET
        uri = ?,
        title = ?,
        author = ?,
        author_uri = ?,
        category = ?,
        updated = ?,
        icon_uri = ?,
        subtitle = ?,
        feed_meta = ? 
        WHERE rowid = ?''', 
        [feed.uri, feed.title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon, feed.subtitle, feed.feed_meta, feed.db_id])
        self.connection.commit()
        return


    def refresh_all(self) -> None:
        """
        Downloads a copy of every feed and updates the database using them.
        """
        print("refreshing.")
        feeds = self.get_all_feeds()
        for feed in feeds:
            new_feed_data = feedutility.atom_parse(_download_xml(feed.uri))
            new_feed_data.feed.db_id = feed.db_id
            new_feed_data.feed.uri = feed.uri
            self._update_feed(new_feed_data.feed)
            self._add_articles_to_database(_get_new_articles(new_feed_data, feed), feed.db_id)
        
            
    def scheduled_refresh(self) -> None:
        self.refresh_all()
        self.refresh_schedule.enter(self.settings.settings["refresh_time"], 1, self.scheduled_refresh)


    def delete_feed(self, feed_id: int) -> None:
        """
        removes a feed and its articles from the database.
        """
        c = self.connection.cursor()
        c.execute('''DELETE FROM feeds WHERE rowid = ?''', [feed_id])
        c.execute('''DELETE FROM articles WHERE feed_id = ?''', [feed_id])
        self.connection.commit()


    def mark_article_read(self, article_id: int) -> None:
        """
        Marks the article read in the database.
        """
        c = self.connection.cursor()
        c.execute('''UPDATE articles SET unread = 0 WHERE rowid = ?''', [article_id])
        self.connection.commit()

    
def _get_new_articles(cf: feedutility.CompleteFeed, f: feedutility.WebFeed) -> List[feedutility.Article]:
    """
    Takes a CompleteFeed, a feed, and returns the new articles in the CompleteFeed.
    """
    old_date = f.updated
    new_articles = [x for x in cf.articles if dateutil.parser.parse(x.updated) > dateutil.parser.parse(old_date)]
    return new_articles
    

def _download_xml(uri) -> any:
    """
    HTTP GET request for file, with headers indicating application.
    """
    headers = {'User-Agent' : 'python-rss-reader-side-project'}
    return defusxml.fromstring(requests.get(uri, headers=headers).text)

def write_string_to_file(str) -> None:
    """
    Write string to a file Output.xml.
    """
    text_file = open("Output.xml", "w", encoding="utf-8")
    text_file.write(str)
    return

def load_rss_from_disk(f: str) -> str:
    """
    Returns content in file "f".
    """
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss
