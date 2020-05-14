from typing import List, Union, Tuple
import collections
from itertools import chain
import requests
import defusedxml.ElementTree as defusxml


class Feed:
    """Holds information for a feed, and its metadata."""

    def __init__(self):
        self.title: str = None
        self.meta: dict = {}

        # attributes used by feed_manager
        self.updated: str = None    # TODO should there be a last fetch time and an updated attribute?
        self.db_id: int = None
        self.template: str = None
        self.uri: str = None
        self.user_title: str = None
        self.parent_folder: Folder = None
        self.refresh_rate: int = None
        

    def __iter__(self):
        yield self


    def update(self, feed: 'Feed'):
        self.title = feed.title
        self.meta.update(feed.meta)


class Article:
    """Holds information from an entry/article in an Atom RSS feed."""

    def __init__(self):
        self.identifier: str = None
        self.title: str = None
        self.updated: str = None
        self.content: str = None
        self.author: str = None
        self.uri: str = None
        self.meta: dict = {}

        # attributes used by feed_manager
        self.feed_id: int = None
        self.unread: bool = None


class Folder:
    """Class which holds information about folders for use in feed_manager."""

    def __init__(self):
        self.title = None
        self.parent_folder = None
        self.children = []

    def __iter__(self):
        for child in self.children:
            yield from child


# def rss_template(uri: str) -> Tuple[Feed, List[Article]]:
#     """RSS data reader for the feed reader.

#     The uri of an article is set to the first uri tag that appears in the article.
#     """

#     def parse_author(author) -> dict:
#         """Returns a dict with data for an author."""
#         a = {}
#         for tag in author:
#             a[tag.tag.split('}', 1)[1]] = tag.text
#         return a

#     rss_article_mapping={
#     "id": "identifier",
#     "title": "title",
#     "updated": "updated",
#     "content": "content",
#     "category": "category",
#     "published": "published",
#     }

#     xml = defusxml.fromstring(download(uri).text)

#     feed = Feed()
#     articles = []

#     # feed
#     for feed_tag in xml:
#         tag_name = feed_tag.tag.split('}', 1)[1]

#         if tag_name == "title":
#             feed.title = feed_tag.text

#         elif tag_name == 'author':
#             feed.meta["author"] = parse_author(feed_tag)

#         # article
#         elif tag_name == 'entry':

#             article = Article()
#             for article_tag in feed_tag:

#                 article_tag_name = article_tag.tag.split('}', 1)[1]

#                 if article_tag_name in rss_article_mapping:
#                     setattr(article, rss_article_mapping[article_tag_name], article_tag.text)

#                 elif article_tag_name == 'link':
#                     article.uri = article_tag.attrib['href']

#                 elif article_tag_name == 'author':
#                     article.author = parse_author(article_tag)["name"]

#                 else:
#                     article.meta[article_tag_name] = feed_tag.text

#             articles.append(article)

#         else:
#             feed.meta[tag_name] = feed_tag.text

#     return feed, articles


def atom_rss_template(uri: str) -> Tuple[Feed, List[Article]]:
    """Atom RSS data reader for the feed reader.

    The uri/author of an article is set to the first link/author tag found.
    """
    xml_feed = defusxml.fromstring(download(uri).text)

    feed = Feed()
    feed.title = xml_feed.find("{http://www.w3.org/2005/Atom}title").text

    # author
    top_author = xml_feed.find("{http://www.w3.org/2005/Atom}author")
    if top_author is not None:
        top_author = top_author.find("{http://www.w3.org/2005/Atom}name").text
    else:
        top_author = ""

    articles = []
    xml_articles = xml_feed.findall("{http://www.w3.org/2005/Atom}entry")
    for xml_article in xml_articles:
        article = Article()

        # article author
        author = xml_article.find("{http://www.w3.org/2005/Atom}author")
        if author is not None:
            article.author = author.find("{http://www.w3.org/2005/Atom}name").text
        else:
            author = top_author
        
        article.identifier = xml_article.find("{http://www.w3.org/2005/Atom}id").text
        article.title = xml_article.find("{http://www.w3.org/2005/Atom}title").text
        article.updated = xml_article.find("{http://www.w3.org/2005/Atom}updated").text
        article.content = xml_article.find("{http://www.w3.org/2005/Atom}content").text
        article.uri = xml_article.find("{http://www.w3.org/2005/Atom}link").attrib["href"]
        articles.append(article)

    return feed, articles


templates = {
    "rss": atom_rss_template
}


def download(uri: str) -> any:
    """Downloads text file with the application's header."""
    headers = {'User-Agent' : 'python-rss-reader'}
    return requests.get(uri, headers=headers)
    

def get_feed(uri, template):
    """"""
    return templates[template](uri)


if __name__ == "__main__":
    a = get_feed("https://www.reddit.com/.rss", "rss")