import feed
import sql_feed_manager
import settings

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg

from typing import List

def UNREAD_ROW_NUMBER(): return 1
UnreadRole = qtc.Qt.UserRole + 1
DbRole = qtc.Qt.UserRole + 2

class View():

    def __init__(self, feed_mgr:sql_feed_manager.FeedManager, settings:settings.Settings):
        """
        initialization.
        """
        self.feed_manager = feed_mgr
        self.settings_manager = settings

        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.articles_cache : List[feed.Article]

        self.main_window : qtw.QMainWindow
        self.article_view : qtw.QTreeView
        self.feed_view : qtw.QTreeView
        self.content_view : qtw.QTextBrowser

        self.feed_model : qtg.QStandardItemModel
        self.article_model : qtg.QStandardItemModel

        self.splitter1 : qtw.QSplitter
        self.splitter2 : qtw.QSplitter

        self.app : qtw.QApplication


    def cleanup(self) -> None:
        """
        Should be called on program close. Saves panel states into settings.
        """
        self.settings_manager.settings["geometry"] = bytes(self.main_window.saveGeometry().toHex()).decode("utf-8")
        self.settings_manager.settings["splitter1"] = bytes(self.splitter1.saveState().toHex()).decode("utf-8")
        self.settings_manager.settings["splitter2"] = bytes(self.splitter2.saveState().toHex()).decode("utf-8")
        self.settings_manager.settings["article_view_headers"] = bytes(self.article_view.header().saveState().toHex()).decode("utf-8")
        self.settings_manager.settings["feed_view_headers"] = bytes(self.feed_view.header().saveState().toHex()).decode("utf-8")


    def gui(self) -> None:
        """
        Starts the UI in graphical mode using qt. Initializes the window, views, and models.
        """
        self.app = qtw.QApplication([])

        self.main_window = qtw.QMainWindow()
        self.main_window.setWindowTitle('RSS Reader')
        # self.main_window.resize(800, 600)

        main_widget = qtw.QWidget()   
        self.main_window.setCentralWidget(main_widget)

        self.feed_model = qtg.QStandardItemModel()
        self.feed_model.setHorizontalHeaderLabels(['Feed Name', 'Unread'])
        self.article_model = qtg.QStandardItemModel()
        self.article_model.setHorizontalHeaderLabels(['Article', 'Author', 'Updated'])

        self.feed_view = qtw.QTreeView()
        self.feed_view.setModel(self.feed_model)
        self.feed_view.setRootIsDecorated(False)
        self.feed_view.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.feed_view.customContextMenuRequested.connect(self.feed_context_menu)
        self.feed_view.setSortingEnabled(True)
        self.feed_view.header().setStretchLastSection(False)
        
        self.article_view = qtw.QTreeView()
        self.article_view.setModel(self.article_model)
        self.article_view.setRootIsDecorated(False)
        self.article_view.setItemDelegate(BoldDelegate())
        self.article_view.sortByColumn(2, qtc.Qt.AscendingOrder)
        self.article_view.setSortingEnabled(True)
        self.article_view.header().setStretchLastSection(False)
        
        self.content_view = qtw.QTextBrowser()
        self.content_view.setOpenExternalLinks(True)

        self.feed_view.selectionModel().selectionChanged.connect(self.output_articles)
        self.article_view.selectionModel().selectionChanged.connect(self.output_content)

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
        menu_bar.addAction("Add Feed...").triggered.connect(self.button_add_feed)
        menu_bar.addAction("Download Feeds").triggered.connect(self.button_refresh)
        menu_bar.addAction("Reload Screen").triggered.connect(self.reset_screen)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        self.main_window.restoreGeometry(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["geometry"], "utf-8")))
        self.splitter1.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter1"], "utf-8")))
        self.splitter2.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter2"], "utf-8")))
        self.feed_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["feed_view_headers"], "utf-8")))
        self.article_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["article_view_headers"], "utf-8")))

        self.output_feeds()
        self.main_window.show()
        self.app.exec_()


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
        self.article_model.removeRows(0, self.article_model.rowCount())
        self.content_view.setHtml("")
        self.output_feeds()


    def output_feeds(self) -> None:
        """
        Repopulates the feed view.
        """
        self.feed_model.removeRows(0, self.feed_model.rowCount())
        self.feeds_cache = self.feed_manager.get_all_feeds()

        for feed in self.feeds_cache:
            title = qtg.QStandardItem(feed.title)
            title.setData(feed.db_id, DbRole)
            title.setEditable(False)
            unread_count = qtg.QStandardItem(str(self.feed_manager.get_unread_articles_count(feed.db_id)))
            unread_count.setData(feed.db_id, DbRole)
            unread_count.setEditable(False)
            self.feed_model.appendRow([title, unread_count])


    def output_articles(self) -> None:
        """
        Gets highlighted feed in feeds_view, then outputs the articles from those feeds into the articles_view.
        """
        self.article_model.removeRows(0, self.article_model.rowCount())
        db_id = self.feed_view.currentIndex().data(DbRole)
        self.articles_cache = self.feed_manager.get_articles(db_id)
        self.article_view.setSortingEnabled(False)

        for article in self.articles_cache:
            title = qtg.QStandardItem(article.title)
            title.setData(article.db_id, DbRole)
            title.setData(article.unread, UnreadRole)
            title.setEditable(False)
            author = qtg.QStandardItem(article.author)
            author.setData(article.unread, UnreadRole)
            author.setEditable(False)
            updated = qtg.QStandardItem(article.updated)
            updated.setData(article.unread, UnreadRole)
            updated.setEditable(False)
            self.article_model.appendRow([title, author, updated])

        self.article_view.sortByColumn(self.article_view.header().sortIndicatorSection(), self.article_view.header().sortIndicatorOrder())
        self.article_view.setSortingEnabled(True)
        


    def output_content(self) -> None:
        """
        Gets highlighted article in article_display, then outputs the content into content_display.
        """
        index = self.article_view.currentIndex()
        
        if index.isValid():
            row = index.row()
            article_db_id = self.article_model.item(row, 0).data(DbRole)
            self.content_view.setHtml(next(x for x in self.articles_cache if x.db_id == article_db_id).content)
            if self.article_view.currentIndex().data(UnreadRole):
                self.mark_article_read(row, article_db_id)


    def mark_article_read(self, row: int, article_id: int) -> None:
        """
        Tells the feed manager to mark as read in the db and remove BoldRole from the row.
        """
        self.feed_manager.set_article_unread_status(article_id, False)
        self.article_model.item(row, 0).setData(False, UnreadRole)
        self.article_model.item(row, 1).setData(False, UnreadRole)
        self.article_model.item(row, 2).setData(False, UnreadRole)
        feed_unread_item = self.feed_model.item(self.feed_view.currentIndex().row(), UNREAD_ROW_NUMBER())
        feed_unread_item.setText(str(int(feed_unread_item.text()) - 1))



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


    def add_new_data(self) -> None:
        """
        Recieves new feed data from the feed manager and adds them to the views.
        """


# class ArticleModel(qtc.QAbstractItemModel):
#     def __init__(self, in_nodes):
#         qtc.QAbstractItemModel.__init__(self)
#         self._root = DbItem(None, 0)


# class DbItem(qtg.QStandardItem):
#     def __init__(self, text: str, db_id: int):
#         qtg.QStandardItem.__init__(self, text)
#         self.db_id : int = db_id
#         self.unread : bool = True

#     def data(self, role):
#         if role == UnreadRole:
#             return self.unread
#         return qtg.QStandardItem.data(self, role)


class BoldDelegate(qtw.QStyledItemDelegate):
    def paint(self, painter, option, index):
        # decide here if item should be bold and set font weight to bold if needed
        option.font.setBold(index.data(UnreadRole))
        qtw.QStyledItemDelegate.paint(self, painter, option, index)