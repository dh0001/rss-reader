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
            published INTEGER)''')
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


    def _add_articles_to_database(self, articles, id) -> None:
        """
        Add multiple articles to database. articles should be a list.
        """
        c = self.connection.cursor()
        entries = []
        for article in articles:
            entries.append((id, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published))
        c.executemany('''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', entries)
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


    def get_articles(self, id) -> List[feedutility.Article]:
        """
        Returns a list containing all the articles with feed_id "id".
        """
        c = self.connection.cursor()
        articles = []
        for article in c.execute('''SELECT * FROM articles WHERE feed_id = ?''', [id]):
            new_article = feedutility.Article()
            new_article.title = article[2]
            new_article.updated = article[3]
            new_article.author = article[4]
            new_article.author_uri = article[5]
            new_article.content = article[6]
            articles.append(new_article)
        return articles


    def _add_atom_file(self, data, location) -> None:
        """
        Add atom feed data to database.
        """
        output = feedutility.atom_parse(data)
        new_articles = output.articles
        new_feed = output.feed
        new_feed.uri = location
        id = self._add_feed_to_database(new_feed)
        self._add_articles_to_database(new_articles, id)


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


    def get_feeds(self) -> List[feedutility.WebFeed]:
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
        refresh all feeds in the database.
        """
        print("refreshing.")
        feeds = self.get_feeds()
        for feed in feeds:
            data = feedutility.atom_parse(_download_xml(feed.uri))
            data.feed.db_id = feed.db_id
            data.feed.db_id = feed.uri
            self._update_feed(data.feed)
            self._add_articles_to_database(_get_new_articles(data, feed), feed.db_id)
    
        
            
    def scheduled_refresh(self) -> None:
        self.refresh_all()
        self.refresh_schedule.enter(self.settings.settings["refresh_time"], 1, self.scheduled_refresh)



    def delete_feed(self, id : int) -> None:
        """
        removes a feed from the database.
        """
        c = self.connection.cursor()
        c.execute('''DELETE FROM feeds WHERE rowid = ?''', [id])
        c.execute('''DELETE FROM articles WHERE rowid = ?''', [id])
        self.connection.commit()
        return

    
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

def load_rss_from_disk(f) -> str:
    """
    Returns content in file "f".
    """
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss
