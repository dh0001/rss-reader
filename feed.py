import defusedxml.ElementTree as ElemTree
from typing import List

# 
def _article_append(to, entry):
    """
    Append an Article object corresponding to entry to list of Articles to.
    """
    new_article = Article()
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        mapping_substitute (new_article, piece, atom_article_mapping, tag)
    to.articles.append(new_article)


def _author_insert(to, entry):
    """
    Insert the "name" tag into to.author.
    """
    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        if (tag == "name"):
            to.author = piece.text


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


def mapping_substitute(obj, value, dict, key):
    """
    Generic function substituting the attribute with name 'key' in object 'obj' with 'value'.
    """
    if (callable(dict[key])):
        dict[key](obj, value)
    elif (isinstance(dict[key], str)):
        setattr(obj, dict[key], value.text)


def atom_insert(parsed_xml, feed):
    """
    insert parsed feed into a WebFeed object.
    """
    for piece in parsed_xml:
        tag = piece.tag.split('}', 1)[1]
        mapping_substitute(feed, piece, atom_mapping, tag)