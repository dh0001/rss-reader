import feed as feedutility
from feed_manager import FeedManager
import settings

import PySide2.QtWidgets as qtw
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg

from typing import List, Union


class ArticleView(qtw.QTreeView):
    """
    A widget for displaying articles.
    """

    def __init__(self, fm : FeedManager):
        super().__init__()

        # an event for request to read an article, 1 argument which is db_id of article
        self.article_read_event = qtc.Signal(int)

        # manager to contact for new information
        self._feed_manager = fm

        # the currently viewed feed
        self._current_feed_id : int

        # model used by this treeview
        self._article_model = ArticleModel()

        self.setModel(self.article_model)
        self.header().setStretchLastSection(False)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)

        

    def refresh(self) -> None:
        """
        Refreshes the data in the ArticleView using feed_manager.
        """
        if _current_feed_id == -1:
            self._article_model.set_articles([])
            return
        self._article_model.set_articles(self.feed_manager.get_articles(self.current_feed_id))
        return

    def receive_new_articles(self, feed_id, articles) -> None:
        """
        Receives new articles which the feed_manager has notified it about.
        feed_id is the id of the feed the articles are associated with.
        Should only update if the feed_id is the same one which is currently being displayed.
        """
        if self._current_feed_id != feed_id:
            return

        self._article_model.add_articles(articles)

    def select_article(self, db_id: int) -> None:
        """
        Changes the view to fetch articles for the new feed_id. If it is -1,
        the view will be blank.
        """
        self._current_feed_id = db_id
        self.refresh()



class ArticleModel(qtc.QAbstractItemModel):
    def __init__(self):
        qtc.QAbstractItemModel.__init__(self)
        self.ar : List[feedutility.Article] = []

    def rowCount(self, index: qtc.QModelIndex):
        """
        Overwritten function which returns the number of rows.
        """

        # so index points to an article
        if index.isValid():
            return 0
        
        # must be index for root
        return len(self.ar)

    def index(self, in_row, in_column, in_parent=None):
        """
        Overwritten function which returns QModelIndex for given row/column.
        """
        if not qtc.QAbstractItemModel.hasIndex(self, in_row, in_column):
            return qtc.QModelIndex()
        return qtc.QAbstractItemModel.createIndex(self, in_row, in_column, 1)

    def parent(self, in_index):
        """
        Overwritten function which returns parent of a node.
        Articles do not have children so returns an invalid index.
        """
        return qtc.QModelIndex()

    def columnCount(self, in_index):
        """
        Overwritten function which returns the number of columns in the model.
        ArticleView only has 3 columns, title, author, and last updated.
        """
        return 3

    def data(self, in_index, role):
        """
        Overwritten function which returns data about an index.
        """
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

            # TODO: font should be user customizable
            f = qtg.QFont()
            f.setPointSize(10)
            if self.ar[in_index.row()].unread == True:
                f.setBold(True)
            return f
        return None

    def headerData(self, section, orientation, role=qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal:
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


    def add_article(self, article: feedutility.Article):
        """
        add a single article to its proper place.
        """
        

    def add_articles(self, articles: List[feedutility.Article]):
        """
        Adds appends an article to the cache, while refreshing the view.
        """
        self.beginInsertRows(qtc.QModelIndex(), len(self.ar), len(self.ar) + len(articles))
        self.ar += articles
        self.endInsertRows()

    def set_articles(self, articles) -> None:
        """
        Resets whats in the display with new articles. Causes unselecting.
        """
        self.beginResetModel()
        self.ar = articles
        self.endResetModel()

    def update_row_unread_status(self, row):
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.FontRole])