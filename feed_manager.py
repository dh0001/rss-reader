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
import dateutil.parser


class FeedManager(qtc.QObject):
    """Manages the feed data and provides an interface for getting that data."""

    new_article_event = qtc.Signal(feedutility.Article)
    article_updated_event = qtc.Signal(feedutility.Article)
    feeds_updated_event = qtc.Signal()

    def __init__(self, settings: settings.Settings):
        super().__init__()

        # feed_cache is a folder, and the 'root' folder for the feed manager.
        # Currently done like this for easier setting of parents, adding to folder, and refresh.
        self.feed_cache = self._load_feeds()

        self.settings = settings
        self._connection = sqlite3.connect(settings.settings["db_file"])
        self._connection.row_factory = sqlite3.Row

        # create and start scheduler thread
        self._scheduler_thread = UpdateThread(self.feed_cache, self.settings)

        if self.settings.settings["first-run"] == "true":
            self._initialize_database()
            self.settings.settings["first-run"] = "false"
            with open ("feeds.json", "w") as f:
                f.write("[]")

        self._scheduler_thread.data_downloaded_event.connect(self._update_feed_with_data)
        self._scheduler_thread.start()


    def cleanup(self) -> None:
        """Closes db connection and exits threads gracefully."""

        self._scheduler_thread.requestInterruption()
        self._scheduler_thread.schedule_update_event.set()
        self._scheduler_thread.wait()
        self._save_feeds()
        self._connection.close()


    def get_articles(self, feed_id: int) -> List[feedutility.Article]:
        """Returns a list containing all the articles with feed_id.

        Args:
            feed_id: The id of the feed to return articles from.

        Returns:
            A list of articles with the corresponding feed_id.
        """
        articles = []
        for row in self._connection.execute('SELECT identifier, uri, title, updated, author, content, unread FROM articles WHERE feed_id = ?', [feed_id]):
            article = feedutility.Article()
            article.feed_id = feed_id
            article.identifier = row['identifier']
            article.uri = row['uri']
            article.title = row['title']
            article.updated = datetime.datetime.fromtimestamp(row['updated'], datetime.timezone.utc)
            article.author = row['author']
            article.content = row['content']
            article.unread = bool(row['unread'])
            articles.append(article)
        return articles


    def add_feed(self, location: str, folder: feedutility.Folder) -> None:
        """Verify that a feed is valid, and adds it to the folder."""

        feed, articles = feedutility.get_feed(location, "rss")

        feed.uri = location
        feed.parent_folder = folder
        feed.template = "rss"

        # feed_counter should always be free
        feed.db_id = self.settings.settings["feed_counter"]
        self.settings.settings["feed_counter"] += 1
        
        folder.children.append(feed)

        self._process_new_articles(feed, articles)
        self.feeds_updated_event.emit()
        self._save_feeds()


    def delete_feed(self, feed: feedutility.Feed) -> None:
        """Removes a feed from the feed_manager.

        Removes a feed with passed feed_id, and its entry from the refresh schedule.
        """
        if feed.refresh_rate != None:
            self._refresh_schedule_remove_item(feed)

        assert feed.parent_folder.children.index(feed) != -1, "Folder was not found when trying to delete it!"
        del feed.parent_folder.children[feed.parent_folder.children.index(feed)]
        self._save_feeds()


    def add_folder(self, folder_name: str, folder: feedutility.Folder) -> None:
        """Adds a folder."""
        new_folder = feedutility.Folder()
        new_folder.title = folder_name
        new_folder.parent_folder = folder
        folder.children.append(new_folder)
        self._save_feeds()


    def delete_folder(self, folder: feedutility.Folder) -> None:
        """Deletes a folder."""

        def _delete_feeds_in_folder(folder: feedutility.Folder) -> None:
            """Deletes all feeds in a folder recursively."""
            for child in folder.children:
                if type(child) == feedutility.Feed:
                    self.delete_feed(child)
                else:
                    _delete_feeds_in_folder(child)
        
        _delete_feeds_in_folder(folder)
        assert folder.parent_folder.children.index(folder) != -1, "Folder was not found when trying to delete it!"
        del folder.parent_folder.children[folder.parent_folder.children.index(folder)]
        self._save_feeds()

    
    def rename_folder(self, name: str, folder: feedutility.Folder) -> None:
        """Changes the name of a folder."""
        folder.title = name
        self._save_feeds()


    def refresh_all(self) -> None:
        """Calls refresh_feed on every feed in the cache."""
        self._scheduler_thread.force_refresh_folder(self.feed_cache)


    def refresh_feed(self, feed: feedutility.Feed) -> None:
        """Adds a feed to the update feed queue."""
        self._scheduler_thread.force_refresh_feed(feed)


    def set_article_unread_status(self, feed: feedutility.Feed, article_identifier: str, status: bool) -> None:
        """Sets the unread status in the database for an article."""
        # TODO: find out if the article has status already set to same value
        self._connection.execute('''UPDATE articles SET unread = ? WHERE identifier = ?''', [status, article_identifier])
        feed.unread_count = self._get_unread_articles_count(feed)
        self.feeds_updated_event.emit()


    def set_refresh_rate(self, feed: feedutility.Feed, rate: Union[int, None]) -> None:
        """Sets the refresh rate for an individual feed.
        
        and sets/resets the scheduled refresh for that feed."""
        self._scheduler_thread.update_refresh_rate(feed, rate)


    def set_feed_user_title(self, feed: feedutility.Feed, user_title: Union[str, None]) -> None:
        """Sets a user specified title for a feed."""
        feed.user_title = user_title
        self._save_feeds()


    def set_default_refresh_rate(self, rate: int) -> None:
        """Sets the default refresh rate for feeds and resets the scheduled default refresh."""
        self.settings.settings["refresh_time"] = rate
        self._scheduler_thread.global_refresh_time_updated()


    def verify_feed_url(self, url: str) -> bool:
        """Verifies if a url points to a proper feed."""
        try:
            feedutility.get_feed(url, "rss")
            return True
        except Exception:
            return False


    def _initialize_database(self) -> None:
        """Creates all the tables used."""
        self._connection.execute('''CREATE TABLE articles (
            feed_id INTEGER,
            identifier TEXT,
            uri TEXT,
            title TEXT,
            updated FLOAT,
            author TEXT,
            content TEXT,
            unread BOOLEAN)''')


    def _load_feeds(self):
        """Load feeds from disk."""

        def set_parents(tree):
            """recursively set parents"""
            for child in tree.children:
                child.parent_folder = tree
                if type(child) == feedutility.Folder:
                    set_parents(child)


        def _dict_to_feed_or_folder(d):
            if "children" in d:
                node = feedutility.Folder()
                node.__dict__ = d
                return node
            elif "title" in d:
                feed = feedutility.Feed()
                feed.__dict__ = d
                return feed
            return d


        folder = feedutility.Folder()
        with open("feeds.json", "rb") as f:
            s = f.read().decode("utf-8")
            folder.children = json.loads(s, object_hook=_dict_to_feed_or_folder)

        set_parents(folder)
        return folder


    def _save_feeds(self):
        """Saves the feeds to disk."""

        unsavable = ["parent_folder"]

        with open ("feeds.json", "w") as f:
            f.write(json.dumps(self.feed_cache.children, default=lambda o: {k:v for k,v in o.__dict__.items() if k not in unsavable}, indent=4))
        


    def _get_unread_articles_count(self, feed: feedutility.Feed) -> int:
        """Return the number of unread articles for a feed."""
        return self._connection.execute('''SELECT count(*) FROM articles WHERE unread = 1 AND feed_id = ?''', [feed.db_id]).fetchone()[0]
    

    def _get_article_identifiers(self, feed_id: int) -> set:
        """Returns a set containing all the identifiers of all articles for a feed."""
        articles = {}
        for article in self._connection.execute('''SELECT identifier, updated FROM articles WHERE feed_id = ?''', [feed_id]):
            articles[article['identifier']] = datetime.datetime.fromtimestamp(article['updated'], datetime.timezone.utc)
        return articles


    def _add_articles_to_database(self, articles: List[feedutility.Article], feed_id: int) -> None:
        """Add a list of articles to the database.
        
        All articles will be marked as unread."""
        with self._connection:
            for article in articles:
                self._connection.execute('''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    [feed_id, article.identifier, article.uri, article.title, article.updated.timestamp(), article.author, article.content, 1])


    def _update_feed_with_data(self, feed: feedutility.Feed, new_feed_data: feedutility.Feed, articles: List[feedutility.Article]):
        """Recieves updated or new feed data."""
        # update feed
        feed.update(new_feed_data)
        
        # update articles
        self._process_new_articles(feed, articles)
        self.feeds_updated_event.emit()


    def _update_articles(self, articles):
        """Updates an existing article in the database."""
        with self._connection:
            for article in articles:
                self._connection.execute('''
                UPDATE articles 
                SET uri = ?,
                    title = ?,
                    updated = ?,
                    author = ?,
                    content = ?,
                    unread = ?
                WHERE identifier = ?''', 
                [article.uri, article.title, article.updated.timestamp(), article.author, article.content, article.unread, 
                article.identifier])


    def _process_new_articles(self, feed, articles):
        """Processes newly created articles for the feed, and adds them to the database.
        
        Checks for and delete old articles in the list, and delete old aricles in the database.
        If the article already exists in the database, will update it instead of adding.
        Will also update the unread count on the feed."""

        # TODO: handle custom delete policy, only using default delete time for now
        limit = self.settings.settings["default_delete_time"]
        if limit == 0:
            date_cutoff = None
        else:
            date_cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=limit)
            self._delete_old_articles(date_cutoff, feed.db_id)
        
        knownIds = self._get_article_identifiers(feed.db_id)

        new_articles = []
        updated_articles = []
        for article in articles:

            if date_cutoff is not None and article.updated < date_cutoff:
                continue

            if article.identifier in knownIds:
                if knownIds[article.identifier] > article.updated:
                    self._update_article(article)
                    updated_articles.append(article)

            else:
                self.new_article_event.emit(article)
                new_articles.append(article)

        self._update_articles(updated_articles)
        map(self.article_updated_event.emit, updated_articles)
        self._add_articles_to_database(new_articles, feed.db_id)

        feed.unread_count = self._get_unread_articles_count(feed)


    def _delete_old_articles(self, cutoff_time: datetime.datetime, feed_id: int) -> None:
        """Deletes articles in the database which are not after the passed time_limit."""
        self._connection.execute('''DELETE from articles WHERE updated < ? and feed_id = ?''', [cutoff_time.timestamp(), feed_id])
        

    def _refresh_schedule_remove_item(self, feed: feedutility.Feed) -> None:
        """Removes an item from the refresh schedule."""
        i = next(i for i,v in enumerate(self._refresh_schedule) if v.feed.db_id == feed.db_id)
        del self._refresh_schedule[i]
        self._scheduler_thread.schedule_update_event.set()


