import feed
import sql_feed_manager
import settings
import struct

from tkinter import *  # pylint: disable=unused-import
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
        
        # Root
        root = Tk()
        root.title("RSS Reader")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Root's Frame
        main_frame = ttk.Frame(root, padding="0 0 0 0")
        main_frame.grid(column=0, row=0, sticky=(N, W, E, S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(column=0, row=0, columnspan=2, sticky=(N, S, E, W))
        ttk.Button(buttons_frame, text="Refresh", command=self.button_refresh).grid(column=0, row=0)
        ttk.Button(buttons_frame, text="Add", command=self.button_add).grid(column=1, row=0)
        ttk.Button(buttons_frame, text="Delete", command=self.button_delete).grid(column=2, row=0)
        ttk.Button(buttons_frame, text="Reload", command=self.button_reload).grid(column=3, row=0)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)
        buttons_frame.columnconfigure(3, weight=1)

        # Feed View
        self.feed_view = ttk.Treeview(main_frame, columns=('id'))
        self.feed_view.grid(column=0, row=1, rowspan=2, sticky=(N, S, E, W))
        self.feed_view.bind("<<TreeviewSelect>>", lambda e: self.tk_output_articles())
        self.feed_view.heading('#0', text="Feed")
        self.feed_view["displaycolumns"]=[]

        # Article View
        self.article_view = ttk.Treeview(main_frame, columns=('author', 'updated'))
        self.article_view.grid(column=1, row=1, sticky=(N, S, E, W))
        self.article_view.heading('#0', text='Article')
        self.article_view.column('#0', minwidth=30)
        self.article_view.heading('author', text='Author')
        self.article_view.column('author', minwidth=30)
        self.article_view.heading('updated', text='Updated')
        self.article_view.column('updated', minwidth=30)
        self.article_view.bind("<<TreeviewSelect>>", lambda e: self.tk_output_content())

        # Content View
        self.content_view = Text(main_frame)
        self.content_view.grid(column=1, row=2, sticky=(N, S, E, W))

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
        Called when the add button is pressed.
        """
        def submit() -> None:
            self.feed_manager.add_feed_from_web(add_entry.get())
            t.destroy()
        t = Toplevel()
        t.title("Add Feed")
        add_entry = ttk.Entry(t)
        add_entry.grid(column=0, row=0, sticky=(E, W))
        ttk.Button(t, text="Add Feed", command=submit).grid(column=0, row=1, sticky=(E, W))


    def button_delete(self) -> None:
        """
        Called when the refresh button is pressed.
        """
        def submit() -> None:
            self.feed_manager.delete_feed(add_entry.get())
            t.destroy()
        t = Toplevel()
        t.title("Delete Feed")
        add_entry = ttk.Entry(t)
        add_entry.grid(column=0, row=0, sticky=(E, W))
        ttk.Button(t, text="Delete Feed", command=submit).grid(column=0, row=1, sticky=(E, W))
        return

    def button_reload(self) -> None:
        """
        Called when the reload button is pressed.
        """
        self.feed_view.delete(*self.feed_view.get_children())
        self.article_view.delete(*self.article_view.get_children())
        self.content_view.delete('1.0', 'end')

        for feed in self.feeds_cache:
            self.feed_view.insert('', 'end', text=feed.title, values=[feed.db_id])

    def tk_output_articles(self) -> None:
        """
        Gets highlighted feed in feeds_display, then outputs the articles from those feeds into the articles_display.
        """
        self.article_view.delete(*self.article_view.get_children())
        self.articles_cache = self.feed_manager.get_articles(self.feed_view.item(self.feed_view.focus())['values'][0])

        for article in self.articles_cache:
            self.article_view.insert('', 'end', text=article.title, values=[article.author, article.updated])


    def tk_output_content(self) -> None:
        """
        Gets highlighted article in article_display, then outputs the content into content_display.
        """
        article = self.article_view.item(self.article_view.focus())['text']
        self.content_view.replace('1.0', 'end', next(x for x in self.articles_cache if x.title == article).content)