from typing import Any, Callable

import PySide6.QtWidgets as qtw
import PySide6.QtCore as qtc
import PySide6.QtGui as qtg
from PySide6.QtUiTools import QUiLoader

from feed import Feed, FeedData, Folder, verify_feed_url
import feed_manager
from settings import settings

QtModelIndex = qtc.QModelIndex | qtc.QPersistentModelIndex

class FeedView(qtw.QTreeView):
    """A tree view for displaying feeds.

    feed_selected_event fires when a feed is selected.
    It should be the sole interface for interacting with the feeds in the feed manager,
    and there should only be one of these views.
    """

    # event for when the selected feed changes. The integer is the db_id of the feed.
    feed_selected_event = qtc.Signal(Feed)

    def __init__(self, fm: feed_manager.FeedManager):
        super().__init__()

        self.feed_manager = fm
        self.feeds_cache = self.feed_manager.feed_cache
        self.feed_view_model = FeedViewModel(self.feeds_cache)
        self.setModel(self.feed_view_model)
        self.selectionModel().selectionChanged.connect(self.fire_selected_event)
        # self.setRootIsDecorated(False)
        self.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.feed_context_menu)


        self.feed_manager.feeds_updated_event.connect(self.update_all_data)
        self.restore_expand_status()

        # these settings are what the default settings should be. They will be overwritten when restore is called
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, qtw.QHeaderView.ResizeMode.Fixed)
        self.header().setSectionResizeMode(1, qtw.QHeaderView.ResizeMode.Fixed)


    def fire_selected_event(self) -> None:
        """
        Fires feed_selected_event with the current selection.
        """
        index = self.currentIndex()

        # could have been a folder that was selected
        if index.isValid() and type(index.internalPointer()) is Feed:
            self.feed_selected_event.emit(index.internalPointer())


    def restore_expand_status(self):
        """Restores the expand/collapse state of folders from previous launch."""
        self.expandAll()
        # TODO: properly implement this
        # indexes = self.feed_model.match(self.feed_model.index(0, 0), qtc.Qt.DisplayRole, "*", -1, qtc.Qt.MatchWildcard|qtc.Qt.MatchRecursive)
        # for index in indexes:
        #     node = index.internalPointer()
        #     if node.folder:
        #         self.feed_view.setExpanded(index, True)


    def update_all_data(self) -> None:
        """Updates feed information."""
        self.feed_view_model.update_all_data()


    def feed_context_menu(self, position: qtc.QPoint) -> None:
        """Outputs the context menu for items in the feed view."""
        index = self.indexAt(position)

        if index.isValid():
            node: Feed = index.internalPointer()
            menu = qtw.QMenu()

            if type(node) is Feed:
                refresh = menu.addAction("Refresh Feed")
                delete = menu.addAction("Delete Feed")
                options = menu.addAction("Feed Options...")
                action = menu.exec(self.viewport().mapToGlobal(position))
                if action == delete:
                    self.prompt_delete_feed(index)
                elif action == refresh:
                    self.refresh_single(node)
                elif action == options:
                    self.dialog_feed_settings(index)

            else:
                # it is a folder
                add_feed = menu.addAction("Add Feed...")
                add_folder = menu.addAction("Add Folder...")
                rename_folder = menu.addAction("Rename...")
                delete_folder = menu.addAction("Delete Folder")
                action = menu.exec(self.viewport().mapToGlobal(position))
                if action == add_feed:
                    self.prompt_add_feed(index)
                elif action == add_folder:
                    self.prompt_add_folder(index)
                elif action == rename_folder:
                    self.prompt_rename_folder(index)
                elif action == delete_folder:
                    self.prompt_delete_folder(index)



    def prompt_add_feed(self, index: qtc.QModelIndex | None = None) -> None:
        """
        Opens a dialog allowing a user to enter a url for a new feed.
        """
        dialog = VerifyDialog(verify_feed_url, "Add Feed:", "Add Feed", "")
        if dialog.exec() == qtw.QDialog.Accepted:
            if index:
                folder: Folder = index.internalPointer()
            else:
                folder = self.feeds_cache
                index = qtc.QModelIndex()
            self.feed_view_model.beginInsertRows(index, len(folder.children), len(folder.children))
            self.feed_manager.add_feed(dialog.get_response(), folder, "rss")
            self.feed_view_model.endInsertRows()

            self.setExpanded(index, True)


    def prompt_delete_feed(self, index: qtc.QModelIndex) -> None:
        """
        Opens a message box prompt which confirms if the user wants to delete a feed.
        Deletes a feed from the view, then tells the feed manager to remove it from the database.
        """
        feed: Feed = index.internalPointer()
        response = qtw.QMessageBox.question(self, "Prompt", "Are you sure you want to delete '" + (feed.user_title if feed.user_title is not None else feed.title) + "'?", qtw.QMessageBox.Yes | qtw.QMessageBox.No)
        if response == qtw.QMessageBox.Yes:
            self.feed_view_model.beginRemoveRows(index.parent(), index.row(), index.row())
            self.feed_manager.delete_feed(feed)
            self.feed_view_model.endRemoveRows()


    def prompt_add_folder(self, index: qtc.QModelIndex | None = None) -> None:
        """
        Opens a dialog allowing a user to enter a name for a new folder.
        Adds a folder to the feed database, with the passed index as a parent.
        """
        dialog = VerifyDialog(lambda _: True, "Add Folder:", "Add Folder", "")
        if dialog.exec() == qtw.QDialog.Accepted:
            if index:
                folder: Folder = index.internalPointer()
            else:
                folder = self.feeds_cache
                index = qtc.QModelIndex()
            self.feed_view_model.beginInsertRows(index, len(folder.children), len(folder.children))
            self.feed_manager.add_folder(dialog.get_response(), folder)
            self.feed_view_model.endInsertRows()


    def prompt_rename_folder(self, index: qtc.QModelIndex) -> None:
        """
        Opens a dialog allowing a user to rename a folder.
        """
        dialog = VerifyDialog(lambda _: True, "Rename Folder:", "Rename Folder", "")
        if dialog.exec() == qtw.QDialog.Accepted:
            if index:
                folder: Folder = index.internalPointer()
            else:
                folder = self.feeds_cache
                index = qtc.QModelIndex()
            self.feed_manager.rename_folder(dialog.get_response(), folder)
            self.feed_view_model.update_row(index)


    def prompt_delete_folder(self, index: qtc.QModelIndex) -> None:
        """Opens a message box prompt which confirms if the user wants to delete a folder."""
        folder: Folder = index.internalPointer()
        response = qtw.QMessageBox.question(self, "Prompt", "Are you sure you want to delete '" + folder.title + "'?", qtw.QMessageBox.Yes | qtw.QMessageBox.No)
        if response == qtw.QMessageBox.Yes:

            self.feed_view_model.beginRemoveRows(index.parent(), index.row(), index.row())
            self.feed_manager.delete_folder(folder)
            self.feed_view_model.endRemoveRows()


    def prompt_set_user_custom_title(self, index: qtc.QModelIndex) -> None:
        """
        Opens a dialog which allows the user to enter a custom title for a feed.
        """
        feed: Feed = index.internalPointer()
        dialog = VerifyDialog(lambda _: True, "Title:", "Set Title", feed.user_title if feed.user_title is not None else feed.title)
        if dialog.exec() == qtw.QDialog.Accepted:
            response = dialog.get_response()
            response = response if response != "" else None

            data = FeedData()
            data.user_title = response
            self.feed_manager.update_feed(feed, data)
            self.feed_view_model.update_row(index)


    def prompt_set_feed_refresh_rate(self, index: qtc.QModelIndex) -> None:
        """
        Opens a dialog which allows the user to set a feed's refresh rate.
        """
        feed: Feed = index.internalPointer()
        dialog = VerifyDialog(lambda x: x.isdigit() or x == "", "Refresh Rate (seconds):", "Set Refresh Rate", str(feed.refresh_rate))
        if dialog.exec() == qtw.QDialog.Accepted:
            response = int(dialog.get_response()) if dialog.get_response() != "" else None
            data = FeedData()
            data.refresh_rate = response
            self.feed_manager.update_feed(feed, data)
            self.feed_view_model.update_row(index)


    def dialog_feed_settings(self, index: qtc.QModelIndex) -> None:
        """Opens a dialog that allows changing a feed's settings."""

        window = QUiLoader().load("ui/feedsettings.ui")

        feed: Feed = index.internalPointer()

        window.customTitleCheck.setChecked(feed.user_title is not None)
        window.customTitleCheck.toggled.connect(window.customTitle.setEnabled)
        if feed.user_title is not None:
            window.customTitle.setText(feed.user_title)
            window.customTitle.setEnabled(True)

        window.refreshRateCheck.setChecked(feed.refresh_rate is not None)
        window.refreshRateCheck.toggled.connect(window.refreshRate.setEnabled)
        if feed.refresh_rate is not None:
            window.refreshRate.setValue(feed.refresh_rate)
            window.refreshRate.setEnabled(True)

        window.deleteTimeCheck.setChecked(feed.delete_time is not None)
        window.deleteTimeCheck.toggled.connect(window.deleteTime.setEnabled)
        if feed.delete_time is not None:
            window.deleteTime.setValue(feed.delete_time)
            window.deleteTime.setEnabled(True)

        window.notifyCheck.setChecked(feed.ignore_new)

        window.setWindowFlags(qtc.Qt.WindowCloseButtonHint | qtc.Qt.WindowTitleHint)

        window.show()
        if window.exec() == qtw.QDialog.Accepted:
            
            data = FeedData()
            data.user_title = window.customTitle.text() if window.customTitleCheck.isChecked() else None
            data.refresh_rate = window.refreshRate.value() if window.refreshRateCheck.isChecked() else None
            data.delete_time = window.deleteTime.value() if window.deleteTimeCheck.isChecked() else None
            data.ignore_new = window.notifyCheck.isChecked()

            self.feed_manager.update_feed(feed, data)


    def refresh_single(self, feed: Feed) -> None:
        """Tells the feed manager to update the feed.

        Called when a refresh button is pressed.
        """
        self.feed_manager.refresh_feed(feed)


    def restore(self):
        # restore geometry
        if settings.feed_view_headers != "":
            self.header().restoreState(qtc.QByteArray.fromBase64(bytes(settings.feed_view_headers, "utf-8")))


    def resizeEvent(self, event: qtg.QResizeEvent):
        remaining_width = event.size().width()
        self.setColumnWidth(0, round(remaining_width * 3 / 4))
        self.setColumnWidth(1, round(remaining_width / 4))


    def cleanup(self):
        # save headers as they are now, since the view will be the same on restart.
        settings.feed_view_headers = str(self.header().saveState().toBase64(), 'utf-8')


