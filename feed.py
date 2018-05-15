import defusedxml.ElementTree as ElemTree
from typing import List, NamedTuple
import collections

class WebFeed:
    """
    class which holds a generic information from a website feed.
    """
    def __init__(self):
        self.db_id : int
        self.identifier = None
        self.uri = None
        self.title = None
        self.author = None
        self.author_uri = None
        self.category = None
        self.updated = None
        self.icon = None
        self.subtitle = None
        self.feed_meta = None


class Article:
    """
    Generic representation of an article in a feed.
    """
    def __init__(self):
        self.identifier = None
        self.uri = None
        self.title = None
        self.updated = None
        self.author = None
        self.author_uri = None
        self.content = None
        self.category = None
        self.published = None


CompleteFeed = NamedTuple('CompleteFeed', [('feed', WebFeed), ('articles', List[Article])])


def _article_append(to: WebFeed, entry):
    """
    Append an Article object corresponding to entry to list of Articles to.
    """
    new_article = Article()
    for child in entry:
        tag = child.tag.split('}', 1)[1]
        _substitute(new_article, child, atom_article_mapping, tag)
    to.articles.append(new_article)


def _author_cf_insert(to, entry):
    """
    Insert the "name" tag into to.author.
    """
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        if (tag == "name"):
            to.feed.author = piece.text


def _author_insert(to, entry):
    """
    Insert the "name" tag into to.author.
    """
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        if (tag == "name"):
            to.author = piece.text


feed_mapping = {
    "atom" : "atom_mapping"
}

atom_mapping = {
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
    "link" : "uri",
    "summary" : "summary",
    "category" : "category",
    "contributor" : "contributor",
    "published" : "published",
    "rights" : "rights",
    "source" : "source"
}


def _feed_substitute(obj, value, dict, key) -> None:
    """
    Substitutes the attribute with the name corresponding to the 'dict' in object 'obj' with 'value'.
    """
    if (callable(dict[key])):
        dict[key](obj, value)
    elif (isinstance(dict[key], str)):
        setattr(obj.feed, dict[key], value.text)


def _substitute(obj, value, dict, key) -> None:
    """
    Substitutes the attribute with the name corresponding to the 'dict' in object 'obj' with 'value'.
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
        _feed_substitute(new_feed, child, atom_mapping, tag)
    return new_feed