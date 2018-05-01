

# Append an Article object corresponding to entry to list of Articles to.
def article_append(to, entry):
    new_article = Article()

    for piece in entry:

        # 
        tag = piece.tag.split('}', 1)[1]
        mapping_substitute (new_article, piece, atom_article_mapping, tag)
    
    to.articles.append(entry)

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


feed_mapping = {
    "atom" : "atom_mapping"
}

atom_mapping = {
    "id" : "uri",
    "title" : "title",
    "updated" : "updated",
    "author" : "author",
    "link" : None,
    "category" : "category",
    "contributor" : None,
    "icon" : "icon",
    "logo" : None,
    "rights" : None,
    "subtitle" : "subtitle",
    "entry" : article_append,
}

atom_article_mapping = {
    "id" : "identifier",
    "title" : "title",
    "updated" : "updated",
    "author" : "author",
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







# substitute the 'map_entry' attribute in object 'to', with 'piece' using the mapping 'mapping'
def mapping_substitute(to, piece, mapping, map_entry):

    if (callable(mapping[map_entry])):
        mapping[map_entry](to, piece)

    elif (isinstance(mapping[map_entry], str)):
        setattr(to, mapping[map_entry], piece.text)


# insert parsed feed into a WebFeed object.
def atom_insert(parsed_xml, feed):
    
    for piece in parsed_xml:
        tag = piece.tag.split('}', 1)[1]

        mapping_substitute(feed, piece, atom_mapping, tag)