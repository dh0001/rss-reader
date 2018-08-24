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
import queue
from typing import List, Union
from PyQt5 import QtCore as qtc
from sortedcontainers import SortedKeyList


class FeedManager():
    """
    Manages the feed objects, and connections to the database.
    """

    def __init__(self, settings: settings.Settings):
        """
        initialization.
        """
        self._settings = settings
        self._connection = sqlite3.connect(settings.settings["db_file"], check_same_thread=False)
        self.feed_cache : List[feedutility.Feed]

        self._new_feed_function : any = None
        self._new_article_function : any = None
        self._feed_data_changed_function : any = None
        
        self._time_limit : int = self._settings.settings["default_delete_time"]

        self._schedule_lock = threading.Lock()
        self.feed_lock = threading.Lock()
        self._refresh_schedule : SortedKeyList
        self._default_refresh_entry : _DefaultFeedRefresh
        self._update_settings : _UpdateThreadSettings
        self._scheduler_thread : qtc.Thread
        self._update_event = threading.Event()

        if self._settings.settings["first-run"] == "true":
            self._create_tables()
            self._settings.settings["first-run"] = "false"
            with open ("feeds.json", "w") as f:
                f.write("[]")

        self._feed_download_queue : queue.SimpleQueue
        self._feed_download_queue_updated_event = threading.Event()
        self._download_thread : qtc.Thread
        self._download_thread_settings : _UpdateThreadSettings

        self._cache_all_feeds()
        self._start_refresh_thread()


    def cleanup(self) -> None:
        """
        Should be called before program exit. Closes db connection and exits threads gracefully.
        """
        self._scheduler_thread.requestInterruption()
        self._update_event.set()
        self._scheduler_thread.wait()
        self._save_all_feeds()
        self._connection.close()


    def get_articles(self, feed_id: int) -> List[feedutility.Article]:
        """
        Returns a list containing all the articles with passed feed_id.
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


    def get_all_feeds(self) -> List[feedutility.Feed]:
        """
        Returns a list containing all the feeds in the database.
        """
        return self.feed_cache


    def add_file_from_disk(self, location: str, folder: feedutility.Folder) -> None:
        """
        Adds new feed to the database from disk location.
        """
        data = _load_rss_from_disk(location)
        self._add_feed(data, location, folder)


    def add_feed_from_web(self, download_uri: str, folder: feedutility.Folder) -> None:
        """
        Adds new feed to database from web location.
        """
        data = _download_xml(download_uri)
        self._add_feed(data, download_uri, folder)


    def delete_feed(self, feed: feedutility.Feed) -> None:
        """
        Removes a feed with passed feed_id from cache. 
        Removes its entry from the refresh schedule, if it exists.
        """
        if feed.refresh_rate != None:
            self._refresh_schedule_remove_item(feed)

        del feed.parent_folder.children[feed.row]
        update_rows(feed.parent_folder.children)


    def add_folder(self, folder_name: str, folder: feedutility.Folder) -> None:
        """
        Adds a folder to the cache.
        """
        new_folder = feedutility.Folder()
        new_folder.title = folder_name
        new_folder.parent_folder = folder
        new_folder.row = len(folder.children)
        folder.children.append(new_folder)


    def delete_folder(self, folder: feedutility.Folder) -> None:
        """
        Deletes a folder.
        """
        self._delete_feeds_in_folder(folder)
        parent = folder.parent_folder
        del parent.children[folder.row]
        update_rows(parent.children)

    
    def rename_folder(self, name: str, folder: feedutility.Folder) -> None:
        """
        Changes the name of a folder.
        """
        folder.title = name

        
    def _delete_feeds_in_folder(self, folder: feedutility.Folder) -> None:
        """
        Deletes all feeds in a folder recursively.
        """
        for child in folder.children:
            if type(child) == feedutility.Feed:
                self.delete_feed(child)
            else:
                self._delete_feeds_in_folder(child)


    def refresh_all(self) -> None:
        """
        Calls refresh_feed on every feed in the cache.
        """
        for feed in self.feed_cache:
            self.refresh_feed(feed)
        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=self._time_limit)).isoformat()
        self._delete_old_articles(date_cutoff)


    def refresh_feed(self, feed: feedutility.Feed) -> None:
        """
        Adds a feed to the update feed queue.
        """
        self._feed_download_queue.put(feed)
        self._update_event.set()


    def set_article_unread_status(self, article_id: int, status: bool) -> None:
        """
        Sets the unread status in the database for passed article_id.
        """
        c = self._connection.cursor()
        c.execute('''UPDATE articles SET unread = ? WHERE rowid = ?''', [status, article_id])
        self._connection.commit()


    def set_refresh_rate(self, feed: feedutility.Feed, rate: Union[int, None]) -> None:
        """
        Sets the refresh rate for an individual feed, and sets/resets the scheduled refresh for that feed.
        """
        with self._schedule_lock:
            feed.refresh_rate = rate
            i = next((i for i,v in enumerate(self._refresh_schedule) if v.feed.db_id == feed.db_id), None)
            if i != None:
                del self._refresh_schedule[i]

            if rate != None:
                self._refresh_schedule.add(_FeedRefresh(feed, time.time() + rate))
                self._update_event.set()


    def set_feed_user_title(self, feed: feedutility.Feed, user_title: Union[str, None]) -> None:
        """
        Sets a user specified title for a feed.
        """
        feed.user_title = user_title


    def set_default_refresh_rate(self, rate: int) -> None:
        """
        Sets the default refresh rate for feeds and resets the scheduled default refresh.
        """
        with self._schedule_lock:
            self._settings.settings["refresh_time"] = rate
            self._default_refresh_entry.refresh_rate = rate
            self._default_refresh_entry.scheduled_time = time.time() + rate
            self._update_event.set()


    def verify_feed_url(self, url: str) -> None:
        """
        Verifies if a url points to a proper feed.
        """
        try:
            down = _download_xml(url)
            feedutility.atom_parse(down)
            return True
        except Exception:
            pass
        return False


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


    def _create_tables(self) -> None:
        """
        Creates all the tables used in rss-reader.
        """
        c = self._connection.cursor()
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


    def _cache_all_feeds(self):
        """
        Caches the feeds on the disk.
        """
        tree = feedutility.Folder()
        with open("feeds.json", "rb") as f:
            s = f.read().decode("utf-8")
            l = json.loads(s, object_hook=dict_to_feed_or_folder)

        tree.children = l
        set_parents(tree)
        self.feed_cache = tree


    def _save_all_feeds(self):
        """
        Saves contents of the cache to the disk.
        """
        with open ("feeds.json", "w") as f:
            f.write(json.dumps(self.feed_cache.children, default=lambda o: _remove_parents(o), indent=4))
        


    def _get_unread_articles_count(self, feed_id: int) -> int:
        """
        Return the number of unread articles for the feed with passed feed_id. Sql operation.
        """
        return self._connection.cursor().execute('''SELECT count(*) FROM articles WHERE unread = 1 AND feed_id = ?''', [feed_id]).fetchone()[0]
    

    def _get_article_identifiers(self, feed_id: int) -> set:
        """
        Returns a set containing all the article atom id's from the feed with passed feed_id's id.
        """
        c = self._connection.cursor()
        articles = set()
        for article in c.execute('''SELECT identifier FROM articles WHERE feed_id = ?''', [feed_id]):
            articles.add(article[0])
        return articles


    def _add_feed(self, data: feedutility.CompleteFeed, download_uri: str, folder: feedutility.Folder) -> None:
        """
        Parse downloaded atom feed data, then insert the feed data and articles data into the database.
        """
        parsed_completefeed = feedutility.atom_parse(data)

        new_feed = feedutility.Feed()
        new_feed.__dict__.update(parsed_completefeed.feed.__dict__)
        new_feed.uri = download_uri

        feed_id = self._settings.settings["feed_counter"]
        self._settings.settings["feed_counter"] += 1

        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=self._time_limit)).isoformat()
        self._add_articles_to_database(_filter_new_articles(parsed_completefeed.articles, date_cutoff, set()), feed_id)
        new_feed.unread_count = self._get_unread_articles_count(feed_id)
        new_feed.db_id = feed_id

        new_feed.row = len(folder.children)
        new_feed.parent_folder = folder
        folder.children.append(new_feed)


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


    def _update_feed_in_database(self, feed: feedutility.Feed) -> None:
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
        WHERE id = ?''', 
        [feed.uri, feed.title, feed.user_title, feed.author, feed.author_uri, feed.category, feed.updated, feed.icon_uri, feed.subtitle, json.dumps(feed.meta), feed.db_id])
        self._connection.commit()


    def _update_feed_with_data(self, feed: feedutility.Feed, new_completefeed: feedutility.CompleteFeed):
        """
        Updates feed with new data.
        """
        feed.__dict__.update(new_completefeed.feed.__dict__)
        
        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=self._time_limit)).isoformat()
        new_articles = _filter_new_articles(new_completefeed.articles, date_cutoff, self._get_article_identifiers(feed.db_id))

        for article in new_articles:
            article.feed_id = feed.db_id
            article.unread = True

        self._add_articles_to_database(new_articles, feed.db_id)
        feed.unread_count = self._get_unread_articles_count(feed.db_id)

        if callable(self._new_article_function):
            self._new_article_function(new_articles, feed.db_id)


    def _delete_old_articles(self, time_limit: str) -> None:
        """
        Deletes articles in the database which are not after the passed time_limit. Time_limit is an iso formatted time.
        """
        c = self._connection.cursor()
        c.execute('''DELETE from articles WHERE updated < ?''', [time_limit])
        self._connection.commit()
        

    def _refresh_schedule_remove_item(self, feed: feedutility.Feed) -> None:
        """
        Removes an item from the refresh schedule.
        """
        with self._schedule_lock:
            i = next(i for i,v in enumerate(self._refresh_schedule) if v.feed.db_id == feed.db_id)
            del self._refresh_schedule[i]
            self._update_event.set()


    def _start_refresh_thread(self) -> None:
        """
        Populates individual_refresh_tracker and starts the refresh schedule.
        """
        self._refresh_schedule = SortedKeyList(key=lambda x: x.scheduled_time)
        feeds = self.get_all_feeds()
        self._feed_download_queue = queue.SimpleQueue()

        for feed in feeds:
            if feed.refresh_rate != None:
                self._refresh_schedule.add(_FeedRefresh(feed, time.time() + feed.refresh_rate))
            
        self._default_refresh_entry = _DefaultFeedRefresh(self._settings.settings["refresh_time"], time.time() + self._settings.settings["refresh_time"])
        self._update_settings = _UpdateThreadSettings(self._settings.settings)

        self._scheduler_thread = UpdateThread(self._refresh_schedule, self._update_event, self._default_refresh_entry, self._schedule_lock, self.feed_cache, self.feed_lock, self._feed_download_queue, self._update_settings)
        self._scheduler_thread.update_feed_event.connect(self._update_feed_with_data)
        self._scheduler_thread.scheduled_default_refresh_event.connect(self.refresh_all)
        self._scheduler_thread.start()



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



class _UpdateThreadSettings():
    """
    Holds the update thread settings.
    """
    def __init__(self, settings: dict):
        self.settings = settings
        self.lock = threading.Lock()
    
    def set_global_rate_limit(self, time: float):
        with self.lock:
            self.settings["global_refresh_rate"] = time

    def get_global_rate_limit(self):
        with self.lock:
            return self.settings["global_refresh_rate"]



class UpdateThread(qtc.QThread):
    update_feed_event = qtc.pyqtSignal(feedutility.Feed, object)
    scheduled_default_refresh_event = qtc.pyqtSignal()
    download_error_event = qtc.pyqtSignal()

    def __init__(self, schedule: SortedKeyList, update_event: threading.Event, default_refresh: _DefaultFeedRefresh, schedule_lock: threading.Lock, feed_list: List[feedutility.Feed], feed_lock: threading.Lock, queue: queue.SimpleQueue, settings: _UpdateThreadSettings):
        qtc.QThread.__init__(self)
        self.schedule = schedule
        self.update_event = update_event
        self.default_refresh = default_refresh
        self.schedule_lock = schedule_lock
        self.feed_list = feed_list
        self.feed_lock = feed_lock
        self.refresh_queue = queue
        self.settings = settings

    def run(self):
        while True:
            if self.isInterruptionRequested():
                return

            if not self.refresh_queue.empty():
                self.update_feed(self.refresh_queue.get_nowait())
                continue
            
            else:
                with self.schedule_lock:
                    # Scheduled refreshes
                    if len(self.schedule) > 0 and self.schedule[0].scheduled_time <= time.time():
                        feed = self.schedule[0].feed
                        self.update_feed(feed)
                        self.schedule.add(_FeedRefresh(feed, time.time() + feed.refresh_rate))
                        del self.schedule[0]
    
                    # Default refresh
                    elif self.default_refresh.scheduled_time <= time.time():
                        self.scheduled_default_refresh_event.emit()
                        self.default_refresh.scheduled_time = time.time() + self.default_refresh.refresh_rate
    
                # get time to wait
                if len(self.schedule) > 0:
                    next_time = min(self.schedule[0].scheduled_time, self.default_refresh.scheduled_time)
                else:
                    next_time = self.default_refresh.scheduled_time

            # wait
            self.update_event.wait(next_time - time.time())
            self.update_event.clear()

    def update_feed(self, feed: feedutility.Feed):
        try:
            new_completefeed = feedutility.atom_parse(_download_xml(feed.uri))
        except Exception:
            print("Error parsing feed")
            return

        self.update_feed_event.emit(feed, new_completefeed)
        time.sleep(self.settings.get_global_rate_limit())


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


def _cache_from_file() -> feedutility.Folder:
    """
    """

def dict_to_feed_or_folder(d):
    if "children" in d:
        node = feedutility.Folder()
        node.__dict__ = d
        return node
    if "author_uri" in d:
        feed = feedutility.Feed()
        feed.__dict__ = d
        return feed
    return d


def _remove_parents(a):
    if "parent_folder" in a.__dict__:
        del a.__dict__["parent_folder"]
    return a.__dict__

def set_parents(tree):
    for child in tree.children:
        child.parent_folder = tree
        if type(child) == feedutility.Folder:
            set_parents(child)


def update_rows(l: list):
    for i,node in enumerate(l):
        node.row = i