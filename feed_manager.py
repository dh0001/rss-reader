from copy import copy
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Dict
import os
import logging

from PySide6 import QtCore as qtc

from feed import ArticleData, Feed, Article, FeedData, Folder, get_feed
from feed_updater import UpdateThread
from settings import settings


class FeedManager(qtc.QObject):
    """Manages the feed data and provides an interface for getting that data."""

    new_article_event: qtc.Signal = qtc.Signal(Article)
    article_updated_event: qtc.Signal = qtc.Signal(Article)
    feeds_updated_event: qtc.Signal = qtc.Signal()

    def __init__(self):
        super().__init__()

        def traverse_dict_output_folder(node: dict[str, Any], parent: Folder):
            # its a folder
            if "children" in node:
                folder = Folder(node["title"], parent)
                for child in node["children"]:
                    folder.children.append(traverse_dict_output_folder(child, folder))
                return folder
            # its a feed
            else:
                feed = Feed(parent)
                
                if node["updated"] == None:
                    node["updated"] = datetime.fromtimestamp(0)
                else:
                    node["updated"] = datetime.fromisoformat(node["updated"])
                
                feed.update(node)
                return feed

        if not os.path.exists("feeds.json"):
            with open("feeds.json", "w") as _new_file:
                _new_file.write("[]")

        with open("feeds.json", "rb") as _feeds_file:
            contents = _feeds_file.read().decode("utf-8")
        
        self.feed_cache = Folder("root")
        """feed_cache is a folder, and the 'root' folder for the feed manager.
        Currently done like this for easier setting of parents, adding to folder, and refresh."""

        feed_dict: list[dict[str, Any]] = json.loads(contents)
        for item in feed_dict:
            self.feed_cache.children.append(traverse_dict_output_folder(item, self.feed_cache))


        self._sqlite_connection = sqlite3.connect(settings.db_file)
        self._sqlite_connection.row_factory = sqlite3.Row

        # create and start scheduler thread
        self._update_thread = UpdateThread(self.feed_cache, settings)

        self._initialize_database()

        self._update_thread.data_downloaded_event.connect(self._handle_data_downloaded)
        self._update_thread.start()

        if settings.startup_update is True:
            self.refresh_all()


    def cleanup(self) -> None:
        """Closes db connection and exits threads gracefully."""

        self._update_thread.requestInterruption()
        self._update_thread.schedule_update_event.set()
        if self._update_thread.wait(1) is False:
            logging.info("not enough time to stop thread 0.5")
        self._save_feeds()
        self._sqlite_connection.close()


    def get_articles(self, feed_id: int) -> List[Article]:
        """Returns a list containing all the articles with feed_id.

        Args:
            feed_id: The id of the feed to return articles from.

        Returns:
            A list of articles with the corresponding feed_id.
        """
        articles = []
        for row in self._sqlite_connection.execute('SELECT identifier, uri, title, updated, author, content, unread, flag FROM articles WHERE feed_id = ? ORDER BY updated DESC LIMIT 200', [feed_id]):
            data = ArticleData()
            data.identifier = row['identifier']
            data.uri = row['uri']
            data.title = row['title']
            data.updated = datetime.fromtimestamp(row['updated'], timezone.utc)
            data.author = row['author']
            data.content = row['content']
            data.unread = bool(row['unread'])
            data.flag = bool(row['flag'])
            articles.append(Article(data))
        return articles


    def add_feed(self, location: str, folder: Folder, analyzer: str) -> None:
        """Adds a feed to the folder."""

        feeddata, articledata = get_feed(location, analyzer)

        feeddata.db_id = settings.feed_counter
        feeddata.uri = location
        feeddata.template = analyzer
        feed = Feed(folder, feeddata)

        folder.children.append(feed)
        self.feeds_updated_event.emit()

        self._add_articles_to_db(feed, articledata)

        settings.feed_counter += 1
        self._save_feeds()


    def delete_feed(self, feed: Feed) -> None:
        """Removes a feed from the feed_manager.

        Removes a feed with passed feed_id, and its entry from the refresh schedule.
        """
        if feed.refresh_rate is not None:
            self._update_thread.remove_feed(feed)

        assert feed.parent_folder.children.index(feed) != -1, "Folder was not found when trying to delete it!"
        del feed.parent_folder.children[feed.parent_folder.children.index(feed)]
        self._save_feeds()


    def add_folder(self, folder_name: str, folder: Folder) -> None:
        """Adds a folder."""
        new_folder = Folder(folder_name, folder)
        folder.children.append(new_folder)
        self._save_feeds()


    def delete_folder(self, folder: Folder) -> None:
        """Deletes a folder."""

        def delete_feeds_in_folder(folder: Folder) -> None:
            """Deletes all feeds in a folder recursively."""
            for child in folder.children:
                if type(child) is Feed:
                    self.delete_feed(child)
                elif type(child) is Folder: # TODO: check if narrowing works now
                    delete_feeds_in_folder(child)

        delete_feeds_in_folder(folder)
        if folder.parent_folder:
            folder.parent_folder.children.remove(folder)

        self._save_feeds()


    def rename_folder(self, name: str, folder: Folder) -> None:
        """Changes the name of a folder."""
        folder.title = name
        self._save_feeds()


    def refresh_all(self) -> None:
        """Schedules all feeds to be refreshed."""
        self._update_thread.force_refresh_folder(self.feed_cache)


    def refresh_feed(self, feed: Feed) -> None:
        """Schedules a feed to be refreshed."""
        self._update_thread.force_refresh_feed(feed)


    def set_article_unread_status(self, feed: Feed, article: Article, status: bool) -> None:
        """Sets the unread status in the article, and in the database.

        Also updates the feed's unread_count, and emits an event for this.
        Does not do anything if the status is not different.
        """
        if article.unread != status:
            article.unread = status
            with self._sqlite_connection:
                self._sqlite_connection.execute('''UPDATE articles SET unread = ? WHERE identifier = ? and feed_id = ?''', [status, article.identifier, article.feed_id])
            feed.unread_count = self._get_unread_articles_count(feed)
            self.feeds_updated_event.emit()


    def toggle_article_flag(self, article: Article) -> None:
        """Inverts flag status on an article."""
        article.flag = not article.flag
        with self._sqlite_connection:
            self._sqlite_connection.execute('''UPDATE articles SET flag = ? WHERE identifier = ? and feed_id = ?''', [article.flag, article.identifier, article.feed_id])


    def set_default_refresh_rate(self, rate: int) -> None:
        """Sets the default refresh rate for feeds and resets the scheduled default refresh."""
        self._update_thread.update_global_refresh_rate(rate)


    def update_feed(self, feed: Feed, data: FeedData) -> None:
        """Sets properties for all feeds.

        Will check if value is same as previous value, and will not update if that is the case.
        Saves feed changes to disk."""
        old_refresh_rate = feed.refresh_rate

        feed.update(data)
        if old_refresh_rate != data.refresh_rate:
            self._update_thread.update_refresh_rate(feed, data.refresh_rate)
        self._save_feeds()
        self.feeds_updated_event.emit()


    def _initialize_database(self) -> None:
        """Creates all the tables used."""
        with self._sqlite_connection:
            self._sqlite_connection.execute('''CREATE TABLE IF NOT EXISTS articles (
                feed_id INTEGER,
                identifier TEXT,
                uri TEXT,
                title TEXT,
                updated FLOAT,
                author TEXT,
                content TEXT,
                unread BOOLEAN,
                flag BOOLEAN)''')


    def _save_feeds(self):
        """Saves the feeds to disk."""

        def default(o: Feed | Folder):
            if type(o) is Feed:
                feed = copy(o)
                data = vars(feed)
                data["updated"] = feed.updated.isoformat()
                data.pop("parent_folder")
                return data
            elif type(o) is Folder:
                folder = copy(o)
                data = vars(folder)
                data.pop("parent_folder")
                return data

        content = json.dumps(self.feed_cache.children, default=default, indent=4)
        with open("feeds.json", "w") as feeds_file:
            feeds_file.write(content)


    def _get_unread_articles_count(self, feed: Feed) -> int:
        """Return the number of unread articles for a feed."""
        with self._sqlite_connection:
            return self._sqlite_connection.execute('''SELECT count(*) FROM articles WHERE unread = 1 AND feed_id = ?''', [feed.db_id]).fetchone()[0]


    def _get_article_identifiers(self, feed_id: int) -> Dict[str, datetime]:
        """Returns a dict containing all the identifiers of all articles for a feed."""
        articles = {}
        with self._sqlite_connection:
            for article in self._sqlite_connection.execute('''SELECT identifier, updated FROM articles WHERE feed_id = ?''', [feed_id]):
                articles[article['identifier']] = datetime.fromtimestamp(article['updated'], timezone.utc)
        return articles


    def _handle_data_downloaded(self, feed: Feed, new_feed_data: FeedData, articles: List[ArticleData]):
        """Recieves updated or new feed data."""
        feed.update(new_feed_data)

        self._add_articles_to_db(feed, articles)
        self.feeds_updated_event.emit()


    def _update_articles(self, articles: list[Article]):
        """Updates multiple existing articles in the database."""
        with self._sqlite_connection:
            for article in articles:
                self._sqlite_connection.execute(
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


    def _add_articles_to_db(self, feed: Feed, articles: list[ArticleData]):
        """Processes newly created articles for the feed, and adds them to the database.

        Checks for and delete old articles in the list, and delete old aricles in the database.
        If the article already exists in the database, will update it instead of adding.
        Will also update the unread count on the feed."""

        if feed.delete_time is not None:
            delete_time = feed.delete_time
        else:
            delete_time = settings.default_delete_time

        if delete_time == 0:
            date_cutoff = None
        else:
            date_cutoff = datetime.now(timezone.utc) - timedelta(minutes=delete_time)
            # Deletes articles in the database which are not after the passed time_limit.
            with self._sqlite_connection:
                self._sqlite_connection.execute('''DELETE from articles WHERE updated < ? and feed_id = ?''', [date_cutoff.timestamp(), feed.db_id])


        known_ids = self._get_article_identifiers(feed.db_id)

        new_articles = []
        updated_articles = []
        for articledata in articles:

            article = Article(articledata)

            if date_cutoff is not None and article.updated < date_cutoff:
                continue

            if article.identifier in known_ids:
                if known_ids[article.identifier] > article.updated:
                    updated_articles.append(article)

            else:
                self.new_article_event.emit(article)
                new_articles.append(article)

        self._update_articles(updated_articles)
        map(self.article_updated_event.emit, updated_articles)

        # add the articles to the database.
        with self._sqlite_connection:
            for article in new_articles:
                self._sqlite_connection.execute(
                    '''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    [feed.db_id, article.identifier, article.uri, article.title, article.updated.timestamp(), article.author, article.content, True, False])

        feed.unread_count = self._get_unread_articles_count(feed)
