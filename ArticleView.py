import feed as feedutility
from feed_manager import FeedManager
import settings

import PySide2.QtWidgets as qtw
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg

from typing import List, Union


class ArticleView(qtw.QTreeView):
    """
    A view for displaying articles. article_selected_event fires when an article is selected.
    """

    article_content_event = qtc.Signal(str)

    def __init__(self, fm : FeedManager):
        super().__init__()

        # manager to contact for new information
        self.feed_manager = fm

        # the currently viewed feed
        self.current_feed : feedutility.Feed = None

        # model used by this treeview
        self.article_model = ArticleViewModel()

        self.setModel(self.article_model)
        self.header().setStretchLastSection(False)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)

        self.selectionModel().selectionChanged.connect(self.selection_changed)

        self.feed_manager.article_updated_event.connect(self.article_model.article_data_updated)


    def refresh(self) -> None:
        """
        Refreshes the data in the ArticleView using feed_manager.
        """
        if self.current_feed == None:
            self.article_model.set_articles([])
            return
        self.article_model.set_articles(self.feed_manager.get_articles(self.current_feed.db_id))
        return


    def receive_new_articles(self, feed_id, articles) -> None:
        """
        Receives new articles which the feed_manager has notified it about.
        feed_id is the id of the feed the articles are associated with.
        Should only update if the feed_id is the same one which is currently being displayed.
        """
        if self._current_feed_id != feed_id:
            return

        self.article_model.add_articles(articles)


    def select_feed(self, feed: feedutility.Feed) -> None:
        """
        Changes the view to fetch articles for the new feed. If it is -1,
        the view will be blank.
        """
        self.current_feed = feed
        self.refresh()


    def selection_changed(self) -> None:
        """
        Fires article_selected_event with the current selection.
        """
        index = self.currentIndex()

        if index.isValid():
            self.mark_article_read(index)
            self.article_content_event.emit(index.internalPointer().content)


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


    def article_context_menu(self, position) -> None:
        """
        Outputs the context menu for items in the article view.
        """
        index = self.feed_view.indexAt(position)
        
        if index.isValid():
            menu = qtw.QMenu()
            mark_read_action = menu.addAction("Mark Read")
            mark_unread_action = menu.addAction("Mark Unread")
            action = menu.exec_(self.feed_view.viewport().mapToGlobal(position))

            if (action == mark_read_action):
                self.mark_article_read(index)
            elif (action == mark_unread_action):
                self.mark_article_unread(index)

    
    def mark_article_read(self, index) -> None:
        """
        Tells the feed manager to mark the indicated article as read.
        """
        self.feed_manager.set_article_unread_status(self.current_feed, index.internalPointer().db_id, False)
        self.article_model.update_row_unread_status(index, False)


    def mark_article_unread(self, index) -> None:
        """
        Tells the feed manager to mark the indicated article as unread.
        """
        self.feed_manager.set_article_unread_status(index.internalPointer().db_id, True)
        self.article_model.update_row_unread_status(index, True)



class ArticleViewModel(qtc.QAbstractItemModel):
    def __init__(self):
        qtc.QAbstractItemModel.__init__(self)
        self.ar : List[feedutility.Article] = []


    def rowCount(self, index: qtc.QModelIndex):
        """
        Returns the number of rows.
        """
        # so index points to an article
        if index.isValid():
            return 0
        
        # must be the root index
        return len(self.ar)


    def index(self, row, column, parent_index=qtc.QModelIndex()):
        """
        Returns QModelIndex for given row/column.
        """
        if not self.hasIndex(row, column, parent_index):
            return qtc.QModelIndex()
        return self.createIndex(row, column, self.ar[row])


    def parent(self, in_index):
        """
        Returns parent of a node. 
        Articles do not have children so returns an invalid index.
        """
        return qtc.QModelIndex()


    def columnCount(self, in_index):
        """
        Returns the number of columns in the model.
        ArticleModel only has 3 columns, title, author, and last updated.
        """
        return 3


    def data(self, in_index, role):
        """
        Returns data about an index.
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
        Add a single article to the model.
        """
        

    def add_articles(self, articles: List[feedutility.Article]):
        """
        Adds multiple articles to the model. Currently only appends to the end.
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


    def update_row_unread_status(self, index, value):

        row = index.row()
        index.internalPointer().unread = value
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.FontRole])


    def article_data_updated(self, row):
        self.dataChanged.emit(qtc.QModelIndex(), qtc.QModelIndex())