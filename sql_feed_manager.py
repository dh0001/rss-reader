import sqlite3
import requests
import defusedxml.ElementTree as defusxml
import feed as feedutility
import sched
import time
import threading
import settings
import json
import datetime
from typing import List, Union
from PyQt5 import QtCore as qtc
from sortedcontainers import SortedKeyList

class _FeedRefresh():
    """
    Small class holding a feed, and its entry in the scheduler.
    """
    __slots__ = 'feed', 'scheduled_time'
    def __init__(self, feed: feedutility.Feed, scheduled_time: float):
        self.feed : feedutility.Feed = feed
        self.scheduled_time : float = scheduled_time



class _DefaultFeedRefresh():
    """
    Small class to hold the time for default refresh.
    """
    __slots__ = 'scheduled_time', 'refresh_rate'
    def __init__(self, refresh_rate: float, scheduled_time: float):
        self.scheduled_time : float = scheduled_time
        self.refresh_rate : float = refresh_rate


class FeedManager():
    """
    Manages the feeds in the application, and connections to the database.
    """

    def __init__(self, settings: settings.Settings):
        """
        initialization.
        """
        self._settings = settings
        self._connection = sqlite3.connect(settings.settings["db_file"], check_same_thread=False)
        self._time_limit : int = self._settings.settings["default_delete_time"]
        self._schedule_lock : threading.Lock = threading.Lock()
        self._refresh_schedule : SortedKeyList
        self._new_feed_function : any = None
        self._new_article_function : any = None
        self._feed_data_changed_function : any = None
        self._schedule_update_event = threading.Event()
        self._default_refresh_entry : _DefaultFeedRefresh
        self._scheduler_thread : qtc.Thread

        if self._settings.settings["first-run"] == "true":
            self._create_tables()
            self._settings.settings["first-run"] = "false"

        self._start_refresh_schedule()


    def cleanup(self) -> None:
        """
        Should be called before program exit. Closes db connection and exits refresh thread gracefully.
        """
        self._scheduler_thread.requestInterruption()
        self._schedule_update_event.set()
        self._scheduler_thread.wait()
        self._connection.close()


    def get_articles(self, feed_id: int) -> List[feedutility.Article]:
        """
        Returns a list containing all the articles with feed_id "id".
        """
        c = self._connection.cursor()
        articles = []
        for article in c.execute('''SELECT rowid, * FROM articles WHERE feed_id = ?''', [feed_id]):
            return_article = feedutility.Article()
            return_article.db_id = article[0]
            return_article.feed_id = article[1]
            return_article.identifier = article[2]
            return_article.uri = article[3]
            return_article.title = article[4]
            return_article.updated = article[5]
            return_article.author = article[6]
            return_article.author_uri = article[7]
            return_article.content = article[8]
            return_article.published = article[9]
            return_article.unread = article[10]
            articles.append(return_article)
        return articles


    def _add_atom_file(self, data: any, download_uri: str) -> None:
        """
        Parse downloaded atom feed data, then insert the feed data and articles data into the database.
        """
        parsed_completefeed = feedutility.atom_parse(data)
        parsed_completefeed.feed.uri = download_uri
        row_id = self._add_feed_to_database(parsed_completefeed.feed)

        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=self._time_limit)).isoformat()
        self._add_articles_to_database(_filter_new_articles(parsed_completefeed.articles, date_cutoff, set()), row_id)


    def add_file_from_disk(self, location: str) -> None:
        """
        Add new feed to database from disk location.
        """
        data = _load_rss_from_disk(location)
        self._add_atom_file(data, location)


    def add_feed_from_web(self, download_uri: str) -> None:
        """
        Add new feed to database from web location.
        """
        data = _download_xml(download_uri)
        self._add_atom_file(data, download_uri)


    def get_all_feeds(self) -> List[feedutility.Feed]:
        """
        Returns a list containing all the feeds in the database.
        """
        c = self._connection.cursor()
        feeds = []
        for feed in c.execute('''SELECT rowid, * FROM feeds'''):
            new_feed = feedutility.Feed()
            new_feed.db_id = feed[0]
            new_feed.uri = feed[1]
            new_feed.title = feed[2]
            new_feed.user_title = feed[3]
            new_feed.author = feed[4]
            new_feed.author_uri = feed[5]
            new_feed.category = feed[6]
            new_feed.updated = feed[7]
            new_feed.icon_uri = feed[8]
            new_feed.subtitle = feed[9]
            new_feed.refresh_rate = feed[10]
            new_feed.meta = feed[11]
            new_feed.unread_count = self.get_unread_articles_count(new_feed.db_id)
            feeds.append(new_feed)
        return feeds


    def get_unread_articles_count(self, feed_id: int) -> int:
        """
        Return the number of unread articles for the feed with passed feed_id. Sql operation.
        """
        return self._connection.cursor().execute('''SELECT count(*) FROM articles WHERE unread = 1 AND feed_id = ?''', [feed_id]).fetchone()[0]
    

    def refresh_all(self) -> None:
        """
        Gets every feed from the database, then calls refresh_feed on all of them.
        """
        #print("refreshing.")
        feeds = self.get_all_feeds()
        for feed in feeds:
            self.refresh_feed(feed)
        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=self._time_limit)).isoformat()
        self._delete_old_articles(date_cutoff)


    def refresh_feed(self, feed: feedutility.Feed) -> None:
        """
        Download a feed and updates the database with the new data. Also calls the new article function with a list of new articles.
        """
        new_completefeed = feedutility.atom_parse(_download_xml(feed.uri))
        new_completefeed.feed.db_id = feed.db_id
        new_completefeed.feed.uri = feed.uri
        
        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=self._time_limit)).isoformat()
        new_articles = _filter_new_articles(new_completefeed.articles, date_cutoff, self._get_article_identifiers(feed.db_id))

        self._update_feed(new_completefeed.feed)

        for article in new_articles:
            article.feed_id = new_completefeed.feed.db_id
            article.unread = True

        self._add_articles_to_database(new_articles, feed.db_id)

        if callable(self._new_article_function):
            self._new_article_function(new_articles, new_completefeed.feed.db_id)


    def delete_feed(self, feed: feedutility.Feed) -> None:
        """
        Removes a feed with passed feed_id, and its articles from the database. Also removes the feed from the refresh
        tracker, if it has an individual refresh rate.
        """
        if feed.refresh_rate != None:
            self._refresh_schedule_remove_item(feed)

        c = self._connection.cursor()
        c.execute('''DELETE FROM feeds WHERE rowid = ?''', [feed.db_id])
        c.execute('''DELETE FROM articles WHERE feed_id = ?''', [feed.db_id])
        self._connection.commit()


    def set_article_unread_status(self, article_id: int, status: bool) -> None:
        """
        Changes the unread column in the database for passed article_id.
        """
        c = self._connection.cursor()
        c.execute('''UPDATE articles SET unread = ? WHERE rowid = ?''', [status, article_id])
        self._connection.commit()


    def set_feed_notify(self, call: any) -> None:
        """
        Tells the feed manager to run the passed function when feed information changes. Passes a list of feed.
        """
        self._new_feed_function = call


    def set_article_notify(self, call: any) -> None:
        """
        Tells the feed manager to run the passed function when article information changes. Passes a list of article.
        """
        self._new_article_function = call

    
    def set_feed_data_changed_notify(self, call: any) -> None:
        """
        Tells the feed manager to run the passed function when feed information changes. Passes a list of feed.
        """
        self._feed_data_changed_function = call


    def set_refresh_rate(self, feed: feedutility.Feed, rate: Union[int, None]) -> None:
        """
        Sets the refresh rate for an individual feed in the database, and sets/resets the scheduled refresh for that feed.
        """
        c = self._connection.cursor()
        c.execute('''UPDATE feeds SET refresh_rate = ? WHERE rowid = ?''', [rate, feed.db_id])
        self._connection.commit()

        with self._schedule_lock:
            feed.refresh_rate = rate
            i = next((i for i,v in enumerate(self._refresh_schedule) if v.feed.db_id == feed.db_id), None)
            if i != None:
                del self._refresh_schedule[i]

            if rate != None:
                self._refresh_schedule.add(_FeedRefresh(feed, time.time() + rate))
                self._schedule_update_event.set()



    def set_default_refresh_rate(self, rate: int) -> None:
        """
        Sets the default refresh rate for feeds and resets the scheduled default refresh.
        """
        with self._schedule_lock:
            self._settings.settings["refresh_time"] = rate
            self._default_refresh_entry = _DefaultFeedRefresh(rate, time.time() + rate)
            self._schedule_update_event.set()


    def set_feed_user_title(self, feed: feedutility.Feed, user_title: Union[str, None]) -> None:
        """
        Sets a user specified title for a feed.
        """
        c = self._connection.cursor()
        c.execute('''UPDATE feeds SET user_title = ? WHERE rowid = ?''', [user_title, feed.db_id])
        self._connection.commit()

        feed.user_title = user_title


    def verify_feed_url(self, url: str) -> None:
        """
        Verifies if a url points to a proper feed.
        """
        try:
            feedutility.atom_parse(_download_xml(url))
            return True
        except Exception:
            pass
        return False


    def _create_tables(self) -> None:
        """
        Creates all the tables used in rss-reader.
        """
        c = self._connection.cursor()
        c.execute('''CREATE TABLE feeds (
            uri TEXT,
            title TEXT,
            user_title TEXT,
            author TEXT,
            author_uri TEXT,
            category TEXT,
            updated INTEGER,
            icon_uri TEXT,
            subtitle TEXT,
            refresh_rate INTEGER,
            feed_meta TEXT)''')
        c.execute('''CREATE TABLE articles (
            feed_id INTEGER,
            identifier TEXT,
            uri TEXT,
            title TEXT,
            updated INTEGER,
            author TEXT,
            author_uri TEXT,
            content TEXT,
            published INTEGER,
            unread INTEGER)''')
        self._connection.commit()


    def _get_article_identifiers(self, feed_id: int) -> set:
        """
        Returns a set containing all the article atom id's from the feed with passed feed_id's id.
        """
        c = self._connection.cursor()
        articles = set()
        for article in c.execute('''SELECT identifier FROM articles WHERE feed_id = ?''', [feed_id]):
            articles.add(article[0])
        return articles


    def _add_feed_to_database(self, feed: feedutility.Feed) -> int:
        """
        Add a feed entry into the database. Returns the row id of the inserted entry.
        """
        c = self._connection.cursor()
        c.execute('''INSERT INTO feeds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
            [feed.uri, feed.title, feed.user_title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon_uri, feed.subtitle, feed.refresh_rate, json.dumps(feed.meta)])
        self._connection.commit()
        return c.lastrowid


    def _add_articles_to_database(self, articles: List[feedutility.Article], feed_id: int) -> None:
        """
        Add a list of articles to the database, and modify them with db_id filled in.
        """
        c = self._connection.cursor()
        for article in articles:
            c.execute('''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                [feed_id, article.identifier, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published, 1])
            article.db_id = c.lastrowid
        self._connection.commit()
        # c = self.connection.cursor()
        # entries = []
        # for article in articles:
        #     entries.append((feed_id, article.identifier, article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published, 1))
        # c.executemany('''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', entries)
        # self.connection.commit()


    def _update_feed(self, feed: feedutility.Feed) -> None:
        """
        Update the passed feed in the database.
        """
        c = self._connection.cursor()
        c.execute('''UPDATE feeds SET
        uri = ?,
        title = ?,
        user_title = ?,
        author = ?,
        author_uri = ?,
        category = ?,
        updated = ?,
        icon_uri = ?,
        subtitle = ?,
        feed_meta = ? 
        WHERE rowid = ?''', 
        [feed.uri, feed.title, feed.user_title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon_uri, feed.subtitle, json.dumps(feed.meta), feed.db_id])
        self._connection.commit()


    def _delete_old_articles(self, time_limit: str) -> None:
        """
        Deletes articles in the database which are not after the passed time_limit. Time_limit is an iso formatted time.
        """
        c = self._connection.cursor()
        c.execute('''DELETE from articles WHERE updated < ?''', [time_limit])
        self._connection.commit()


    def _scheduled_refresh(self, feed: feedutility.Feed) -> None:
        """
        Runs refresh_feed on the feed.
        """
        print("refreshing ", feed.title)
        with self._schedule_lock:
            self.refresh_feed(feed)


    def _scheduled_default_refresh(self) -> None:
        """
        Runs the scheduled refresh on feeds using the default refresh time.
        """
        print("start default refresh")
        with self._schedule_lock:
            feeds = self.get_all_feeds()
            for feed in feeds:
                if feed.refresh_rate == None:
                    print("refreshing by default: ", feed.title)
                    self.refresh_feed(feed)
        

    def _start_refresh_schedule(self) -> None:
        """
        Populates individual_refresh_tracker and starts the refresh schedule.
        """

        self._refresh_schedule = SortedKeyList(key=lambda x: x.scheduled_time)
        feeds = self.get_all_feeds()

        for feed in feeds:
            if feed.refresh_rate != None:
                self._refresh_schedule.add(_FeedRefresh(feed, time.time() + feed.refresh_rate))
            
        self._default_refresh_entry = _DefaultFeedRefresh(self._settings.settings["refresh_time"], time.time() + self._settings.settings["refresh_time"])

        self._scheduler_thread = SchedulerThread(self._refresh_schedule, self._schedule_update_event, self._default_refresh_entry, self._schedule_lock)
        self._scheduler_thread.start()
        self._scheduler_thread.scheduled_refresh_event.connect(self._scheduled_refresh)
        self._scheduler_thread.scheduled_default_refresh_event.connect(self._scheduled_default_refresh)


    def _refresh_schedule_remove_item(self, feed: feedutility.Feed) -> None:
        """
        Removes an item from the refresh schedule.
        """
        with self._schedule_lock:
            i = next(i for i,v in enumerate(self._refresh_schedule) if v.feed.db_id == feed.db_id)
            del self._refresh_schedule[i]
            self._schedule_update_event.set()




