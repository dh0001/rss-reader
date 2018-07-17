import feed
import sql_feed_manager
import settings
import struct

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg



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
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.articles_cache : List[feed.Article]

        self.main_widget : qtw.QWidget
        self.article_view : qtw.QTreeView
        self.feed_view : qtw.QTreeView
        self.content_view : qtw.QTextBrowser

        self.feed_model : qtg.QStandardItemModel
        self.article_model : qtg.QStandardItemModel


    def gui(self) -> None:
        """
        Starts the UI in graphical mode using qt. Initializes the window, views, and models.
        """
        app = qtw.QApplication([])

        main_window = qtw.QMainWindow()
        main_window.setWindowTitle('RSS Reader')
        main_window.resize(700, 500)

        self.main_widget = qtw.QWidget()   
        main_window.setCentralWidget(self.main_widget)

        self.feed_model = qtg.QStandardItemModel()
        self.article_model = qtg.QStandardItemModel()

        self.feed_view = qtw.QTreeView()
        self.feed_view.setModel(self.feed_model)
        self.feed_view.setRootIsDecorated(False)
        self.feed_view.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.feed_view.customContextMenuRequested.connect(self.feed_context_menu)
        self.article_view = qtw.QTreeView()
        self.article_view.setModel(self.article_model)
        self.article_view.setRootIsDecorated(False)
        self.content_view = qtw.QTextBrowser()
        self.content_view.setOpenExternalLinks(True)

        self.button_reload()

        self.feed_view.selectionModel().selectionChanged.connect(self.output_articles)
        self.article_view.selectionModel().selectionChanged.connect(self.output_content)

        splitter1 = qtw.QSplitter(qtc.Qt.Vertical)
        splitter1.addWidget(self.article_view)
        splitter1.addWidget(self.content_view)
        splitter2 = qtw.QSplitter(qtc.Qt.Horizontal)
        splitter2.addWidget(self.feed_view)
        splitter2.addWidget(splitter1)
        splitter2.setSizes([200, 400])

        hbox = qtw.QHBoxLayout(self.main_widget)
        hbox.addWidget(splitter2)
        self.main_widget.setLayout(hbox)        

        menu_bar = main_window.menuBar().addMenu('Options')
        menu_bar.addAction("Add Feed...").triggered.connect(self.button_add)
        menu_bar.addAction("Download Feeds").triggered.connect(self.button_refresh)
        menu_bar.addAction("Reload Screen").triggered.connect(self.button_reload)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        main_window.show()
        app.exec_()


    def button_refresh(self) -> None:
        """
        Called when the refresh button is pressed.
        """
        self.feed_manager.refresh_all()
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.button_reload()


    def button_add(self) -> None:
        """
        Called when the add button is pressed.
        """
        inputDialog = qtw.QInputDialog(None, qtc.Qt.WindowSystemMenuHint | qtc.Qt.WindowTitleHint)
        inputDialog.setWindowTitle("Add Feed")
        inputDialog.setLabelText("Feed Url:")
        inputDialog.show()
        if (inputDialog.exec_() == qtw.QDialog.Accepted):
            self.feed_manager.add_feed_from_web(inputDialog.textValue())
            self.button_reload()


    def button_delete(self, db_id: int) -> None:
        """
        Called when the delete button is pressed.
        """
        self.feed_manager.delete_feed(db_id)
        self.button_reload()


    def button_reload(self) -> None:
        """
        Called when the reload button is pressed. Deletes everything in the article, feed, and content view,
        then repopulates the feed view.
        """
        self.feed_model.clear()
        self.feed_model.setColumnCount(1)
        self.feed_model.setHorizontalHeaderLabels(['Feed Name'])
        self.article_model.clear()
        self.article_model.setColumnCount(3)
        self.article_model.setHorizontalHeaderLabels(['Article', 'Author', 'Updated'])
        self.content_view.setHtml("")
        self.feeds_cache = self.feed_manager.get_all_feeds()

        for feed in self.feeds_cache:
            title = DbItem(feed.title, feed.db_id)
            title.setEditable(False)
            self.feed_model.appendRow([title])


    def output_articles(self) -> None:
        """
        Gets highlighted feed in feeds_display, then outputs the articles from those feeds into the articles_display.
        """
        self.article_model.clear()
        self.article_model.setColumnCount(3)
        self.article_model.setHorizontalHeaderLabels(['Article', 'Author', 'Updated'])    
        db_id = self.feed_model.itemFromIndex(self.feed_view.currentIndex()).feed_id
        self.articles_cache = self.feed_manager.get_articles(db_id)

        for article in self.articles_cache:
            title = qtg.QStandardItem(article.title)
            title.setEditable(False)
            author = qtg.QStandardItem(article.author)
            author.setEditable(False)
            updated = qtg.QStandardItem(article.updated)
            updated.setEditable(False)
            self.article_model.appendRow([title, author, updated])


    def output_content(self) -> None:
        """
        Gets highlighted article in article_display, then outputs the content into content_display.
        """
        article = self.article_model.item(self.article_view.currentIndex().row(), 0).text()
        self.content_view.setHtml(next(x for x in self.articles_cache if x.title == article).content)

    def feed_context_menu(self, position) -> None:
        """
        Outputs the context menu for items in the feed view.
        """
        index = self.feed_view.indexAt(position)
        
        if index.isValid():
            menu = qtw.QMenu()
            delete_action = menu.addAction("Delete Feed")
            action = menu.exec_(self.feed_view.viewport().mapToGlobal(position))

            if action == delete_action:
                self.button_delete(self.feed_model.itemFromIndex(index).feed_id)


class DbItem(qtg.QStandardItem):
    def __init__(self, text: str, feed_id: int):
        qtg.QStandardItem.__init__(self, text)
        self.feed_id = feed_id
