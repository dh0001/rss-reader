import defusedxml.ElementTree as ElemTree
from typing import List
import collections

CompleteFeed = collections.namedtuple('CompleteFeed', ['feed', 'articles'])

class WebFeed:
    """
    class which holds a generic information from a website feed.
    """
    def __init__(self):
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


def _article_append(to: WebFeed, entry):
    """
    Append an Article object corresponding to entry to list of Articles to.
    """
    new_article = Article()
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        _feed_substitute (new_article, piece, atom_article_mapping, tag)
    to.articles.append(new_article)


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


def _feed_substitute(obj, value, dict, key):
    """
    Substitutes the attribute with the name corresponding to the 'dict' in object 'obj' with 'value'.
    """
    if (callable(dict[key])):
        dict[key](obj, value)
    elif (isinstance(dict[key], str)):
        setattr(obj.feed, dict[key], value.text)


def atom_insert(parsed_xml) -> CompleteFeed:
    """
    Takes in parsed xml "parsed_xml" corresponding to an atom feed, and returns a CompleteFeed, containing the Feed and a list of Article.
    """
    new_feed = CompleteFeed
    for child in parsed_xml:
        tag = child.tag.split('}', 1)[1]
        _feed_substitute(new_feed, child, atom_mapping, tag)
    