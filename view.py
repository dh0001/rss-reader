import feed
import sql_feed_manager
import settings

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg

from typing import List


class View():

    def __init__(self, feed_mgr:sql_feed_manager.FeedManager, settings:settings.Settings):
        """
        initialization.
        """
        self.feed_manager = feed_mgr
        self.feed_manager.set_article_notify(self.recieve_new_articles)
        self.feed_manager.set_feed_notify(self.recieve_new_feeds)
        self.feed_manager.set_feed_data_changed_notify(self.feed_data_changed)
        self.settings_manager = settings

        self.feeds_cache : List[feed.Feed]
        self.articles_cache : List[feed.Article]

        self.main_window : qtw.QMainWindow
        self.article_view : qtw.QTreeView
        self.feed_view : qtw.QTreeView
        self.content_view : qtw.QTextBrowser

        self.feed_model : FeedModel
        self.article_model : ArticleModel

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

        self.feed_model = FeedModel()
        self.article_model = ArticleModel()

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
        self.article_view.setSortingEnabled(True)
        self.article_view.customContextMenuRequested.connect(self.feed_context_menu)
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
        menu_bar.addAction("Force Update Feeds").triggered.connect(self.button_refresh_all)
        menu_bar.addAction("Refresh Caches").triggered.connect(self.reset_screen)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        self.main_window.restoreGeometry(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["geometry"], "utf-8")))
        self.splitter1.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter1"], "utf-8")))
        self.splitter2.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter2"], "utf-8")))
        self.feed_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["feed_view_headers"], "utf-8")))
        self.article_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["article_view_headers"], "utf-8")))

        self.output_feeds()
        self.button_refresh_all()
        self.main_window.show()
        self.app.exec_()


    def button_refresh_all(self, which=None) -> None:
        """
        Called when the refresh all button is pressed. Tells the feed manager to update all the feeds.
        """
        self.feed_manager.refresh_all()
        self.feed_data_changed()


    def button_refresh(self, which) -> None:
        """
        Called when a refresh button is pressed. Tells the feed manager to update the feed.
        """
        self.feed_manager.refresh_feed(which)
        self.feed_data_changed()


    def button_add_feed(self) -> None:
        """
        Called when the add feed button is pressed. Opens a dialog which allows inputting a new feed.
        """

        dialog = GenericDialog(self.feed_manager.verify_feed_url, "Add Feed:", "Add Feed")
        if (dialog.exec_() == qtw.QDialog.Accepted):
            self.feed_manager.add_feed_from_web(dialog.get_response())
            self.reset_screen()
        # inputDialog = qtw.QInputDialog(None, qtc.Qt.WindowSystemMenuHint | qtc.Qt.WindowTitleHint)
        # inputDialog.setWindowTitle("Add Feed")
        # inputDialog.setLabelText("Feed Url:")
        # inputDialog.show()
        # if (inputDialog.exec_() == qtw.QDialog.Accepted):
        #     self.feed_manager.add_feed_from_web(inputDialog.textValue())
        #     self.reset_screen()


    def button_delete(self, row: int) -> None:
        """
        Called when the delete button is pressed. Deletes the feed from the view then tells the feed manager
        to remove it from the database.
        """
        self.feed_manager.delete_feed(self.feeds_cache[row])
        self.feed_model.remove_feed(row)
        self.reset_screen()


    def reset_screen(self) -> None:
        """
        Repopulates the feed view, and cause other views to clear.
        """
        self.output_feeds()
        self.output_articles()
        self.output_content()


    def output_feeds(self) -> None:
        """
        Repopulates the feed view.
        """
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.feed_model.set_feeds(self.feeds_cache)


    def output_articles(self) -> None:
        """
        Gets highlighted feed in feeds_view, then outputs the articles from those feeds into the articles_view.
        """
        index = self.feed_view.currentIndex()
        if index.isValid():
            db_id = self.feeds_cache[index.row()].db_id
            self.articles_cache = self.feed_manager.get_articles(db_id)
        else:
            self.articles_cache = []

        self.article_view.setSortingEnabled(False)
        self.article_model.set_articles(self.articles_cache)
        #self.article_view.sortByColumn(self.article_view.header().sortIndicatorSection(), self.article_view.header().sortIndicatorOrder())
        self.article_view.setSortingEnabled(True)
        

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
        Tells the feed manager to mark as read in the db and remove BoldRole from the row.
        """
        self.feed_manager.set_article_unread_status(article_id, False)
        self.articles_cache[row].unread = False
        self.article_model.update_row_unread_status(row)
        self.feeds_cache[self.feed_view.currentIndex().row()].unread_count -= 1
        self.feed_model.update_row(self.feed_view.currentIndex().row())


    def feed_context_menu(self, position) -> None:
        """
        Outputs the context menu for items in the feed view.
        """
        index = self.feed_view.indexAt(position)
        
        if index.isValid():
            menu = qtw.QMenu()
            refresh = menu.addAction("Refresh Feed")
            delete = menu.addAction("Delete Feed")
            set_refresh_rate = menu.addAction("Set Refresh Rate")
            action = menu.exec_(self.feed_view.viewport().mapToGlobal(position))

            if action == delete:
                self.button_delete(index.row())
            elif action == refresh:
                self.button_refresh(self.feeds_cache[index.row()])
            elif action == set_refresh_rate:
                dialog = GenericDialog(lambda x: x.isdigit(), "Refresh Rate (minutes):", "Set Refresh Rate")
                if (dialog.exec_() == qtw.QDialog.Accepted):
                    self.feed_manager.set_refresh_rate(self.feeds_cache[index.row()], int(dialog.get_response()))
                    self.feed_model.update_row(index.row())

    
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
                self.button_delete(index.row())


    def recieve_new_articles(self, articles: List[feed.Article], feed_id: int) -> None:
        """
        Recieves new article data from the feed manager and adds them to the views.
        """
        current_index = self.feed_view.currentIndex()
        if current_index.isValid() and self.feeds_cache[current_index.row()].db_id == feed_id:
            self.article_view.setSortingEnabled(False)
            self.article_model.add_articles(articles)
            self.article_view.setSortingEnabled(True)
            

    def recieve_new_feeds(self, feeds: List[feed.Feed]) -> None:
        """
        Recieves new feed data from the feed manager and adds them to the views.
        """
        for f in feeds:
            self.feed_model.add_feed(f)


    def feed_data_changed(self) -> None:
        """
        Updates feed information.
        """
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.feed_model.update_data(self.feeds_cache)



class ArticleModel(qtc.QAbstractItemModel):
    def __init__(self):
        """
        initialization.
        """
        qtc.QAbstractItemModel.__init__(self)
        self.ar : List[feed.Article] = []

    def rowCount(self, index: qtc.QModelIndex):
        """
        Returns the number of rows. When index is a valid row in the model, returns 0.
        """
        if index.isValid():
            return 0
        return len(self.ar)

    def add_articles(self, articles: List[feed.Article]):
        """
        Adds appends an article to the cache, while refreshing the view.
        """
        self.beginInsertRows(qtc.QModelIndex(), len(self.ar), len(articles))
        self.ar += articles
        self.endInsertRows()

    def index(self, in_row, in_column, in_parent=None):
        """
        Returns QModelIndex for given row/column.
        """
        if not qtc.QAbstractItemModel.hasIndex(self, in_row, in_column):
            return qtc.QModelIndex()
        return qtc.QAbstractItemModel.createIndex(self, in_row, in_column, 1)

    def parent(self, in_index):
        """
        Returns an invalid index, model does not have subtrees.
        """
        return qtc.QModelIndex()

    def columnCount(self, in_index):
        """
        Returns the number of columns.
        """
        return 3

    def data(self, in_index, role):
        if not in_index.isValid():
            return None
        if role == qtc.Qt.DisplayRole:
            if in_index.column() == 0:
                return self.ar[in_index.row()].title
            if in_index.column() == 1:
                return self.ar[in_index.row()].author
            if in_index.column() == 2:
                return self.ar[in_index.row()].updated
        if role == qtc.Qt.FontRole and self.ar[in_index.row()].unread == True:
            f = qtg.QFont()
            f.setBold(True)
            return f
        return None

    def set_articles(self, articles) -> None:
        self.beginResetModel()
        self.ar = articles
        self.endResetModel()

    def headerData(self, section, orientation, role=qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal: # Horizontal
                return {
                    0: "Name",
                    1: "Author",
                    2: "Updated"
                }.get(section, None)

    def sort(self, column, order=qtc.Qt.AscendingOrder):
        self.beginResetModel()
        order = True if order == qtc.Qt.AscendingOrder else False
        if column == 0:
            self.ar.sort(key=lambda e: e.title, reverse=order)
        if column == 1:
            self.ar.sort(key=lambda e: e.author, reverse=order)
        if column == 2:
            self.ar.sort(key=lambda e: e.updated, reverse=order)
        self.endResetModel()

    def update_row_unread_status(self, row):
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.FontRole])



class FeedModel(qtc.QAbstractItemModel):
    def __init__(self):
        qtc.QAbstractItemModel.__init__(self)
        self.ar : List[feed.Feed] = []

    def rowCount(self, in_index):
        if in_index.isValid():
            return 0
        return len(self.ar)

    def add_feed(self, feed):
        self.beginInsertRows(qtc.QModelIndex(), len(self.ar), 1)
        self.ar.append(feed)
        self.endInsertRows()

    def remove_feed(self, row):
        """
        Removes the feed in the view, and in the cache.
        """
        self.beginRemoveRows(qtc.QModelIndex(), row, row)
        del self.ar[row]
        self.endRemoveRows()


    def index(self, in_row, in_column, in_parent=None):
        if not qtc.QAbstractItemModel.hasIndex(self, in_row, in_column):
            return qtc.QModelIndex()
        return qtc.QAbstractItemModel.createIndex(self, in_row, in_column, 1)

    def parent(self, in_index):
        return qtc.QModelIndex()

    def columnCount(self, in_index):
        return 2

    def data(self, in_index, role):
        if not in_index.isValid():
            return None
        if role == qtc.Qt.DisplayRole:
            if in_index.column() == 0:
                return self.ar[in_index.row()].title
            if in_index.column() == 1:
                return self.ar[in_index.row()].refresh_rate
        elif role == qtc.Qt.FontRole:
            if self.ar[in_index.row()].unread_count > 0:
                f = qtg.QFont()
                f.setBold(True)
                return f
        return None

    def set_feeds(self, feeds: List[feed.Feed]) -> None:
        self.beginResetModel()
        self.ar = feeds
        self.endResetModel()

    def headerData(self, section, orientation, role=qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal: # Horizontal
                return {
                    0: "Feed Name",
                    1: "Unread"
                }.get(section, None)

    def sort(self, column, order=qtc.Qt.AscendingOrder):
        order = True if order == qtc.Qt.AscendingOrder else False
        if column == 0:
            self.ar.sort(key=lambda e: e.title, reverse=order)
        if column == 1:
            self.ar.sort(key=lambda e: e.author, reverse=order)
        self.dataChanged.emit(qtc.QModelIndex(), qtc.QModelIndex())

    def update_row(self, row: int):
        self.dataChanged.emit(self.index(row, 0), self.index(row, 1), [qtc.Qt.DisplayRole, qtc.Qt.FontRole])

    def update_data(self, feeds: List[feed.Feed]):
        self.ar = feeds
        self.dataChanged.emit(qtc.QModelIndex(), qtc.QModelIndex())


class GenericDialog(qtw.QDialog):

    def __init__(self, verify, prompt, window_title):
        qtw.QDialog.__init__(self, None, qtc.Qt.WindowCloseButtonHint | qtc.Qt.WindowTitleHint)

        self.setObjectName(window_title)

        self.verify_function = verify
        
        vbox = qtw.QGridLayout()
        vbox.addWidget(qtw.QLabel(prompt), 0, 0, 1, 2)

        self.le = qtw.QLineEdit()
        vbox.addWidget(self.le, 1, 0, 1, 2)

        buttonBox = qtw.QDialogButtonBox(qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.verify_response)
        buttonBox.rejected.connect(self.reject)
        vbox.addWidget(buttonBox, 2, 1, 1, 1)

        self.error_label = qtw.QLabel("")
        self.error_label.setMinimumWidth(qtg.QFontMetrics(qtg.QFont()).width("Verify Failed"))
        vbox.addWidget(self.error_label, 2, 0, 1, 1)

        vbox.setSizeConstraint(qtw.QLayout.SetFixedSize)

        self.setLayout(vbox)

        self.show()

    def verify_response(self):
        
        self.error_label.setText("Verifying...")
        if self.verify_function(self.le.text()):
            self.accept()
        else:
            self.error_label.setText("Verify Failed")


    def get_response(self):
        return self.le.text()