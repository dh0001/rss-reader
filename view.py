import feed
import sql_feed_manager
import settings

from tkinter import *
from tkinter import ttk

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
        self.window : Tk
        self.article_view : ttk.Treeview
        self.feed_view : ttk.Treeview
        self.content_view : Text



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


    def gui(self) -> None:
        """
        Starts the UI in graphical mode using Tk.
        """
        root = Tk()
        root.title("RSS Reader")

        mainframe = ttk.Frame(root, padding="0 0 0 0")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)

        buttons_frame = ttk.Frame(mainframe)
        buttons_frame.grid(column=0, row=0, columnspan=2, sticky=(N, S, E, W))
        ttk.Button(buttons_frame, text="Refresh", command=self.button_refresh).grid(column=0, row=0)
        ttk.Button(buttons_frame, text="Add", command=self.button_add).grid(column=1, row=0)
        ttk.Button(buttons_frame, text="Delete", command=self.button_delete).grid(column=2, row=0)
        ttk.Button(buttons_frame, text="Reload", command=self.button_reload).grid(column=3, row=0)

        self.feed_view = ttk.Treeview(mainframe)
        self.feed_view.grid(column=0, row=1, rowspan=2, sticky=(N, S, E, W))

        self.content_view = Text(mainframe)
        self.content_view.grid(column=1, row=2, sticky=(N, S, E, W))

        self.article_view = ttk.Treeview(mainframe, columns=('author', 'updated'))
        self.article_view.grid(column=1, row=1, sticky=(N, S, E, W))
        self.article_view.heading('#0', text='Article')
        self.article_view.column('#0', minwidth=30)
        self.article_view.heading('author', text='Author')
        self.article_view.column('author', minwidth=30)
        self.article_view.heading('updated', text='Updated')
        self.article_view.column('updated', minwidth=30)

        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)
        buttons_frame.columnconfigure(3, weight=1)
        mainframe.columnconfigure(0, weight=1)
        mainframe.columnconfigure(1, weight=1)
        mainframe.rowconfigure(0, weight=0)
        mainframe.rowconfigure(1, weight=1)
        mainframe.rowconfigure(2, weight=1)

        self.button_refresh()
        self.button_reload()

        root.mainloop()
    
    def button_refresh(self) -> None:
        """
        Called when the refresh button is pressed.
        """
        self.feed_manager.refresh_all()
        self.feeds_cache = self.feed_manager.get_feeds()
        return

    def button_add(self) -> None:
        """
        Called when the refresh button is pressed.
        """
        return

    def button_delete(self) -> None:
        """
        Called when the refresh button is pressed.
        """
        return

    def button_reload(self) -> None:
        """
        Called when the refresh button is pressed.
        """
        self.feed_view.delete(*self.feed_view.get_children())

        for feed in self.feeds_cache:
            self.feed_view.insert('', 'end', text=feed.title)
        return

    def _tk_tree_output_feeds(self) -> None:
        """
        Outputs contents of feeds_cache.
        """
        for feed in self.feeds_cache:
            print ("Feed: ", feed.title)
            print ("Last Updated: ", feed.updated)

    def _tk_tree_output_articles(self) -> None:
        """
        Output contents of articles_cache.
        """
        for article in self.articles_cache:
            print ("Article: ", article.title)