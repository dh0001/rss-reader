import sqlite3
import requests
import defusedxml.ElementTree as EleTree
import feed


def create_tables(connection):
    c = connection.cursor()
    c.execute('''CREATE TABLE feeds (
        uri TEXT,
        title TEXT,
        author TEXT,
        author_uri TEXT,
        category TEXT,
        updated INTEGER,
        icon_uri TEXT,
        subtitle TEXT,
        feed_meta TEXT)''')
    c.execute('''CREATE TABLE entries (
        feed_id INTEGER,
        uri TEXT
        title TEXT,
        updated INTEGER,
        author TEXT,
        author_uri TEXT,
        content TEXT,
        published INTEGER)''')
    connection.commit()


def download_rss_file(uri):
    return requests.get(uri)

def write_string_to_file(str):
    text_file = open("Output.xml", "w", encoding="utf-8")
    text_file.write(str)
    return

def load_rss_from_disk(f):
    with open(f, "rb") as file:
        rss = file.read().decode("utf-8")
        return rss


feeds = None

def init():
    return

def add_atom_file(file):
    data = download_rss_file(file)
    feed.atom_insert(EleTree.fromstring(data), feeds)
