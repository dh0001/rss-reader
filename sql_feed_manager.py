import sqlite3
import requests
import xml.etree.ElementTree as ET



# class which holds a generic information from a website feed.
class WebFeed:
    def __init__(self):
        self.identifier = None
        self.uri = None
        self.title = None
        self.author = None
        self.author_uri = None
        self.updated = None
        self.icon = None
        self.subtitle = None
        self.feed_meta = None


# generic representation of an article in a feed.
class Article:
    def __init__(self):
        self.identifier = None
        self.feed_id = None
        self.uri = None
        self.title = None
        self.updated = None
        self.author = None
        self.author_uri = None
        self.content = None
        self.category = []
        self.published = None

# Append an Article object corresponding to entry to list of Articles to.
def article_append(to, entry):
    new_article = Article()

    for piece in entry:

        # 
        tag = piece.tag.split('}', 1)[1]
        mapping_substitute (new_article, piece, atom_article_mapping, tag)
    
    to.articles.append(entry)



# generic representation of a person, ie author, contributor.
class Person:
    def __init__(self):
        self.name = None
        self.uri = None
        self.email = None

# append into the list 'to', a new Person object corresponding to the xml representation 'person'.
def person_append(to, person, index):
    new_person = Person()

    for child in person:
        setattr(new_person, child.tag, child.text)

    getattr(to, index).append(new_person)




feed_mapping = {
    "atom" : "atom_mapping"
}

atom_mapping = {
    "id" : "uri",
    "title" : "title",
    "updated" : "updated",
    "author" : lambda to, piece: person_append(to, piece, "authors"),
    "link" : "links",
    "category" : "categories",
    "contributor" : "contributor",
    "icon" : "icon",
    "logo" : "logo",
    "rights" : "rights",
    "subtitle" : "subtitle",
    "entry" : article_append,
}

atom_article_mapping = {
    "id" : "identifier",
    "title" : "title",
    "updated" : "updated",
    "author" : lambda to, piece: person_append(to, piece, "authors"),
    "content" : "content",
    "link" : "link",
    "summary" : "summary",
    "category" : "categories",
    "contributor" : "contributor",
    "published" : "published",
    "rights" : "rights",
    "source" : "source",
    "entry" : article_append,
}

atom_category_map={
    "term" : "term",
    "scheme" : "scheme",
    "label" : "label",
}

atom_person_map = {
    "name" : "name",
    "uri" :  "uri",
    "email" : "email",
}

atom_content_map = {
    "src" : "source",
    "type" : "content_type",
}

# substitute the 'map_entry' attribute in object 'to', with 'piece' using the mapping 'mapping'
def mapping_substitute(to, piece, mapping, map_entry):

    if (callable(mapping[map_entry])):
        mapping[map_entry](to, piece)

    elif (isinstance(mapping[map_entry], str)):
        setattr(to, mapping[map_entry], piece.text)




# insert parsed feed into a WebFeed object.
def Atom_Insert(parsed_xml, feed):
    
    for piece in parsed_xml:
        tag = piece.tag.split('}', 1)[1]

        mapping_substitute(feed, piece, atom_mapping, tag)



class Settings():
    def __init__(self):
        feed_list = []







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