class SchedulerThread(qtc.QThread):

    scheduled_refresh_event = qtc.pyqtSignal(feedutility.Feed)
    scheduled_default_refresh_event = qtc.pyqtSignal()

    def __init__(self, scheduler: SortedKeyList, schedule_update_event: threading.Event, default_refresh: _DefaultFeedRefresh, schedule_lock: threading.Lock):
        qtc.QThread.__init__(self)
        self.abc = "abc"
        self.scheduler = scheduler
        self.schedule_updated_event = schedule_update_event
        self.default_refresh = default_refresh
        self.schedule_lock = schedule_lock

    def run(self):
        while True:
            if self.isInterruptionRequested():
                return

            with self.schedule_lock:
                if len(self.scheduler) > 0 and self.scheduler[0].scheduled_time <= time.time():
                    self.scheduled_refresh_event.emit(self.scheduler[0].feed)
                    feed = self.scheduler[0].feed
                    del self.scheduler[0]
                    self.scheduler.add(_FeedRefresh(feed, time.time() + feed.refresh_rate))

                elif self.default_refresh.scheduled_time <= time.time():
                    self.scheduled_default_refresh_event.emit()
                    self.default_refresh.scheduled_time = time.time() + self.default_refresh.refresh_rate

            if len(self.scheduler) > 0:
                next_time = min(self.scheduler[0].scheduled_time, self.default_refresh.scheduled_time)
            else:
                next_time = self.default_refresh.scheduled_time
            self.schedule_updated_event.wait(next_time - time.time())
            self.schedule_updated_event.clear()



    
def _filter_new_articles(articles: List[feedutility.Article], date_cutoff: str, known_ids: set) -> List[feedutility.Article]:
    """
    Returns a list containing the articles in 'articles' which have an id which is not part of the known_ids set.
    """
    new_articles = [x for x in articles if x.updated > date_cutoff and not x.identifier in known_ids]
    return new_articles
    

def _download_xml(uri: str) -> any:
    """
    Downloads file indicated by 'uri' using requests library, with a User-Agent header.
    """
    headers = {'User-Agent' : 'python-rss-reader-side-project'}
    file = requests.get(uri, headers=headers)
    return defusxml.fromstring(file.text)


def write_string_to_file(str: str) -> None:
    """
    Write string to the file named Output.xml.
    """
    text_file = open("Output.xml", "w", encoding="utf-8")
    text_file.write(str)
    return


def _load_rss_from_disk(f: str) -> str:
    """
    Returns content in file "f".
    """
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss
