import feed as feedutility
import feed_manager
import settings

import PySide2.QtWidgets as qtw
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg


class FeedView(qtw.QTreeView):
    """
    A view for displaying feeds. Allows selecting feeds, renaming them, and deleting them from
    the database. Has an feed_selected_event can be used to see when what is currently selected.
    """

    def __init__(self, fm : feed_manager.FeedManager):
        super().__init__()

        # event for when the selected feed changes. The integer is the db_id of the feed.
        self.feed_selected_event = qtc.Signal(int)

        self.selectionChanged.connect(self.changed)
        self.feed_manager = fm
        self.feed_model = FeedModel()
        self.setModel(self.feed_model)
        #self.setRootIsDecorated(False)
        self.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.feed_context_menu)
        self.header().setStretchLastSection(False)


    def changed(self) -> None:
        """
        """
        index = self.feed_view.currentIndex()
        self.articles_cache = []

        # could have been a folder that was selected
        if index.isValid() and type(index.internalPointer()) == feedutility.Feed:
            self.feed_selected_event.emit(index.internalPointer().db_id)
            

    def refresh(self) -> None:
        """
        Refreshes the data in the FeedView using feed_manager.
        """
        self.feeds_cache = self.feed_manager.get_all_feeds()
        self.feed_model.set_feeds(self.feeds_cache)
        self.restore_expand_status()


    def restore_expand_status(self):
        self.expandAll()
        # indexes = self.feed_model.match(self.feed_model.index(0, 0), qtc.Qt.DisplayRole, "*", -1, qtc.Qt.MatchWildcard|qtc.Qt.MatchRecursive)
        # for index in indexes:
        #     node = index.internalPointer()
        #     if node.folder:
        #         self.feed_view.setExpanded(index, True)


    def feed_context_menu(self, position) -> None:
        """
        Outputs the context menu for items in the feed view.
        """
        index = self.indexAt(position)
        
        if index.isValid():
            node = index.internalPointer()
            menu = qtw.QMenu()

            if type(node) == feedutility.Feed:
                refresh = menu.addAction("Refresh Feed")
                delete = menu.addAction("Delete Feed")
                set_refresh_rate = menu.addAction("Set Refresh Rate")
                set_custom_title = menu.addAction("Set Title")
                action = menu.exec_(self.viewport().mapToGlobal(position))
                if action == delete:
                    self.prompt_delete_feed(index)
                elif action == refresh:
                    self.refresh_single(node)
                elif action == set_refresh_rate:
                    self.prompt_set_feed_refresh_rate(index)
                elif action == set_custom_title:
                    self.prompt_set_user_custom_title(index)

            else:
                add_feed = menu.addAction("Add Feed...")
                add_folder = menu.addAction("Add Folder...")
                rename_folder = menu.addAction("Rename...")
                delete_folder = menu.addAction("Delete Folder")
                action = menu.exec_(self.viewport().mapToGlobal(position))
                if action == add_feed:
                    self.prompt_add_feed(index)
                elif action == add_folder:
                    self.prompt_add_folder(index)
                elif action == rename_folder:
                    self.prompt_rename_folder(index)
                elif action == delete_folder:
                    self.prompt_delete_folder(index)



    def prompt_add_feed(self, index: qtc.QModelIndex=None) -> None:
        """
        Opens a dialog allowing a user to enter a url for a new feed.
        Called when the add feed button is pressed. Opens a dialog which allows inputting a new feed.
        """
        dialog = GenericDialog(self.feed_manager.verify_feed_url, "Add Feed:", "Add Feed", "")
        if (dialog.exec_() == qtw.QDialog.Accepted):
            if index:
                folder = index.internalPointer()
            else:
                folder = self.feeds_cache
                index = qtc.QModelIndex()
            self.feed_model.beginInsertRows(index, len(folder.children), len(folder.children))
            self.feed_manager.add_feed_from_web(dialog.get_response(), folder)
            self.feed_model.endInsertRows()

            self.setExpanded(index, True)


    def prompt_delete_feed(self, index: qtc.QModelIndex) -> None:
        """
        Opens a message box prompt which confirms if the user wants to delete a feed.
        Deletes a feed from the view, then tells the feed manager to remove it from the database.
        """
        feed = index.internalPointer()
        response = qtw.QMessageBox.question(None, "Prompt", "Are you sure you want to delete '" + (feed.user_title if feed.user_title != None else feed.title) + "'?", qtw.QMessageBox.Yes | qtw.QMessageBox.No)
        if response == qtw.QMessageBox.Yes:
            self.feed_model.beginRemoveRows(index.parent(), feed.row, feed.row)
            self.feed_manager.delete_feed(feed)
            self.feed_model.endRemoveRows()


    def prompt_add_folder(self, index: qtc.QModelIndex=None) -> None:
        """
        Opens a dialog allowing a user to enter a name for a new folder.
        Adds a folder to the feed database, with the passed index as a parent.
        """
        dialog = GenericDialog(lambda x: True, "Add Folder:", "Add Folder", "")
        if (dialog.exec_() == qtw.QDialog.Accepted):
            if index:
                folder = index.internalPointer()
            else:
                folder = self.feeds_cache
                index = qtc.QModelIndex()
            self.feed_model.beginInsertRows(index, len(folder.children), len(folder.children))
            self.feed_manager.add_folder(dialog.get_response(), folder)
            self.feed_model.endInsertRows()


    def prompt_rename_folder(self, index: qtc.QModelIndex) -> None:
        """
        Opens a dialog allowing a user to rename a folder.
        """
        dialog = GenericDialog(lambda x: True, "Rename Folder:", "Rename Folder", "")
        if (dialog.exec_() == qtw.QDialog.Accepted):
            if index:
                folder = index.internalPointer()
            else:
                folder = self.feeds_cache
                index = qtc.QModelIndex()
            self.feed_manager.rename_folder(dialog.get_response(), folder)
            self.feed_model.update_row(index)


    def prompt_delete_folder(self, index: qtc.QModelIndex) -> None:
        """
        Opens a message box prompt which confirms if the user wants to delete a folder.
        Deletes the folder from the view then tells the feed manager to remove it from the database.
        Resets the screen.
        """
        folder = index.internalPointer()
        response = qtw.QMessageBox.question(None, "Prompt", "Are you sure you want to delete '" + folder.title + "'?", qtw.QMessageBox.Yes | qtw.QMessageBox.No)
        if response == qtw.QMessageBox.Yes:


            self.feed_model.beginRemoveRows(index.parent(), folder.row, folder.row)
            self.feed_manager.delete_folder(folder)
            self.feed_model.endRemoveRows()
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




class FeedModel(qtc.QAbstractItemModel):
    def __init__(self):
        qtc.QAbstractItemModel.__init__(self)
        self.tree = feedutility.Folder()

    def rowCount(self, in_index: qtc.QModelIndex):
        if in_index.isValid():
            node = in_index.internalPointer()
            if type(node) == feedutility.Folder:
                return len(in_index.internalPointer().children)
            return 0
        return len(self.tree.children)

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
            parent = index.internalPointer().parent_folder
            if not parent is self.tree:
                return qtc.QAbstractItemModel.createIndex(self, parent.row, 0, parent)
        return qtc.QModelIndex()

    def columnCount(self, in_index):
        """
        Returns 2. There are only two columns in FeedView, the feed name, and its unread count.
        """
        return 2

    def data(self, in_index, role):
        if not in_index.isValid():
            return None

        node = in_index.internalPointer()

        if type(node) == feedutility.Feed:
            if role == qtc.Qt.DisplayRole or role == qtc.Qt.ToolTipRole:
                if in_index.column() == 0:
                    return node.user_title if node.user_title != None else node.title
                if in_index.column() == 1:
                    return node.unread_count

        # must be a folder
        else:
            if role == qtc.Qt.DisplayRole:
                if in_index.column() == 0:
                    return node.title
                if in_index.column() == 1:
                    return None

        if role == qtc.Qt.FontRole:
            f = qtg.QFont()
            f.setPointSize(10)
            if type(node) == feedutility.Feed and node.unread_count > 0:
                f.setBold(True)
            return f
        

    def set_feeds(self, tree: feedutility.Folder) -> None:   
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