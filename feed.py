import defusedxml.ElementTree as ElemTree
from typing import List, NamedTuple, Union
import collections
from itertools import chain

class Feed:
    """
    Holds information from an RSS feed, and additional data.
    """
    def __init__(self):
        self.title : str = None
        self.author : str = None
        self.author_uri : str = None
        self.category : str = None
        self.updated : str = None
        self.icon_uri : str = None
        self.subtitle : str = None
        self.meta : dict = None

        self.db_id : int = None
        self.row : int = None
        self.uri : str = None           # the id
        self.user_title : str = None
        self.parent_folder : Folder = None
        self.unread_count : int = None
        self.refresh_rate : int = None

    def __iter__(self):
            yield self


class FeedData:
    """
    Holds information from an RSS feed.
    """
    def __init__(self):
        self.title : str = None
        self.author : str = None
        self.author_uri : str = None
        self.category : str = None
        self.updated : str = None
        self.icon_uri : str = None
        self.subtitle : str = None
        self.meta : dict = {}


class Article:
    """
    Holds information from an entry/article in an Atom RSS feed.
    """
    def __init__(self):
        self.identifier : str = None    # the id
        self.uri : str = None           # the first link href
        self.title : str = None
        self.updated : str = None
        self.author : str = None
        self.author_uri : str = None
        self.content : str = None
        self.category : str = None
        self.published : str = None
        self.unread : bool = None
        self.meta : dict = None

        self.db_id : int = None
        self.feed_id : int = None


class Folder:
    """
    Class which holds information about folders.
    """
    def __init__(self):
        self.row = None
        self.title = None
        self.parent_folder = None
        self.children = []

    def __iter__(self):
        for child in self.children:
            yield from child
        


CompleteFeed = NamedTuple('CompleteFeed', [('feed', FeedData), ('articles', List[Article])])


def _article_append(append_to: CompleteFeed, entry) -> None:
    """
    Append an Article object to the list of articles in the CompleteFeed
    """
    new_article = Article()
    for child in entry:
        tag = child.tag.split('}', 1)[1]
        _article_substitute(new_article, child, _article_mapping, tag)
    append_to.articles.append(new_article)


def _author_cf_insert(to: CompleteFeed, entry) -> None:
    """
    Insert the "name" tag into to.feed.author.
    """
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        if (tag == "name"):
            to.feed.author = piece.text


def _author_insert(to, entry) -> None:
    """
    Insert the "name" tag entry into to.author.
    """
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        if (tag == "name"):
            to.author = piece.text


def _link_insert(to: Article, entry) -> None:
    """
    Insert the href attribute into to.
    """
    to.uri = entry.attrib['href']


def _feed_substitute(cf: CompleteFeed, value: any, dictionary: dict, key: str) -> None:
    """
    Substitutes the attribute with name corresponding in 'dict' in the feed portion of CompleteFeed 'cf' with 'value'.
    """
    if (callable(dictionary[key])):
        dictionary[key](cf, value)
    elif (isinstance(dictionary[key], str)):
        setattr(cf.feed, dictionary[key], value.text)
    # else:
    #     cf.feed.meta[key] = value


def _article_substitute(obj: object, value: any, dictionary: dict, key: str) -> None:
    """
    Substitutes the attribute with name corresponding in 'dict' in object 'obj' with 'value'.
    """
    if (callable(dictionary[key])):
        dictionary[key](obj, value)
    elif (isinstance(dictionary[key], str)):
        setattr(obj, dictionary[key], value.text)
    # else:
    #     obj.meta[key] = value


_feed_mapping = {
    "id" : None,
    "title" : "title",
    "updated" : "updated",
    "author" : _author_insert,
    "link" : None,
    "category" : "category",
    "contributor" : None,
    "icon" : "icon",
    "logo" : None,
    "rights" : None,
    "subtitle" : "subtitle",
    "entry" : _article_append,
}

_article_mapping = {
    "id" : "identifier",
    "title" : "title",
    "updated" : "updated",
    "author" : _author_insert,
    "content" : "content",
    "link" : _link_insert,
    "summary" : None,
    "category" : "category",
    "contributor" : None,
    "published" : "published",
    "rights" : None,
    "source" : None
}


def atom_parse(parsed_xml) -> CompleteFeed:
    """
    Takes in parsed xml "parsed_xml" corresponding to an atom feed, and returns a CompleteFeed, containing the Feed and a list of Article.
    """
    cf = CompleteFeed
    cf.feed = FeedData()
    cf.articles = []
    
    for child in parsed_xml:
        tag = child.tag.split('}', 1)[1]
        _feed_substitute(cf, child, _feed_mapping, tag)
    return cf
