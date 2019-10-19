from typing import List, Union
import collections
from itertools import chain
import requests
import defusedxml.ElementTree as defusxml


class Feed:
    """
    Holds information for a feed, and its metadata.
    """

    def __init__(self):
        self.title: str = None
        self.author: str = None
        self.author_uri: str = None
        self.category: str = None
        self.updated: str = None
        self.icon_uri: str = None
        self.subtitle: str = None
        self.meta: dict = {}

        self.db_id: int = None
        self.template: str = None
        self.uri: str = None
        self.user_title: str = None
        self.parent_folder: Folder = None
        self.unread_count: int = None
        self.refresh_rate: int = None

    def __iter__(self):
        yield self


class FeedData:
    """
    Holds information from an RSS feed.
    """

    def __init__(self):
        self.title: str = None
        self.author: str = None
        self.author_uri: str = None
        self.category: str = None
        self.updated: str = None
        self.icon_uri: str = None
        self.subtitle: str = None
        self.meta: dict = {}


class Article:
    """
    Holds information from an entry/article in an Atom RSS feed.
    """

    def __init__(self):
        self.identifier: str = None    # the id
        self.uri: str = None           # the first link href
        self.title: str = None
        self.updated: str = None
        self.author: str = None
        self.author_uri: str = None
        self.content: str = None
        self.category: str = None
        self.published: str = None
        self.unread: bool = None
        self.meta: dict = None

        self.db_id: int = None
        self.feed_id: int = None


class Folder:
    """
    Class which holds information about folders.
    """

    def __init__(self):
        self.title = None
        self.parent_folder = None
        self.children = []

    def __iter__(self):
        for child in self.children:
            yield from child


class CompleteFeed:
    __slots__ = 'feed', 'articles'

    def __init__(self):
        self.feed = FeedData()
        self.articles = []


rss_mapping = {
    # "id": None,
    "title": "title",
    "updated": "updated",
    # "author": author_insert,
    # "link": None,
    "category": "category",
    # "contributor": None,
    "icon": "icon",
    # "logo": None,
    # "rights": None,
    "subtitle": "subtitle",
    # "entry": article_append,
}

rss_article_mapping = {
    "id": "identifier",
    "title": "title",
    "updated": "updated",
    # "author": author_insert,
    "content": "content",
    # "link": link_insert,
    # "summary": None,
    "category": "category",
    # "contributor": None,
    "published": "published",
    # "rights": None,
    # "source": None
}


def rss_template(uri) -> CompleteFeed:

    xml = defusxml.fromstring(download(uri))

    cf = CompleteFeed()

    for child in xml:
        tag = child.tag.split('}', 1)[1]

        if tag in rss_mapping:
            setattr(cf.feed, rss_mapping[tag], child.text)

        elif tag == 'author':
            author_insert(cf.feed, child)

        elif tag == 'entry':

            article = Article()
            for articlechild in child:

                tag = articlechild.tag.split('}', 1)[1]

                if tag in rss_article_mapping:
                    setattr(article, rss_article_mapping[tag], articlechild.text)

                elif tag == 'link':
                    article.uri = articlechild.attrib['href']

                elif tag == 'author':
                    author_insert(article, articlechild)

            cf.articles.append(article)

        else:
            cf.feed.meta[tag] = child.text

    return cf


templates = {
    "rss": rss_template
}


def download(uri: str) -> any:
    """
    Downloads text file with the application's header.
    """
    headers = {'User-Agent' : 'python-rss-reader'}
    return requests.get(uri, headers=headers).text
    

def get_feed(uri, template):
    return templates[template](uri)


def author_insert(to, entry) -> None:
    """
    Insert the "name" tag entry into to.author.
    """
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        if (tag == "name"):
            to.author = piece.text
