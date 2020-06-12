from typing import List, Union, Tuple
import requests
import defusedxml.ElementTree as defusxml
import dateutil.parser


class Feed:
    """Holds information for a feed, and its metadata."""

    def __init__(self):
        self.title: str = None
        self.meta: dict = {}

        # attributes used by feed_manager
        self.updated: str = None    # TODO this value currently unused. should there be a last fetch time and an updated attribute?
        self.db_id: int = None
        self.template: str = None
        self.uri: str = None
        self.user_title: Union[str, None] = None
        self.parent_folder: Folder = None
        self.refresh_rate: Union[int, None] = None
        self.ignore_new: bool = False
        self.delete_time: Union[int, None] = None


    def __iter__(self):
        yield self


    def update(self, feed: 'Feed'):
        """Updates the feed with new values, except values used by the feed manager."""
        self.title = feed.title
        self.meta.update(feed.meta)


class Article:
    """Holds information from an entry/article in an Atom RSS feed."""

    def __init__(self):
        self.identifier: str = None
        self.title: str = None
        self.updated = None
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
        """iterating over a folder returns feeds in the folder recursively."""
        for child in self.children:
            yield from child


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
        article.updated = dateutil.parser.isoparse(xml_article.find("{http://www.w3.org/2005/Atom}updated").text)
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


def get_feed(uri, template) -> Feed:
    """Retrives and processes data for a feed from the internet."""
    return templates[template](uri)


if __name__ == "__main__":
    test = get_feed("https://www.reddit.com/.rss", "rss")