class FeedViewModel(qtc.QAbstractItemModel):
    """Item model which describes folders which contain feeds or other folders."""

    definedrows = {
        0: "Feed Name",
        1: "Unread"
    }

    def __init__(self, folder: Folder):
        qtc.QAbstractItemModel.__init__(self)
        self.tree = folder



    def rowCount(self, parent: QtModelIndex = qtc.QModelIndex()):
        if parent.isValid():
            node: Any = parent.internalPointer()
            if type(node) is Folder:
                return len(node.children)
            return 0
        return len(self.tree.children)


    def index(self, row: int, column: int, parent: QtModelIndex = qtc.QModelIndex()):
        """
        Returns QModelIndex for given row/column.
        """
        folder: Folder
        if parent.isValid():
            folder = parent.internalPointer()
        else:
            folder = self.tree

        if self.hasIndex(row, column, parent):
            return self.createIndex(row, column, folder.children[row])
        return qtc.QModelIndex()


    def parent(self, index: qtc.QModelIndex):
        """
        Returns the parent index of an index.
        """
        if index.isValid():
            parent = index.internalPointer().parent_folder
            if parent is not self.tree:
                return qtc.QAbstractItemModel.createIndex(self, parent.parent_folder.children.index(parent), 0, parent)
        return qtc.QModelIndex()


    def columnCount(self, *_):
        """
        There are only two columns in FeedView, the feed name, and its unread count.
        """
        return 2


    def data(self, index: QtModelIndex, role: int = 0):
        if not index.isValid():
            return None

        node: Feed | Folder = index.internalPointer()

        if type(node) is Feed:
            if role in (qtc.Qt.DisplayRole, qtc.Qt.ToolTipRole):
                if index.column() == 0:
                    return node.user_title if node.user_title is not None else node.title
                if index.column() == 1:
                    return node.unread_count

        # must be a folder
        else:
            if role == qtc.Qt.DisplayRole:
                if index.column() == 0:
                    return node.title
                if index.column() == 1:
                    return None

        if role == qtc.Qt.FontRole:
            font = qtg.QFont()
            font.setPointSize(settings.font_size)
            if type(node) is Feed and node.unread_count > 0:
                font.setBold(True)
            return font

        return None


    def set_feeds(self, tree: Folder) -> None:
        """Replaces the data in the model with new data."""
        self.beginResetModel()
        self.tree = tree
        self.endResetModel()


    def headerData(self, section: int, orientation: qtc.Qt.Orientation, role: int = qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal:  # Horizontal
                return self.definedrows.get(section, None)
        return None


    def update_row(self, index: qtc.QModelIndex):
        """Emits a data changed signal for a row in the feed view."""
        self.dataChanged.emit(self.index(index.row(), 0, index), self.index(index.row(), 1, index), [qtc.Qt.DisplayRole, qtc.Qt.FontRole])


    def update_all_data(self):
        """Updates all rows."""
        self.dataChanged.emit(qtc.QModelIndex(), qtc.QModelIndex())



class VerifyDialog(qtw.QDialog):
    """Line input dialog which does a check on the input before allowing it to be accepted."""


    def __init__(self, verify: Callable[[str], bool], prompt: str, window_title: str, default_text: str):
        qtw.QDialog.__init__(self, None, qtc.Qt.WindowCloseButtonHint | qtc.Qt.WindowTitleHint)

        self.setObjectName(window_title)

        self.verify_function = verify

        layout = qtw.QGridLayout()
        layout.addWidget(qtw.QLabel(prompt), 0, 0, 1, 2)

        self.input_field = qtw.QLineEdit()
        self.input_field.setText(default_text)
        self.input_field.selectAll()
        layout.addWidget(self.input_field, 1, 0, 1, 2)

        buttons = qtw.QDialogButtonBox(qtw.QDialogButtonBox.Ok | qtw.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.verify_response)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 2, 1, 1, 1)

        self.error_label = qtw.QLabel("")
        self.error_label.setMinimumWidth(qtg.QFontMetrics(qtg.QFont()).horizontalAdvance("Verify Failed"))
        layout.addWidget(self.error_label, 2, 0, 1, 1)

        layout.setSizeConstraint(qtw.QLayout.SetFixedSize)

        self.setLayout(layout)

        self.show()


    def verify_response(self):
        """Checks if the input in the field is valid. Displays an error message if it is not."""
        self.error_label.setText("Verifying...")
        self.error_label.repaint()
        if self.verify_function(self.input_field.text()):
            self.accept()
        else:
            self.error_label.setText("Verify Failed")


    def get_response(self):
        """Returns the input from the user in the input field."""
        return self.input_field.text()
