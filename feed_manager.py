import sqlite3
import json
import datetime
from typing import List, Union, Dict
import os

from PySide2 import QtCore as qtc

from feed import Feed, Article, Folder, get_feed
from feed_updater import UpdateThread


class FeedManager(qtc.QObject):
    """Manages the feed data and provides an interface for getting that data."""

    new_article_event = qtc.Signal(Article)
    article_updated_event = qtc.Signal(Article)
    feeds_updated_event = qtc.Signal()

    def __init__(self, settings: dict):
        super().__init__()

        # feed_cache is a folder, and the 'root' folder for the feed manager.
        # Currently done like this for easier setting of parents, adding to folder, and refresh.
        self.feed_cache = self._load_feeds()

        self.settings = settings
        self._connection = sqlite3.connect(self.settings["db_file"])
        self._connection.row_factory = sqlite3.Row

        # create and start scheduler thread
        self._scheduler_thread = UpdateThread(self.feed_cache, self.settings)

        self._initialize_database()

        self._scheduler_thread.data_downloaded_event.connect(self._update_feed_with_data)
        self._scheduler_thread.start()

        if settings["startup_update"] is True:
            self.refresh_all()


    def cleanup(self) -> None:
        """Closes db connection and exits threads gracefully."""

        self._scheduler_thread.requestInterruption()
        self._scheduler_thread.schedule_update_event.set()
        self._scheduler_thread.wait()
        self._save_feeds()
        self._connection.close()


    def get_articles(self, feed_id: int) -> List[Article]:
        """Returns a list containing all the articles with feed_id.

        Args:
            feed_id: The id of the feed to return articles from.

        Returns:
            A list of articles with the corresponding feed_id.
        """
        articles = []
        for row in self._connection.execute('SELECT identifier, uri, title, updated, author, content, unread, flag FROM articles WHERE feed_id = ?', [feed_id]):
            article = Article()
            article.feed_id = feed_id
            article.identifier = row['identifier']
            article.uri = row['uri']
            article.title = row['title']
            article.updated = datetime.datetime.fromtimestamp(row['updated'], datetime.timezone.utc)
            article.author = row['author']
            article.content = row['content']
            article.unread = bool(row['unread'])
            article.flag = bool(row['flag'])
            articles.append(article)
        return articles


    def add_feed(self, location: str, folder: Folder) -> None:
        """Verify that a feed is valid, and adds it to the folder."""

        feed, articles = get_feed(location, "rss")

        feed.uri = location
        feed.parent_folder = folder
        feed.template = "rss"

        # feed_counter should always be free
        feed.db_id = self.settings["feed_counter"]
        self.settings["feed_counter"] += 1

        folder.children.append(feed)

        self._process_new_articles(feed, articles)
        self.feeds_updated_event.emit()
        self._save_feeds()


    def delete_feed(self, feed: Feed) -> None:
        """Removes a feed from the feed_manager.

        Removes a feed with passed feed_id, and its entry from the refresh schedule.
        """
        if feed.refresh_rate is not None:
            self._scheduler_thread.remove_feed(feed)

        assert feed.parent_folder.children.index(feed) != -1, "Folder was not found when trying to delete it!"
        del feed.parent_folder.children[feed.parent_folder.children.index(feed)]
        self._save_feeds()


    def add_folder(self, folder_name: str, folder: Folder) -> None:
        """Adds a folder."""
        new_folder = Folder()
        new_folder.title = folder_name
        new_folder.parent_folder = folder
        folder.children.append(new_folder)
        self._save_feeds()


    def delete_folder(self, folder: Folder) -> None:
        """Deletes a folder."""

        def _delete_feeds_in_folder(folder: Folder) -> None:
            """Deletes all feeds in a folder recursively."""
            for child in folder.children:
                if type(child) is Feed:
                    self.delete_feed(child)
                else:
                    _delete_feeds_in_folder(child)

        _delete_feeds_in_folder(folder)
        assert folder.parent_folder.children.index(folder) != -1, "Folder was not found when trying to delete it!"
        del folder.parent_folder.children[folder.parent_folder.children.index(folder)]
        self._save_feeds()


    def rename_folder(self, name: str, folder: Folder) -> None:
        """Changes the name of a folder."""
        folder.title = name
        self._save_feeds()


    def refresh_all(self) -> None:
        """Schedules all feeds to be refreshed."""
        self._scheduler_thread.force_refresh_folder(self.feed_cache)


    def refresh_feed(self, feed: Feed) -> None:
        """Schedules a feed to be refreshed."""
        self._scheduler_thread.force_refresh_feed(feed)


    def set_article_unread_status(self, feed: Feed, article: Article, status: bool) -> None:
        """Sets the unread status in the article, and in the database.

        Also updates the feed's unread_count, and emits an event for this.
        Does not do anything if the status is not different.
        """
        if article.unread != status:
            article.unread = status
            with self._connection:
                self._connection.execute('''UPDATE articles SET unread = ? WHERE identifier = ? and feed_id = ?''', [status, article.identifier, article.feed_id])
            feed.unread_count = self._get_unread_articles_count(feed)
            self.feeds_updated_event.emit()


    def toggle_article_flag(self, article: Article) -> None:
        """Inverts flag status on an article."""
        article.flag = not article.flag
        with self._connection:
            self._connection.execute('''UPDATE articles SET flag = ? WHERE identifier = ? and feed_id = ?''', [article.flag, article.identifier, article.feed_id])


    def set_refresh_rate(self, feed: Feed, rate: Union[int, None]) -> None:
        """Sets the refresh rate for an individual feed.

        and sets/resets the scheduled refresh for that feed."""
        self._scheduler_thread.update_refresh_rate(feed, rate)


    @staticmethod
    def set_feed_user_title(feed: Feed, user_title: Union[str, None]) -> None:
        """Sets a user specified title for a feed."""
        feed.user_title = user_title


    def set_default_refresh_rate(self, rate: int) -> None:
        """Sets the default refresh rate for feeds and resets the scheduled default refresh."""
        self._scheduler_thread.update_global_refresh_rate(rate)


    def set_feed_attributes(self, feed: Feed, user_title: Union[str, None], refresh_rate: Union[int, None], delete_time: Union[int, None], ignore_new_articles: bool) -> None:
        """Sets properties for all feeds.

        Will check if value is same as previous value, and will not update if that is the case.
        Saves feed changes to disk."""
        if feed.refresh_rate != refresh_rate:
            self.set_refresh_rate(feed, refresh_rate)

        if feed.user_title != user_title:
            self.set_feed_user_title(feed, user_title)

        feed.delete_time = delete_time
        feed.ignore_new = ignore_new_articles
        self.feeds_updated_event.emit()
        self._save_feeds()


    @staticmethod
    def verify_feed_url(url: str) -> bool:
        """Verifies if a url points to a proper feed."""
        try:
            get_feed(url, "rss")
            return True
        except Exception:
            return False


    def _initialize_database(self) -> None:
        """Creates all the tables used."""
        with self._connection:
            self._connection.execute('''CREATE TABLE IF NOT EXISTS articles (
                feed_id INTEGER,
                identifier TEXT,
                uri TEXT,
                title TEXT,
                updated FLOAT,
                author TEXT,
                content TEXT,
                unread BOOLEAN,
                flag BOOLEAN)''')


    @staticmethod
    def _load_feeds():
        """Load feeds from disk."""

        def set_parents(tree):
            """recursively set parents"""
            for child in tree.children:
                child.parent_folder = tree
                if type(child) is Folder:
                    set_parents(child)


        def _dict_to_feed_or_folder(node):
            if "children" in node:
                folder = Folder()
                folder.__dict__ = node
                return folder

            if "title" in node:
                feed = Feed()
                feed.__dict__ = node
                return feed
            return node

        if not os.path.exists("feeds.json"):
            with open("feeds.json", "w") as new_file:
                new_file.write("[]")

        folder = Folder()
        with open("feeds.json", "rb") as feeds_file:
            contents = feeds_file.read().decode("utf-8")
            folder.children = json.loads(contents, object_hook=_dict_to_feed_or_folder)

        set_parents(folder)
        return folder


    def _save_feeds(self):
        """Saves the feeds to disk."""

        unsavable = ["parent_folder"]

        with open("feeds.json", "w") as feeds_file:
            feeds_file.write(json.dumps(self.feed_cache.children, default=lambda o: {k: v for (k, v) in o.__dict__.items() if k not in unsavable}, indent=4))



    def _get_unread_articles_count(self, feed: Feed) -> int:
        """Return the number of unread articles for a feed."""
        with self._connection:
            return self._connection.execute('''SELECT count(*) FROM articles WHERE unread = 1 AND feed_id = ?''', [feed.db_id]).fetchone()[0]


    def _get_article_identifiers(self, feed_id: int) -> Dict[str, datetime.datetime]:
        """Returns a set containing all the identifiers of all articles for a feed."""
        articles = {}
        with self._connection:
            for article in self._connection.execute('''SELECT identifier, updated FROM articles WHERE feed_id = ?''', [feed_id]):
                articles[article['identifier']] = datetime.datetime.fromtimestamp(article['updated'], datetime.timezone.utc)
        return articles


    def _add_articles_to_database(self, articles: List[Article], feed_id: int) -> None:
        """Add a list of articles to the database.

        All articles will be marked as unread."""
        with self._connection:
            for article in articles:
                self._connection.execute(
                    '''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    [feed_id, article.identifier, article.uri, article.title, article.updated.timestamp(), article.author, article.content, True, False])


    def _update_feed_with_data(self, feed: Feed, new_feed_data: Feed, articles: List[Article]):
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
                self._connection.execute(
                    '''
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

        if feed.delete_time is not None:
            limit = feed.delete_time
        else:
            limit = self.settings["default_delete_time"]

        if limit == 0:
            date_cutoff = None
        else:
            date_cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=limit)
            self._delete_old_articles(date_cutoff, feed.db_id)

        known_ids = self._get_article_identifiers(feed.db_id)

        new_articles = []
        updated_articles = []
        for article in articles:

            if date_cutoff is not None and article.updated < date_cutoff:
                continue

            if article.identifier in known_ids:
                if known_ids[article.identifier] > article.updated:
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
        with self._connection:
            self._connection.execute('''DELETE from articles WHERE updated < ? and feed_id = ?''', [cutoff_time.timestamp(), feed_id])

