import sqlite3
from feed import Article
import datetime
import dateutil.parser
import timeit

con_old_articles = sqlite3.connect("articlesold.db")

articles_old = []
for row in con_old_articles.execute('''SELECT * FROM articles'''):
    article = Article()
    article.feed_id = row[0]
    article.identifier = row[1]
    article.uri = row[2]
    article.title = row[3]
    article.updated = dateutil.parser.isoparse(row[4])
    article.author = row[5]
    article.content = row[6]
    article.unread = bool(row[7])
    articles_old.append(article)


con_new_articles = sqlite3.connect("articlesnew.db", detect_types=sqlite3.PARSE_DECLTYPES)
with con_new_articles:
    con_new_articles.execute('''CREATE TABLE IF NOT EXISTS articles (
    feed_id INTEGER,
    identifier TEXT,
    uri TEXT,
    title TEXT,
    updated FLOAT,
    author TEXT,
    content TEXT,
    unread BOOLEAN)''')

    for article in articles_old:
        con_new_articles.execute('''INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        [article.feed_id, article.identifier, article.uri, article.title, article.updated.timestamp(), article.author, article.content, article.unread])


articles_new = []
con_new_articles.row_factory = sqlite3.Row
for row in con_new_articles.execute('SELECT feed_id, identifier, uri, title, updated, author, content, unread FROM articles'):
    article = Article()
    article.feed_id = row['feed_id']
    article.identifier = row['identifier']
    article.uri = row['uri']
    article.title = row['title']
    article.updated = datetime.datetime.fromtimestamp(row['updated'], datetime.timezone.utc)
    article.author = row['author']
    article.content = row['content']
    article.unread = bool(row['unread'])
    articles_new.append(article)

print(bool(articles_new[0].unread))


q = datetime.timedelta(0)

for i,a in enumerate(articles_old):
    if q != a.updated - articles_new[i].updated:
        print("Error detected", q, i)