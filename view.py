import feed
import sql_feed_manager
import settings
from typing import List

class View():


    def __init__(self, feed_mgr:sql_feed_manager.FeedManager, settings:settings.Settings):
        """
        initialization.
        """
        self.feed_manager : sql_feed_manager.FeedManager
        self.feed_manager = feed_mgr
        self.settings_manager = settings

        self.feeds_cache : List[feed.WebFeed]
        self.articles_cache : List[feed.Article]



    def _std_output_feeds(self) -> None:
        """
        Outputs contents of feeds_cache.
        """
        for feed in self.feeds_cache:
            print ("Feed: ", feed.title)
            print ("Last Updated: ", feed.updated)

    def _std_output_articles(self) -> None:
        """
        Output contents of articles_cache.
        """
        for article in self.articles_cache:
            print ("Article: ", article.title)
 

    def console_ui(self) -> None:
        """
        Starts the UI in console mode.
        """
        while(1):
            self.feeds_cache = self.feed_manager.get_feeds()
            self._std_output_feeds()
            command = input("> ")
            if (command.isdigit()):
                self.articles_cache = self.feed_manager.get_articles(int(command))
                self._std_output_articles()
                input("continue > ")
            elif (command == "refresh"):
                self.feed_manager.refresh_all()
            elif (command == "exit"):
                return
            elif (command == "add"):
                arg = input("add feed > ")
                self.feed_manager.add_feed_from_web(arg)
            elif (command == "delete"):
                arg = input("delete feed > ")
                self.feed_manager.delete_feed(arg)
            else:
                print("Invalid Command.")