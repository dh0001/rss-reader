from datetime import datetime
import webbrowser
from feed import Article, ArticleData, FeedData
from analyzers.util import download

import dateutil.parser
import defusedxml.ElementTree as defusxml

from util import check_type


def open_feed_uri_in_browser(article: Article):
    if article.uri is not None:
        webbrowser.open(article.uri)


def atom_rss_template(uri: str) -> tuple[FeedData, list[ArticleData]]:
    """Atom RSS data reader for the feed reader.

    The uri/author of an article is set to the first link/author tag found.
    """
    xml_feed = defusxml.fromstring(download(uri).text)  # type: ignore

    feed = FeedData()
    feed.meta = {}

    # feed required
    feed.title = check_type(str, xml_feed.find("{http://www.w3.org/2005/Atom}title").text)
    feed.updated = datetime.now()
    feed.meta["updated"] = check_type(str, xml_feed.find("{http://www.w3.org/2005/Atom}updated").text)
    feed.meta["id"] = check_type(str, xml_feed.find("{http://www.w3.org/2005/Atom}title").text)

    # feed recommended
    feed_author = "no author"
    top_author = xml_feed.find("{http://www.w3.org/2005/Atom}author")
    if top_author is not None:
        feed_author = check_type(str, top_author.find("{http://www.w3.org/2005/Atom}name").text)

    # articles
    articles = []
    xml_articles = xml_feed.findall("{http://www.w3.org/2005/Atom}entry")
    for xml_article in xml_articles:
        article = ArticleData()

        author = xml_article.find("{http://www.w3.org/2005/Atom}author")
        if author is not None:
            article.author = check_type(str, author.find("{http://www.w3.org/2005/Atom}name").text)
        else:
            article.author = feed_author

        # required for atom rss
        article.identifier = check_type(str, xml_article.find("{http://www.w3.org/2005/Atom}id").text)
        article.title = check_type(str, xml_article.find("{http://www.w3.org/2005/Atom}title").text)
        article.updated = dateutil.parser.isoparse(check_type(str, xml_article.find("{http://www.w3.org/2005/Atom}updated").text))

        # optional for atom rss
        content = xml_article.find("{http://www.w3.org/2005/Atom}content")
        article.content = check_type(str, content.text) if content is not None else ""

        link = xml_article.find("{http://www.w3.org/2005/Atom}link")
        article.uri = check_type(str, link.attrib["href"]) if content is not None else ""

        articles.append(article)

    return feed, articles


templates = {
    "rss": atom_rss_template,
}

actions = {
    "rss": open_feed_uri_in_browser,
}
