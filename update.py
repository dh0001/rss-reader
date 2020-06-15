import sqlite3
import datetime

from feed import Article

con_old_articles = sqlite3.connect("articlesold.db")

articles_old = []
con_old_articles.row_factory = sqlite3.Row
for row in con_old_articles.execute('SELECT feed_id, identifier, uri, title, updated, author, content, unread FROM articles'):
    article = Article()
    article.feed_id = row['feed_id']
    article.identifier = row['identifier']
    article.uri = row['uri']
    article.title = row['title']
    article.updated = datetime.datetime.fromtimestamp(row['updated'], datetime.timezone.utc)
    article.author = row['author']
    article.content = row['content']
    article.unread = bool(row['unread'])
    # article.flag = bool(row['flag'])
    articles_old.append(article)


con_new_articles = sqlite3.connect("articlesnew.db")
with con_new_articles:
    con_new_articles.execute('''CREATE TABLE IF NOT EXISTS articles (
    feed_id INTEGER,
    identifier TEXT,
    uri TEXT,
    title TEXT,
    updated FLOAT,
    author TEXT,
    content TEXT,
    unread BOOLEAN,
    flag BOOLEAN)''')

    for article in articles_old:
        con_new_articles.execute(
            '''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [article.feed_id, article.identifier, article.uri, article.title, article.updated.timestamp(), article.author, article.content, article.unread, False])


articles_new = []
con_new_articles.row_factory = sqlite3.Row
for row in con_new_articles.execute('SELECT feed_id, identifier, uri, title, updated, author, content, unread, flag FROM articles'):
    article = Article()
    article.feed_id = row['feed_id']
    article.identifier = row['identifier']
    article.uri = row['uri']
    article.title = row['title']
    article.updated = datetime.datetime.fromtimestamp(row['updated'], datetime.timezone.utc)
    article.author = row['author']
    article.content = row['content']
    article.unread = bool(row['unread'])
    article.flag = bool(row['flag'])
    articles_new.append(article)
