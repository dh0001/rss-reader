import sqlite3
import requests
import xml.etree.ElementTree as ET



# class which holds a generic information from a website feed.
class WebFeed:
    def __init__(self):
        self.identifier = None
        self.title = None
        self.updated = None
        self.authors = []
        self.links = []
        self.categories = [] 
        self.contributors = []
        self.icon = None
        self.logo = None
        self.rights = Text()
        self.subtitle = None
        self.articles = []
        self.feed_type = None



# stores a hyperlink, and generic data about it
class Link:
    def __init__(self):
        self.href = None
        self.rel = None
        self.media_type = None
        self.hreflang = None
        self.title = None
        self.length = None

# appends a Link object 'entry' to array of links 'to'.
def link_append(to, entry):
    
    new_link = Link()

    for child in entry.attrib:
        setattr(new_link, child.key, child.value)

    to.append(new_link)



# generic representation of an article in a feed.
class Article:
    def __init__(self):
        self.identifier = None
        self.title = None
        self.updated = None
        self.authors = []
        self.content = None
        self.link = None
        self.summary = None
        self.category = []
        self.contributor = None
        self.published = None
        self.rights = None
        self.source = None

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



# generic representation of text content.
class Text:
    def __init__(self):
        self.text = None
        self.encoding = None

# populate the attribute 'index' in 'to' with a Text object 'text'.
def text_insert(to, text, index):

    new_text = Text()

    if (text.attrib.length > 0):
        new_text.encoding = text.attrib
    
    to.attribute(index).text = new_text



# generic representation of a category.
class Category:
    def __init__(self):
        self.term = None
        self.scheme = None
        self.label = None

# append a Category 'category' to list of Category 'to'.
def category_append(to, category):
    
    for key,val in category.attrib.items():
        mapping_substitute(to, val, atom_category_map, key)



# generic representation of content.
class Content:
    def __init__(self):
        self.body = None
        self.content_type = None
        self.source = None

# populate attribute 'index' in 'to' with a Content 'content'.
def content_insert(to, content, index):

    new_content = Content()

    for attr in content.attrib:
        mapping_substitute(new_content, attr.val, atom_content_map, attr.key)

    new_content.body = content.text

    setattr(to, index, new_content)




feed_mapping = {
    "atom" : "atom_mapping"
}

atom_mapping = {
    "id" : "identifier",
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
        title TEXT,
        updated INTEGER,
        author TEXT,
        icon TEXT,
        link TEXT,
        logo TEXT,
        rights TEXT,
        subtitle TEXT,
        feed_type TEXT)''')
    
    c.execute('''CREATE TABLE authors (
        feed_id INTEGER,
        name TEXT,
        uri TEXT,
        email TEXT)''')
    
    c.execute('''CREATE TABLE articles (
        title TEXT,
        updated INTEGER,
        author TEXT,
        content TEXT,
        link TEXT,
        summary TEXT,
        contributor TEXT,
        published INTEGER,
        rights TEXT,
        source TEXT)''')
    
    c.execute('''CREATE TABLE article_authors(
        feed_id INTEGER,
        name TEXT,
        uri TEXT,
        email TEXT)''')
    
    connection.commit()
