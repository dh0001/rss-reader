
import feed
import sql_feed_manager
import settings

class View():


    def __init__(self, feed_mgr:sql_feed_manager.FeedManager, settings:settings.Settings):
        self.feed_manager : sql_feed_manager.FeedManager
        self.feed_manager = feed_mgr
        self.settings_manager = settings



    def std_output(self):
        feeds = self.feed_manager.get_feeds()
        for feed in feeds:
            print ("Feed: ", feed.title)
            print ("Last Updated: ", feed.updated)
 

    def console_ui(self):
        while(1):
            self.std_output()
            command = input("> ")
            if (command == "refresh"):
                self.feed_manager.refresh()
            elif (command == "exit"):
                return
            elif (command == "add"):
                feed = input("add feed > ")
                self.feed_manager.add_feed_from_web(feed)
            elif (command == "delete"):
                feed = input("delete feed > ")
                self.feed_manager.delete_feed(feed)
            else:
                print("Invalid Command.")