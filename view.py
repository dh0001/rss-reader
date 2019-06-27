import feed as feedutility
import feed_manager
import settings
from FeedView import FeedView
from ArticleView import ArticleView

import PySide2.QtWidgets as qtw
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg

from typing import List, Union
import json


class View():
    """
    Handles all interaction with user.
    """

    def __init__(self, mgr: feed_manager.FeedManager, settings: settings.Settings):
        self.main_window : qtw.QMainWindow
        self.article_view : qtw.QTreeView
        self.feed_view : FeedView
        self.content_view : qtw.QTextBrowser
        self.splitter1 : qtw.QSplitter
        self.splitter2 : qtw.QSplitter

        self.feed_manager = mgr
        self.settings_manager = settings


    def cleanup(self) -> None:
        """
        Saves panel states into settings.
        """
        self.settings_manager.settings["geometry"] = bytes(self.main_window.saveGeometry().toHex()).decode("utf-8")
        self.settings_manager.settings["splitter1"] = bytes(self.splitter1.saveState().toHex()).decode("utf-8")
        self.settings_manager.settings["splitter2"] = bytes(self.splitter2.saveState().toHex()).decode("utf-8")
        self.settings_manager.settings["article_view_headers"] = bytes(self.article_view.header().saveState().toHex()).decode("utf-8")
        self.settings_manager.settings["feed_view_headers"] = bytes(self.feed_view.header().saveState().toHex()).decode("utf-8")


    def gui(self) -> None:
        """
        Starts the GUI. Initializes the window, views, and sets up interactions.
        """
        self.app = qtw.QApplication([])

        self.main_window = qtw.QMainWindow()
        self.main_window.setWindowTitle('RSS Reader')
        # self.main_window.resize(800, 600)

        main_widget = qtw.QWidget()   
        self.main_window.setCentralWidget(main_widget)

        self.feed_view = FeedView(self.feed_manager)
        self.article_view = ArticleView(self.feed_manager)

        self.content_view = TBrowser()
        self.content_view.setOpenExternalLinks(True)

        self.splitter1 = qtw.QSplitter(qtc.Qt.Vertical)
        self.splitter1.addWidget(self.article_view)
        self.splitter1.addWidget(self.content_view)
        self.splitter2 = qtw.QSplitter(qtc.Qt.Horizontal)
        self.splitter2.addWidget(self.feed_view)
        self.splitter2.addWidget(self.splitter1)
        # self.splitter1.setSizes([200, 300])
        # self.splitter2.setSizes([200, 500])

        hbox = qtw.QHBoxLayout(main_widget)
        hbox.addWidget(self.splitter2)
        main_widget.setLayout(hbox)

        menu_bar = self.main_window.menuBar().addMenu('Options')
        menu_bar.addAction("Add feed...").triggered.connect(self.feed_view.prompt_add_feed)
        menu_bar.addAction("Add folder...").triggered.connect(self.feed_view.prompt_add_folder)
        menu_bar.addAction("Force Update Feeds").triggered.connect(self.refresh_all)
        menu_bar.addAction("Refresh Caches").triggered.connect(self.reset_screen)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        self.main_window.restoreGeometry(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["geometry"], "utf-8")))
        self.splitter1.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter1"], "utf-8")))
        self.splitter2.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter2"], "utf-8")))
        self.feed_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["feed_view_headers"], "utf-8")))
        self.article_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["article_view_headers"], "utf-8")))

        self.main_window.show()
        self.feed_view.refresh()
        # self.refresh_all()
        
        self.app.exec_()


    
    def article_context_menu(self, position) -> None:
        """
        Outputs the context menu for items in the article view.
        """
        index = self.feed_view.indexAt(position)
        
        if index.isValid():
            menu = qtw.QMenu()
            delete_action = menu.addAction("Mark")
            action = menu.exec_(self.feed_view.viewport().mapToGlobal(position))

            if action == delete_action:
                self.prompt_delete_feed(index)


    def refresh_all(self) -> None:
        """
        Called when the refresh all button is pressed. Tells the feed manager to update all the feeds.
        """
        self.feed_manager.refresh_all()


    def refresh_single(self, feed: feedutility.Feed) -> None:
        """
        Called when a refresh button is pressed. Tells the feed manager to update the feed.
        """
        self.feed_manager.refresh_feed(feed)


    def reset_screen(self) -> None:
        """
        Repopulates the feed view, and cause other views to clear.
        """
        self.output_feeds()
        self.output_articles()
        self.output_content()
        

    def output_content(self) -> None:
        """
        Gets highlighted article in article_display, then outputs the content into content_display.
        """
        index = self.article_view.currentIndex()
        
        if index.isValid():
            row = index.row()
            article_db_id = self.articles_cache[row].db_id
            self.content_view.setHtml(next(x for x in self.articles_cache if x.db_id == article_db_id).content)
            if self.articles_cache[row].unread == True:
                self.mark_article_read(row, article_db_id)
        else:
            self.content_view.setHtml(None)


    def mark_article_read(self, row: int, article_id: int) -> None:
        """
        Tells the feed manager to mark as read in the db.
        Decrements the currently highlighted feed's unread count by 1.
        """
        self.feed_manager.set_article_unread_status(article_id, False)
        self.articles_cache[row].unread = False
        self.article_model.update_row_unread_status(row)
        self.feed_view.currentIndex().internalPointer().unread_count -= 1
        self.feed_model.update_row(self.feed_view.currentIndex())


    def recieve_new_articles(self, articles: List[feedutility.Article], feed_id: int) -> None:
        """
        Recieves new article data from the feed manager and adds them to the views,
        if the currently highlighted feed is the correct feed.
        """
        index = self.feed_view.currentIndex()
        if index.isValid():
            node = index.internalPointer()
            if type(node) == feedutility.Feed and node.db_id == feed_id:
                self.article_model.add_articles(articles)
        self.feed_data_changed()
            

    def recieve_new_feeds(self, feeds: List[feedutility.Feed]) -> None:
        """
        Recieves new feed data from the feed manager and adds them to the views.
        """
        for f in feeds:
            self.feed_model.add_feed(f)


    def feed_data_changed(self) -> None:
        """
        Updates feed information.
        """
        self.feed_view.feed_model.update_data()



    def save_expand_status(self):
        indexes = self.feed_model.match(self.feed_model.index(0, 0), qtc.Qt.DisplayRole, "*", -1, qtc.Qt.MatchWildcard|qtc.Qt.MatchRecursive)
        for index in indexes:
            node = index.internalPointer()
            if node.folder:
                self.feed_view.setExpanded(index, True)




class TBrowser(qtw.QTextBrowser):
    def loadResource(self, type: int, url: str):
        return None