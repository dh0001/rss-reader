import feed
import sql_feed_manager
import settings
import struct

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg



from typing import List

BoldRole = qtc.Qt.UserRole + 1
DbRole = qtc.Qt.UserRole + 2

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
        self.article_view.setItemDelegate(BoldDelegate())
        self.content_view = qtw.QTextBrowser()
        self.content_view.setOpenExternalLinks(True)

        self.reset_screen()

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
        menu_bar.addAction("Add Feed...").triggered.connect(self.button_add_feed)
        menu_bar.addAction("Download Feeds").triggered.connect(self.button_refresh)
        menu_bar.addAction("Reload Screen").triggered.connect(self.reset_screen)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        main_window.show()
        app.exec_()


    def button_refresh(self) -> None:
        """
        Called when a refresh button is pressed. Tells the feed manager to update the feeds.
        """
        self.feed_manager.refresh_all()
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.reset_screen()


    def button_add_feed(self) -> None:
        """
        Called when the add feed button is pressed.
        """
        inputDialog = qtw.QInputDialog(None, qtc.Qt.WindowSystemMenuHint | qtc.Qt.WindowTitleHint)
        inputDialog.setWindowTitle("Add Feed")
        inputDialog.setLabelText("Feed Url:")
        inputDialog.show()
        if (inputDialog.exec_() == qtw.QDialog.Accepted):
            self.feed_manager.add_feed_from_web(inputDialog.textValue())
            self.reset_screen()


    def button_delete(self, db_id: int) -> None:
        """
        Called when the delete button is pressed.
        """
        self.feed_manager.delete_feed(db_id)
        self.reset_screen()


    def reset_screen(self) -> None:
        """
        Deletes everything in the article, feed, and content view, then repopulates the feed view.
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
            title = qtg.QStandardItem(feed.title)
            title.setData(feed.db_id, DbRole)
            title.setEditable(False)
            self.feed_model.appendRow([title])


    def output_articles(self) -> None:
        """
        Gets highlighted feed in feeds_display, then outputs the articles from those feeds into the articles_display.
        """
        self.article_model.clear()
        self.article_model.setColumnCount(3)
        self.article_model.setHorizontalHeaderLabels(['Article', 'Author', 'Updated'])

        db_id = self.feed_view.currentIndex().data(DbRole)
        self.articles_cache = self.feed_manager.get_articles(db_id)

        for article in self.articles_cache:
            title = qtg.QStandardItem(article.title)
            title.setData(article.db_id, DbRole)
            title.setData(article.unread, BoldRole)
            title.setEditable(False)
            author = qtg.QStandardItem(article.author)
            author.setData(article.unread, BoldRole)
            author.setEditable(False)
            updated = qtg.QStandardItem(article.updated)
            updated.setData(article.unread, BoldRole)
            updated.setEditable(False)
            self.article_model.appendRow([title, author, updated])


    def mark_article_read(self, row: int, article_id: int) -> None:
        """
        Tells the feed manager to mark as read in the db and remove BoldRole from the row.
        """
        self.feed_manager.mark_article_read(article_id)
        self.article_model.item(row, 0).setData(False, BoldRole)
        self.article_model.item(row, 1).setData(False, BoldRole)
        self.article_model.item(row, 2).setData(False, BoldRole)


    def output_content(self) -> None:
        """
        Gets highlighted article in article_display, then outputs the content into content_display.
        """
        row = self.article_view.currentIndex().row()
        article_db_id = self.article_model.item(row, 0).data(DbRole)
        self.content_view.setHtml(next(x for x in self.articles_cache if x.db_id == article_db_id).content)
        self.mark_article_read(row, article_db_id)


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
                self.button_delete(self.feed_model.itemFromIndex(index).data(DbRole))


class ArticleModel(qtc.QAbstractItemModel):
    def __init__(self, in_nodes):
        qtc.QAbstractItemModel.__init__(self)
        self._root = DbItem(None, 0)


class DbItem(qtg.QStandardItem):
    def __init__(self, text: str, db_id: int):
        qtg.QStandardItem.__init__(self, text)
        self.db_id : int = db_id
        self.unread : bool = True

    def data(self, role):
        if role == BoldRole:
            return self.unread
        return qtg.QStandardItem.data(self, role)


class BoldDelegate(qtw.QStyledItemDelegate):
    def paint(self, painter, option, index):
        # decide here if item should be bold and set font weight to bold if needed
        option.font.setBold(index.data(BoldRole))
        qtw.QStyledItemDelegate.paint(self, painter, option, index)