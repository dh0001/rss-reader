import sqlite3
import feed as feedutility
import sched
import settings
import json
import datetime
from typing import List, Union
from PySide2 import QtCore as qtc
from sortedcontainers import SortedKeyList
from FeedUpdater import UpdateThread


class FeedManager(qtc.QObject):
    """
    Manages the feed data and provides an interface for getting that data. 
    """

    new_article_event = qtc.Signal(feedutility.Article)
    article_updated_event = qtc.Signal(feedutility.Article)
    feeds_updated_event = qtc.Signal()

    def __init__(self, settings: settings.Settings):
        super().__init__()

        self.feed_cache = self._load_feeds()

        self.settings = settings
        self._connection = sqlite3.connect(settings.settings["db_file"], check_same_thread=False)
        self._scheduler_thread = UpdateThread(self.feed_cache, self.settings)

        if self.settings.settings["first-run"] == "true":
            self._create_tables()
            self.settings.settings["first-run"] = "false"
            with open ("feeds.json", "w") as f:
                f.write("[]")

        self._scheduler_thread.data_downloaded_event.connect(self._update_feed_with_data)
        self._scheduler_thread.scheduled_default_refresh_event.connect(self.refresh_all)
        self._scheduler_thread.start()


    def cleanup(self) -> None:
        """
        Should be called before program exit. Closes db connection and exits threads gracefully.
        """
        self._scheduler_thread.requestInterruption()
        self._scheduler_thread.schedule_update_event.set()
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


    def add_feed(self, location: str, folder: feedutility.Folder) -> None:
        """
        Adds a new feed to the specified folder.
        """

        completefeed = feedutility.get_feed(location, "rss")

        new_feed = feedutility.Feed()
        new_feed.__dict__.update(completefeed.feed)
        new_feed.uri = location
        new_feed.parent_folder = folder
        new_feed.template = "rss"

        feed_id = self.settings.settings["feed_counter"]
        self.settings.settings["feed_counter"] += 1
        new_feed.db_id = feed_id

        folder.children.append(new_feed)

        self._process_new_articles(new_feed, completefeed.articles)


    def delete_feed(self, feed: feedutility.Feed) -> None:
        """
        Removes a feed with passed feed_id from cache. 
        Removes its entry from the refresh schedule, if it exists.
        """
        if feed.refresh_rate != None:
            self._refresh_schedule_remove_item(feed)

        del feed.parent_folder.children[feed.row]


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
        self._scheduler_thread.force_refresh_folder(self.feed_cache)


    def refresh_feed(self, feed: feedutility.Feed) -> None:
        """
        Adds a feed to the update feed queue.
        """
        self._scheduler_thread.force_refresh_feed(feed)


    def set_article_unread_status(self, feed, article_id, status: bool) -> None:
        """
        Sets the unread status in the database for passed article_id.
        """
        # TODO: find out if the article has status already set to same value
        c = self._connection.cursor()
        c.execute('''UPDATE articles SET unread = ? WHERE rowid = ?''', [status, article_id])
        self._connection.commit()
        feed.unread_count = self._get_unread_articles_count(feed)
        self.feeds_updated_event.emit()


    def set_refresh_rate(self, feed: feedutility.Feed, rate: Union[int, None]) -> None:
        """
        Sets the refresh rate for an individual feed, and sets/resets the scheduled refresh for that feed.
        """
        self._scheduler_thread.update_refresh_rate(feed, rate)


    def set_feed_user_title(self, feed: feedutility.Feed, user_title: Union[str, None]) -> None:
        """
        Sets a user specified title for a feed.
        """
        feed.user_title = user_title


    def set_default_refresh_rate(self, rate: int) -> None:
        """
        Sets the default refresh rate for feeds and resets the scheduled default refresh.
        """
        self.settings.settings["refresh_time"] = rate
        self._scheduler_thread.global_refresh_time_updated()


    def verify_feed_url(self, url: str) -> None:
        """
        Verifies if a url points to a proper feed.
        """
        try:
            feedutility.get_feed(url, "rss")
            return True
        except Exception:
            pass
        return False


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


    def _load_feeds(self):
        """
        Load feeds from disk.
        """
        tree = feedutility.Folder()
        with open("feeds.json", "rb") as f:
            s = f.read().decode("utf-8")
            l = json.loads(s, object_hook=dict_to_feed_or_folder)

        tree.children = l
        set_parents(tree)
        return tree


    def _save_all_feeds(self):
        """
        Saves contents of the cache to the disk.
        """
        with open ("feeds.json", "w") as f:
            f.write(json.dumps(self.feed_cache.children, default=lambda o: _remove_parents(o), indent=4))
        


    def _get_unread_articles_count(self, feed: feedutility.Feed) -> int:
        """
        Return the number of unread articles for the feed with passed feed_id. Sql operation.
        """
        return self._connection.cursor().execute('''SELECT count(*) FROM articles WHERE unread = 1 AND feed_id = ?''', [feed.db_id]).fetchone()[0]
    

    def _get_article_identifiers(self, feed_id: int) -> set:
        """
        Returns a set containing all the article atom id's from the feed with passed feed_id's id.
        """
        c = self._connection.cursor()
        articles = {}
        for article in c.execute('''SELECT identifier, updated FROM articles WHERE feed_id = ?''', [feed_id]):
            articles[article[0]] = article[1]
        return articles


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
        Recieves updated or new feed data.
        """
        # update feed
        feed.__dict__.update(new_completefeed.feed.__dict__)
        
        # update articles
        self._process_new_articles(feed, new_completefeed.articles)
        self.feeds_updated_event.emit()


    def _update_article(self, article):
        c = self._connection.cursor()
        c.execute('''
        UPDATE articles 
        SET uri = ?,
            title = ?,
            updated = ?,
            author = ?,
            author_uri = ?,
            content = ?,
            published = ?,
            unread = ?
        WHERE identifier = ?''', 
        [article.uri, article.title, article.updated, article.author, article.author_uri, article.content, article.published, article.unread, article.identifier])
        self._connection.commit()


    def _process_new_articles(self, feed, articles):
        """
        Processes the articles as new articles of the feed, and adds them to the database.
        """
        new_articles = []

        # TODO: handle custom delete policy
        limit = self.settings.settings["default_delete_time"]

        date_cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=limit)).isoformat()
        
        knownIds = self._get_article_identifiers(feed.db_id)

        for article in articles:

            if article.updated < date_cutoff:
                continue

            # TODO: these lines should not be needed
            article.feed_id = feed.db_id
            article.unread = True

            if article.identifier in knownIds:
                if knownIds[article.identifier] > article.updated:
                    self._update_article(article)
                    self.article_updated_event.emit(article)

            else:
                new_articles.append(article)
                self.new_article_event.emit(article)

        self._delete_old_articles(date_cutoff, feed.db_id)

        if len(new_articles) > 0:
            self._add_articles_to_database(new_articles, feed.db_id)

        feed.unread_count = self._get_unread_articles_count(feed)


    def _delete_old_articles(self, time_limit: str, feed_id: int) -> None:
        """
        Deletes articles in the database which are not after the passed time_limit.
        Time_limit is a string with an iso formatted time.
        """
        c = self._connection.cursor()
        c.execute('''DELETE from articles WHERE updated < ? and feed_id = ?''', [time_limit, feed_id])
        self._connection.commit()
        

    def _refresh_schedule_remove_item(self, feed: feedutility.Feed) -> None:
        """
        Removes an item from the refresh schedule.
        """
        i = next(i for i,v in enumerate(self._refresh_schedule) if v.feed.db_id == feed.db_id)
        del self._refresh_schedule[i]
        self._scheduler_thread.schedule_update_event.set()




def dict_to_feed_or_folder(d):
    if "children" in d:
        node = feedutility.Folder()
        node.__dict__.update(d)
        return node
    if "author_uri" in d:
        feed = feedutility.Feed()
        feed.__dict__.update(d)
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
