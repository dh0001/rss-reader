import requests
import xml.etree.ElementTree as ET
import pickle



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




class Link:
    def __init__(self):
        self.href = None
        self.rel = None
        self.media_type = None
        self.hreflang = None
        self.title = None
        self.length = None

def Link_Append(to, entry):
    
    new_link = Link()

    for child in entry.attrib:
        setattr(new_link, child, child)





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

# in WebFeed 'to', append a new Article object corresponding to the xml representation 'entry' to articles.
def Article_Append(to, entry):
    new_article = Article()

    for piece in entry:
        tag = piece.tag.split('}', 1)[1]
        Mapping_Substitute (new_article, piece, atom_article_mapping, tag)
    
    to.articles.append(entry)




class Person:
    def __init__(self):
        self.name = None
        self.uri = None
        self.email = None

# append into the list 'to', a new Person object corresponding to the xml representation 'person'.
def Person_Append(to, person, index):
    new_person = Person()

    for child in person:
        setattr(new_person, child.tag, child.text)

    getattr(to, index).append(new_person)




class Text:
    def __init__(self):
        self.text = None
        self.encoding = None

# populate 'to' using 'text'
def Text_Insert(to, text, index):

    new_text = Text()

    if (text.attrib.length > 0):
        new_text.encoding = text.attrib
    
    to.attribute(index).text = new_text




class Category:
    def __init__(self):
        self.term = None
        self.scheme = None
        self.label = None

def Category_Append(to, category):
    
    for key,val in category.attrib.items():
        Mapping_Substitute(to, val, atom_category_map, key)




class Content:
    def __init__(self):
        self.body = None
        self.content_type = None
        self.source = None

def Content_Insert(to, content, index):

    new_content = Content()

    for attr in content.attrib:
        Mapping_Substitute(new_content, attr.val, atom_content_map, attr.key)

    new_content.body = content.text

    setattr(to, index, new_content)




feed_mapping : {
    "atom" : "atom_mapping"
}

atom_mapping = {
    "id" : "identifier",
    "title" : "title",
    "updated" : "updated",
    "author" : lambda to, piece: Person_Append(to, piece, "authors"),
    "link" : "links",
    "category" : "categories",
    "contributor" : "contributor",
    "icon" : "icon",
    "logo" : "logo",
    "rights" : "rights",
    "subtitle" : "subtitle",
    "entry" : Article_Append,
}

atom_article_mapping = {
    "id" : "identifier",
    "title" : "title",
    "updated" : "updated",
    "author" : lambda to, piece: Person_Append(to, piece, "authors"),
    "content" : "content",
    "link" : "link",
    "summary" : "summary",
    "category" : "categories",
    "contributor" : "contributor",
    "published" : "published",
    "rights" : "rights",
    "source" : "source",
    "entry" : Article_Append,
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
def Mapping_Substitute(to, piece, mapping, map_entry):

    if (callable(mapping[map_entry])):
        mapping[map_entry](to, piece)

    elif (isinstance(mapping[map_entry], str)):
        setattr(to, mapping[map_entry], piece.text)




# insert parsed feed into a WebFeed object.
def Atom_Insert(parsed_xml, feed):
    
    for piece in parsed_xml:
        tag = piece.tag.split('}', 1)[1]

        Mapping_Substitute(feed, piece, atom_mapping, tag)



class Settings():
    def __init__(self):
        feed_list = []



def download_rss_file():
    text_file = open("Output.xml", "w", encoding="utf-8")
    rss_request = requests.get("http://reddit.com/.rss")
    text_file.write(rss_request.text)
    text_file.close()

def load_rss_from_disk():
    with open("Output.xml", "rb") as text_file:
        rss = text_file.read().decode("utf-8")
        return rss

def store_data():
    with open('feed_data.pickle', 'wb') as handle:
        pickle.dump(feed_web_data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_data():
    with open('feed_data.pickle', 'rb') as handle:
        feed_disk_data = pickle.load(handle)
        return feed_disk_data



# create WebFeed object
feed_object = WebFeed()
feed_web_data = ET.fromstring(rss)

Atom_Insert(feed_web_data, feed_object)


feed_disk_data = None
feed_array = []



