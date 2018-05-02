
import feed

class View():

    feed_manager = None

    def __init__(self, feed_mgr):
        self.feed_manager = feed_mgr



    def output(self):
        feeds = self.feed_manager.get_feeds()
        for feed in feeds:
            print (feed.title)
            for article in feed.articles:
                print (article.title)