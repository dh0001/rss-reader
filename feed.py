import defusedxml.ElementTree as ElemTree
from typing import List, NamedTuple
import collections

class WebFeed:
    """
    class which holds a generic information from a website feed.
    """
    def __init__(self):
        self.db_id : int = None
        self.uri : str = None   # the id
        self.title : str = None
        self.author : str = None
        self.author_uri : str = None
        self.category : str = None
        self.updated : str = None
        self.icon : str = None
        self.subtitle : str = None
        self.feed_meta : str = None


class Article:
    """
    Generic representation of an article in a feed.
    """
    def __init__(self):
        self.db_id : int = None
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


CompleteFeed = NamedTuple('CompleteFeed', [('feed', WebFeed), ('articles', List[Article])])


def _article_append(append_to: CompleteFeed, entry) -> None:
    """
    Append an Article object to the list of articles in the CompleteFeed
    """
    new_article = Article()
    for child in entry:
        tag = child.tag.split('}', 1)[1]
        _substitute(new_article, child, atom_article_mapping, tag)
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


atom_feed_mapping = {
    "id" : "uri",
    "title" : "title",
    "updated" : "updated",
    "author" : _author_cf_insert,
    "link" : None,
    "category" : "category",
    "contributor" : None,
    "icon" : "icon",
    "logo" : None,
    "rights" : None,
    "subtitle" : "subtitle",
    "entry" : _article_append,
}

atom_article_mapping = {
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


def _cf_feed_substitute(cf: CompleteFeed, value, dict, key) -> None:
    """
    Substitutes the attribute with name corresponding in 'dict' in the feed portion of CompleteFeed 'cf' with 'value'.
    """
    if (callable(dict[key])):
        dict[key](cf, value)
    elif (isinstance(dict[key], str)):
        setattr(cf.feed, dict[key], value.text)


def _substitute(obj, value, dict, key) -> None:
    """
    Substitutes the attribute with name corresponding in 'dict' in object 'obj' with 'value'.
    """
    if (callable(dict[key])):
        dict[key](obj, value)
    elif (isinstance(dict[key], str)):
        setattr(obj, dict[key], value.text)


def atom_parse(parsed_xml) -> CompleteFeed:
    """
    Takes in parsed xml "parsed_xml" corresponding to an atom feed, and returns a CompleteFeed, containing the Feed and a list of Article.
    """
    new_feed = CompleteFeed
    new_feed.feed = WebFeed()
    new_feed.articles = []
    
    for child in parsed_xml:
        tag = child.tag.split('}', 1)[1]
        _cf_feed_substitute(new_feed, child, atom_feed_mapping, tag)
    return new_feed