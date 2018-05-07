
import feed
import sql_feed_manager

class View():


    def __init__(self, feed_mgr:sql_feed_manager.FeedManager):
        self.feed_manager : sql_feed_manager.FeedManager
        self.feed_manager = feed_mgr



    def std_output(self):
        feeds = self.feed_manager.get_feeds()
        for feed in feeds:
            print ("Feed: ", feed.title)
            for article in feed.articles:
                print ("Article: ", article.title, "By: ", article.author)


    def console_ui(self):
        while(1):
            self.std_output()
            command = input("> ")
            if (command == "refresh"):
                self.feed_manager.refresh()
            elif (command == "exit"):
                return
            else:
                print("Invalid Command.")