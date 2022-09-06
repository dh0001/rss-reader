from __future__ import annotations
from datetime import datetime

import importlib.util
from pathlib import Path

from typing import Any, Callable, Iterator

from util import check_type

DEFAULT_TIME = datetime.fromtimestamp(0)

class Feed():
    """Holds information for a feed, and its metadata."""

    def __init__(self, parent_folder: Folder, data: FeedData | None = None):
        """Initialize a feed with all of its required elements."""
        # feed data
        self.title: str = "untitled feed"
        "Contains a human readable title for the feed. Often the same as the title of the associated website. This value should not be blank. "

        self.meta: dict[str, Any] = {}
        "Any metadata the feed uses."

        self.updated: datetime = DEFAULT_TIME   # TODO this value currently unused. Does it even matter when it was last updated?
        "Indicates the last time the feed was modified in a significant way."

        self.db_id: int = -1
        self.template: str = "undefined"
        self.uri: str = "undefined"

        # user set
        self.user_title: str | None = None
        self.parent_folder: Folder = parent_folder
        self.refresh_rate: int | None = None
        self.ignore_new: bool = False
        self.delete_time: int | None = None
        self.unread_count: int = 0

        if data:
            self.update(data)
            self.type_check()


    def __iter__(self):
        yield self


    def update(self, data: FeedData | dict[str, Any]):
        """Update the feed with new values."""
        if type(data) is dict:
            vars(self).update(data)
        else:
            vars(self).update(vars(data))
        self.type_check()


    def type_check(self):
        """Checks types of the members. Ensure that they all exist, and are valid."""
        # feed data
        check_type(str, self.title)
        check_type(dict[str, Any], self.meta)
        check_type(datetime, self.updated)

        check_type(int, self.db_id)
        check_type(str, self.template)
        check_type(str, self.uri)

        # user set
        check_type(str | None, self.user_title)
        check_type(Folder, self.parent_folder)
        check_type(int | None, self.refresh_rate)
        check_type(bool, self.ignore_new)
        check_type(int | None, self.delete_time)
        check_type(int, self.unread_count)


class FeedData(Feed):
    def __init__(self):
        pass


class Article():
    """Holds information from an entry/article in an Atom RSS feed."""

    def __init__(self, data: ArticleData | None = None):

        self.identifier: str = "article id"
        self.title: str = "untitled article"
        self.updated: datetime = datetime.min
        self.content: str = "no content"
        self.author: str = "no author"
        self.uri: str | None = None
        self.meta: dict[str, Any] = {}

        # attributes used by feed_manager
        self.feed_id: int = -1
        self.unread: bool = True
        self.flag: bool = False

        if data:
            self.update(data)


    def update(self, data: ArticleData | dict[str, Any]):
        """Update the feed with new values."""
        if type(data) is dict:
            vars(self).update(data)
        else:
            vars(self).update(vars(data))
        self.type_check()


    def type_check(self):
        check_type(str, self.identifier)
        check_type(str, self.title)
        check_type(datetime, self.updated)
        check_type(str, self.content)
        check_type(str, self.author)
        check_type(str | None, self.uri)
        check_type(dict[str, Any], self.meta)

        # attributes used by feed_manager
        check_type(int, self.feed_id)
        check_type(bool, self.unread)
        check_type(bool, self.flag)


class ArticleData(Article):
    """Class for storing Feed attributes in a dictionary."""
    def __init__(self):
        pass



class Folder:
    """Class which holds information about folders for use in feed_manager."""

    def __init__(self,
                 title: str,
                 parent_folder: Folder | None = None,
                 children: list[Feed | Folder] | None = None):

        self.title: str = title
        self.parent_folder = parent_folder
        self.children: list[Feed | Folder] = [] if children is None else children


    def __iter__(self) -> Iterator[Feed]:
        """Iterate over a folder returns feeds in the folder recursively."""
        for child in self.children:
            yield from child

analyzer = Callable[[str], tuple[FeedData, list[ArticleData]]]
action = Callable[[Article], Any]
analyzers: dict[str, analyzer] = {}
actions: dict[str, action] = {}


for analyzer_file in Path("analyzers").glob("analyzer-*"):
    spec = importlib.util.spec_from_file_location("", analyzer_file)
    if spec is None or spec.loader is None:
        raise Exception("cannot import analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    analyzers.update(check_type(dict[str, analyzer], module.templates))
    actions.update(check_type(dict[str, action], module.actions))


def get_feed(uri: str, template: str) -> tuple[FeedData, list[ArticleData]]:
    """Retrives and processes data for a feed from the internet."""
    return analyzers[template](uri)


def apply_action(feed: Feed, article: Article):
    actions[feed.template](article)


def verify_feed_url(url: str) -> bool:
    """Verifies if a url points to a proper feed."""
    try:
        get_feed(url, "rss")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # test = get_feed("https://www.reddit.com/.rss", "rss")
    test = get_feed("https://www.youtube.com/feeds/videos.xml?channel_id=UC18NaGQLruOEw65eQE3bNbg", "rss")
    pass
