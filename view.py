import feed as feedutility
import sql_feed_manager
import settings

import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg

from typing import List, Union


class View():

    def __init__(self, feed_mgr: sql_feed_manager.FeedManager, settings: settings.Settings):
        """
        initialization.
        """
        self.main_window : qtw.QMainWindow
        self.article_view : qtw.QTreeView
        self.feed_view : qtw.QTreeView
        self.content_view : qtw.QTextBrowser
        self.feed_model : FeedModel
        self.article_model : ArticleModel
        self.splitter1 : qtw.QSplitter
        self.splitter2 : qtw.QSplitter

        self.feeds_cache : List[feedutility.Feed]
        self.articles_cache : List[feedutility.Article]
        self.feed_manager = feed_mgr
        self.feed_manager.set_article_notify(self.recieve_new_articles)
        self.feed_manager.set_feed_notify(self.recieve_new_feeds)
        self.feed_manager.set_feed_data_changed_notify(self.feed_data_changed)
        self.settings_manager = settings


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
        #self.feed_view.setRootIsDecorated(False)
        self.feed_view.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.feed_view.customContextMenuRequested.connect(self.feed_context_menu)
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
        menu_bar.addAction("Add feed...").triggered.connect(self.prompt_add_feed)
        menu_bar.addAction("Add folder...").triggered.connect(self.prompt_add_folder)
        menu_bar.addAction("Force Update Feeds").triggered.connect(self.refresh_all)
        menu_bar.addAction("Refresh Caches").triggered.connect(self.reset_screen)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        self.main_window.restoreGeometry(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["geometry"], "utf-8")))
        self.splitter1.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter1"], "utf-8")))
        self.splitter2.restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["splitter2"], "utf-8")))
        self.feed_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["feed_view_headers"], "utf-8")))
        self.article_view.header().restoreState(qtc.QByteArray.fromHex(bytes(self.settings_manager.settings["article_view_headers"], "utf-8")))

        self.output_feeds()
        #self.button_refresh_all()
        self.main_window.show()
        self.app.exec_()


    def prompt_add_feed(self, index: qtc.QModelIndex=None) -> None:
        """
        Opens a dialog allowing a user to enter a url for a new feed.
        Called when the add feed button is pressed. Opens a dialog which allows inputting a new feed.
        Resets the screen.
        """
        dialog = GenericDialog(self.feed_manager.verify_feed_url, "Add Feed:", "Add Feed", "")
        if (dialog.exec_() == qtw.QDialog.Accepted):
            if index:
                folder = index.internalPointer().folder.db_id
            else:
                folder = 0
            self.feed_manager.add_feed_from_web(dialog.get_response(), folder)
            self.reset_screen()


    def prompt_delete_feed(self, index: qtc.QModelIndex) -> None:
        """
        Opens a message box prompt which confirms if the user wants to delete a feed.
        Deletes a feed from the view, then tells the feed manager to remove it from the database.
        Resets the screen.
        """
        feed = index.internalPointer().data
        response = qtw.QMessageBox.question(None, "Prompt", "Are you sure you want to delete '" + feed.user_title if feed.user_title != None else feed.title + "'?", qtw.QMessageBox.Yes | qtw.QMessageBox.No)
        if response == qtw.QMessageBox.Yes:
            self.feed_model.remove_feed(index)
            self.feed_manager.delete_feed(feed)
            self.reset_screen()


    def prompt_add_folder(self, index: qtc.QModelIndex=None) -> None:
        """
        Opens a dialog allowing a user to enter a name for a new folder.
        Adds a folder to the feed database, with the passed index as a parent.
        Resets the screen.
        """
        dialog = GenericDialog(lambda x: True, "Add Folder:", "Add Folder", "")
        if (dialog.exec_() == qtw.QDialog.Accepted):
            if index:
                folder = index.internalPointer().folder.db_id
            else:
                folder = 0
            self.feed_manager.add_folder(dialog.get_response(), folder)
            self.reset_screen()


    def prompt_delete_folder(self, index: qtc.QModelIndex) -> None:
        """
        Opens a message box prompt which confirms if the user wants to delete a folder.
        Deletes the folder from the view then tells the feed manager to remove it from the database.
        Resets the screen.
        """
        folder = index.internalPointer().folder
        response = qtw.QMessageBox.question(None, "Prompt", "Are you sure you want to delete '"+ folder.title + "'?", qtw.QMessageBox.Yes | qtw.QMessageBox.No)
        if response == qtw.QMessageBox.Yes:
            self.feed_manager.delete_folder(folder)
            self.reset_screen()


    def prompt_set_user_custom_title(self, index: qtc.QModelIndex) -> None:
        """
        Opens a dialog which allows the user to enter a custom title for a feed.
        Tells the feed manager to set the custom name of the feed in the database.
        Tells the view to update the row of the passed index.
        """
        feed = index.internalPointer().data
        dialog = GenericDialog(lambda x: True, "Title:", "Set Title", feed.user_title if feed.user_title != None else feed.title)
        if (dialog.exec_() == qtw.QDialog.Accepted):
            response = dialog.get_response() if dialog.get_response() != "" else None
            self.feed_manager.set_feed_user_title(feed, response)
            self.feed_model.update_row(index)

        
    def prompt_set_feed_refresh_rate(self, index: qtc.QModelIndex) -> None:
        """
        Opens a dialog which allows the user to set a feed's refresh rate.
        Tells the feed manager to set the refresh rate of the feed in the database.
        Tells the view to update the row of the passed index.
        """
        feed = index.internalPointer().data
        dialog = GenericDialog(lambda x: x.isdigit() or x == "", "Refresh Rate (seconds):", "Set Refresh Rate", str(feed.refresh_rate))
        if (dialog.exec_() == qtw.QDialog.Accepted):
            response = int(dialog.get_response()) if dialog.get_response() != "" else None
            self.feed_manager.set_refresh_rate(feed, response)
            self.feed_model.update_row(index)


    def feed_context_menu(self, position) -> None:
        """
        Outputs the context menu for items in the feed view.
        """
        index = self.feed_view.indexAt(position)
        
        if index.isValid():
            node = index.internalPointer()
            menu = qtw.QMenu()

            if node.data:
                refresh = menu.addAction("Refresh Feed")
                delete = menu.addAction("Delete Feed")
                set_refresh_rate = menu.addAction("Set Refresh Rate")
                set_custom_title = menu.addAction("Set Title")
                action = menu.exec_(self.feed_view.viewport().mapToGlobal(position))
                if action == delete:
                    self.prompt_delete_feed(index)
                elif action == refresh:
                    self.refresh_single(node.data)
                elif action == set_refresh_rate:
                    self.prompt_set_feed_refresh_rate(index)
                elif action == set_custom_title:
                    self.prompt_set_user_custom_title(index)

            else:
                add_feed = menu.addAction("Add Feed")
                add_folder = menu.addAction("Add Folder")
                delete_folder = menu.addAction("Delete Folder")
                action = menu.exec_(self.feed_view.viewport().mapToGlobal(position))
                if action == add_feed:
                    self.prompt_add_feed(index)
                elif action == add_folder:
                    self.prompt_add_folder(index)
                elif action == delete_folder:
                    self.prompt_delete_folder(index)

    
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


    def output_feeds(self) -> None:
        """
        Repopulates the feed view.
        """
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.feed_model.set_feeds(self.feeds_cache, self.feed_manager.get_all_folders())
        self.restore_expand_status()


    def output_articles(self) -> None:
        """
        Outputs the articles of the highlighted feed in the articles_view.
        """
        index = self.feed_view.currentIndex()
        self.articles_cache = []
        if index.isValid():
            node = index.internalPointer()
            if node.data != None:
                self.articles_cache = self.feed_manager.get_articles(node.data.db_id)
            

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
        Tells the feed manager to mark as read in the db.
        Decrements the currently highlighted feed's unread count by 1.
        """
        self.feed_manager.set_article_unread_status(article_id, False)
        self.articles_cache[row].unread = False
        self.article_model.update_row_unread_status(row)
        self.feed_view.currentIndex().internalPointer().data.unread_count -= 1
        self.feed_model.update_row(self.feed_view.currentIndex())


    def recieve_new_articles(self, articles: List[feedutility.Article], feed_id: int) -> None:
        """
        Recieves new article data from the feed manager and adds them to the views,
        if the currently highlighted feed is the correct feed.
        """
        current_index = self.feed_view.currentIndex()
        if current_index.isValid() and current_index.internalPointer().data.db_id == feed_id:
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
        self.feed_model.update_data()


    def restore_expand_status(self):
        self.feed_view.expandAll()
        # indexes = self.feed_model.match(self.feed_model.index(0, 0), qtc.Qt.DisplayRole, "*", -1, qtc.Qt.MatchWildcard|qtc.Qt.MatchRecursive)
        # for index in indexes:
        #     node = index.internalPointer()
        #     if node.folder:
        #         self.feed_view.setExpanded(index, True)


    def save_expand_status(self):
        indexes = self.feed_model.match(self.feed_model.index(0, 0), qtc.Qt.DisplayRole, "*", -1, qtc.Qt.MatchWildcard|qtc.Qt.MatchRecursive)
        for index in indexes:
            node = index.internalPointer()
            if node.folder:
                self.feed_view.setExpanded(index, True)


class ArticleModel(qtc.QAbstractItemModel):
    def __init__(self):
        """
        initialization.
        """
        qtc.QAbstractItemModel.__init__(self)
        self.ar : List[feedutility.Article] = []

    def rowCount(self, index: qtc.QModelIndex):
        """
        Returns the number of rows. When index is a valid row in the model, returns 0.
        """
        if index.isValid():
            return 0
        return len(self.ar)

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
        if role == qtc.Qt.DisplayRole or role == qtc.Qt.ToolTipRole:
            if in_index.column() == 0:
                return self.ar[in_index.row()].title
            if in_index.column() == 1:
                return self.ar[in_index.row()].author
            if in_index.column() == 2:
                return self.ar[in_index.row()].updated
        elif role == qtc.Qt.FontRole:
            f = qtg.QFont()
            f.setPointSize(10)
            if self.ar[in_index.row()].unread == True:
                f.setBold(True)
            return f
        return None

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

    def add_articles(self, articles: List[feedutility.Article]):
        """
        Adds appends an article to the cache, while refreshing the view.
        """
        self.beginInsertRows(qtc.QModelIndex(), len(self.ar), len(articles))
        self.ar += articles
        self.endInsertRows()

    def set_articles(self, articles) -> None:
        self.beginResetModel()
        self.ar = articles
        self.endResetModel()

    def update_row_unread_status(self, row):
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.FontRole])



class Node():
    def __init__(self, folder: feedutility.Folder=None, data: feedutility.Feed=None, parent: 'Node'=None, row: int=None):
        self.folder = folder
        self.children = []
        self.parent = parent
        self.data = data
        self.row = row



class FeedModel(qtc.QAbstractItemModel):
    def __init__(self):
        qtc.QAbstractItemModel.__init__(self)
        self.tree = Node()
        self.array : List[Node]

    def rowCount(self, in_index: qtc.QModelIndex):
        if in_index.isValid():
            return len(in_index.internalPointer().children)
        return len(self.tree.children)

    def add_feed(self, feed: feedutility.Feed, index: qtc.QModelIndex):
        if index.isValid():
            self.beginInsertRows(index, len(index.internalPointer().children), 1)
            index.internalPointer().children.append(feed)
            self.endInsertRows()


    def update_rows(self, l: List[Node]):
        for i,node in enumerate(l):
            node.row = i

    def remove_feed(self, index: qtc.QModelIndex):
        """
        Removes feed from the view's tree.
        """
        node = index.internalPointer()
        parent = node.parent
        row = node.row

        self.beginRemoveRows(index.parent(), row, row)
        del parent.children[row]
        self.update_rows(parent.children)
        self.endRemoveRows()

    def index(self, row, column, parent_index=qtc.QModelIndex()):
        """
        Returns QModelIndex for given row/column.
        """
        if parent_index.isValid():
            parent = parent_index.internalPointer()
        else:
            parent = self.tree
            
        if qtc.QAbstractItemModel.hasIndex(self, row, column, parent_index):
            return qtc.QAbstractItemModel.createIndex(self, row, column, parent.children[row])
        return qtc.QModelIndex()

    def parent(self, index):
        """
        Returns the parent index of an index.
        """
        if index.isValid():
            parent = index.internalPointer().parent
            if not parent is self.tree:
                return qtc.QAbstractItemModel.createIndex(self, parent.row, 0, parent)
        return qtc.QModelIndex()

    def columnCount(self, in_index):
        return 2

    def data(self, in_index, role):
        if not in_index.isValid():
            return None

        node = in_index.internalPointer()

        if node.data != None:
            if role == qtc.Qt.DisplayRole or role == qtc.Qt.ToolTipRole:
                if in_index.column() == 0:
                    return node.data.user_title if node.data.user_title != None else node.data.title
                if in_index.column() == 1:
                    return node.data.unread_count
        else:
            if role == qtc.Qt.DisplayRole:
                if in_index.column() == 0:
                    return node.folder.title
                if in_index.column() == 1:
                    return None

        if role == qtc.Qt.FontRole:
            f = qtg.QFont()
            f.setPointSize(10)
            if node.data and node.data.unread_count > 0:
                f.setBold(True)
            return f
        

    def set_feeds(self, feeds: List[feedutility.Feed], folders: List[feedutility.Folder]) -> None:
        tree = Node()
        self.array = []

        for folder in folders:
            node = Node(folder=folder)
            self.array.append(node)

            if folder.parent == 0:
                node.parent = tree
                node.row = len(tree.children)
                tree.children.append(node)
            else:
                parent = next(v for v in self.array if v.folder.db_id == folder.parent)
                node.parent = parent
                node.row = len(parent.children)
                parent.children.append(node)

        for feed in feeds:
            if feed.parent_folder == 0:
                tree.children.append(Node(data=feed, parent=tree, row=len(tree.children)))
            else:
                parent = next(v for v in self.array if v.folder.db_id == feed.parent_folder)
                parent.children.append(Node(data=feed, parent=parent, row=len(parent.children)))
            
        self.beginResetModel()
        self.tree = tree
        self.endResetModel()

    def headerData(self, section, orientation, role=qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal: # Horizontal
                return {
                    0: "Feed Name",
                    1: "Unread"
                }.get(section, None)

    def update_row(self, index: qtc.QModelIndex):
        self.dataChanged.emit(self.index(index.row(), 0, index), self.index(index.row(), 1, index), [qtc.Qt.DisplayRole, qtc.Qt.FontRole])

    def update_data(self):
        self.dataChanged.emit(qtc.QModelIndex(), qtc.QModelIndex())




class GenericDialog(qtw.QDialog):

    def __init__(self, verify, prompt, window_title, default_text):
        qtw.QDialog.__init__(self, None, qtc.Qt.WindowCloseButtonHint | qtc.Qt.WindowTitleHint)

        self.setObjectName(window_title)

        self.verify_function = verify
        
        vbox = qtw.QGridLayout()
        vbox.addWidget(qtw.QLabel(prompt), 0, 0, 1, 2)

        self.le = qtw.QLineEdit()
        self.le.setText(default_text)
        self.le.selectAll()
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
        self.error_label.repaint()
        if self.verify_function(self.le.text()):
            self.accept()
        else:
            self.error_label.setText("Verify Failed")

    def get_response(self):
        return self.le.text()