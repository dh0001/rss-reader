import operator
import logging
from typing import List, Optional, Union, Any

import PySide2.QtWidgets as qtw
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg

from feed import Feed, Article
from feed_manager import FeedManager
from settings import settings


class ArticleFilter(qtw.QWidget):
    """A view for displaying articles, and a textbox for filtering them.

    article_selected_event fires when an article is selected.
    """
    article_selected_event = qtc.Signal(str)

    def __init__(self, fm: FeedManager):
        super().__init__()

        self.lay = qtw.QVBoxLayout()
        self.setLayout(self.lay)


class ArticleView(qtw.QTreeView):
    """A view for displaying articles.

    article_selected_event fires when an article is selected.
    """
    article_selected_event = qtc.Signal(Article)

    def __init__(self, fm: FeedManager):
        super().__init__()

        # manager to contact for new information
        self.feed_manager = fm

        # the currently viewed feed
        self.current_feed: Union[None, Feed] = None

        # model used by this treeview
        self.article_view_model = ArticleViewModel(self)

        self.setModel(self.article_view_model)
        self.header().setStretchLastSection(False)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.selectionModel().selectionChanged.connect(self.selection_changed)
        self.setAlternatingRowColors(True)

        self.feed_manager.article_updated_event.connect(self.article_view_model.update_article_data)
        self.feed_manager.new_article_event.connect(self.article_view_model.new_article)

        self.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.article_context_menu)


    def refresh(self) -> None:
        """Refreshes the data in the ArticleView using feed_manager."""
        if self.current_feed is None:
            self.article_view_model.set_articles([])
            return
        self.article_view_model.set_articles(self.feed_manager.get_articles(self.current_feed.db_id))
        return


    def select_feed(self, feed: Union[None, Feed] = None) -> None:
        """Changes which feed's articles should be shown in the view.

        If feed is unspecified, the view will be blank.
        """
        self.current_feed = feed
        self.refresh()


    def selection_changed(self) -> None:
        """Fires article_selected_event with the current selection, also marks the article as read.

        Should only be called by event.
        """
        index = self.currentIndex()

        if index.isValid():
            article: Article = index.internalPointer()
            if article.unread is True:
                if self.current_feed is None:
                    logging.error("current feed is none, but article was selected!")
                    return
                self.feed_manager.set_article_unread_status(self.current_feed, article, False)
            self.article_selected_event.emit(article)


    def recieve_new_articles(self, articles: List[Article], feed_id: int) -> None:
        """Recieves new article data from the feed manager and adds them to the views.

        Only adds articles which are the same as the currently highlighted feed
        """


    def update_all_data(self) -> None:
        """Updates all rows."""
        self.article_view_model.update_all_data()


    def article_context_menu(self, mouse_position) -> None:
        """Outputs the context menu for items in the article view."""
        index = self.indexAt(mouse_position)

        if self.current_feed is None:
            return

        if index.isValid():
            menu = qtw.QMenu()
            article: Article = index.internalPointer()

            if article.unread:
                toggle_action = menu.addAction("Mark Read")
            else:
                toggle_action = menu.addAction("Mark Unread")
            if article.flag:
                flag_action = menu.addAction("Unflag Article")
            else:
                flag_action = menu.addAction("Flag Article")

            action = menu.exec_(self.viewport().mapToGlobal(mouse_position))

            if action == toggle_action:
                if article.unread:
                    self.feed_manager.set_article_unread_status(self.current_feed, article, False)
                else:
                    self.feed_manager.set_article_unread_status(self.current_feed, article, True)
                self.article_view_model.update_row_unread_status(index)
            elif action == flag_action:
                self.feed_manager.toggle_article_flag(article)
                self.article_view_model.update_row_unread_status(index)




class ArticleViewModel(qtc.QAbstractItemModel):
    """Item model which describes a list of articles."""

    definedrows = {
        0: "Name",
        1: "Author",
        2: "Updated"
    }

    def __init__(self, view):
        qtc.QAbstractItemModel.__init__(self)
        self.articles: List[Article] = []
        self.view = view


    def rowCount(self, index: qtc.QModelIndex) -> int:
        """Returns the number of rows."""
        # so index points to an article
        if index.isValid():
            return 0

        # must be the root index
        return len(self.articles)


    def index(self, row, column, parent_index=qtc.QModelIndex()):
        """Returns QModelIndex for given row/column."""
        if not self.hasIndex(row, column, parent_index):
            return qtc.QModelIndex()
        return self.createIndex(row, column, self.articles[row])


    def parent(self, _in_index):
        """Returns parent of a node.

        Articles do not have children so returns an invalid index.
        """
        return qtc.QModelIndex()


    def columnCount(self, _in_index=None):
        """Returns the number of columns in the model.

        ArticleModel only has 3 columns, title, author, and last updated.
        """
        return 3


    def data(self, index, role):
        """Returns data about an index."""
        if not index.isValid():
            return None

        if role in (qtc.Qt.DisplayRole, qtc.Qt.ToolTipRole):
            if index.column() == 0:
                return index.internalPointer().title
            if index.column() == 1:
                return index.internalPointer().author
            if index.column() == 2:
                return index.internalPointer().updated.astimezone().strftime('%a %b %d, %Y %I:%M %p')

        elif role == qtc.Qt.FontRole:
            font = qtg.QFont()
            font.setPointSize(settings["font_size"])
            if index.internalPointer().unread is True:
                font.setBold(True)
            return font

        elif role == qtc.Qt.ForegroundRole:
            if index.internalPointer().flag is True:
                return qtg.QColor(qtc.Qt.red)

        return None


    def headerData(self, section, orientation, role=qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal:
                return self.definedrows.get(section, None)
        return None


    def sort(self, column, ascending=qtc.Qt.AscendingOrder):
        self.beginResetModel()
        ascending = ascending is qtc.Qt.AscendingOrder
        if column == 0:
            self.articles.sort(key=lambda e: e.title, reverse=ascending)
        elif column == 1:
            self.articles.sort(key=lambda e: e.author, reverse=ascending)
        elif column == 2:
            self.articles.sort(key=lambda e: e.updated, reverse=ascending)
        self.endResetModel()


    def set_articles(self, articles: List[Article]) -> None:
        """Resets whats in the display with new articles.

        Causes unselecting.
        """
        self.articles = articles
        self.sort(self.view.header().sortIndicatorSection(), self.view.header().sortIndicatorOrder())


    def update_row_unread_status(self, index):
        """Emits a change in the unread status for a row in the article view."""
        row = index.row()
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.FontRole])


    def update_row_flag_status(self, index):
        """Emits a change in the flag status for a row in the article view."""
        row = index.row()
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.ForegroundRole])


    def update_article_data(self, article):
        """Updates an existing article in the model with data."""
        if self.view.current_feed is not None and self.view.current_feed.db_id == article.feed_id:
            i = next((i for i, v in enumerate(self.articles) if v.identifier == article.identifier), None)
            if i is not None:
                self.articles[i].__dict__ = article.__dict__
                self.dataChanged.emit(self.index(i, 0), self.index(i, self.columnCount()))
            else:
                logging.error("Article was updated in manager, but not already in view")


    def new_article(self, article):
        """Updates the model with a new article."""
        if self.view.current_feed is not None and self.view.current_feed.db_id == article.feed_id:
            if self.view.header().sortIndicatorOrder() == qtc.Qt.AscendingOrder:
                operation = operator.gt
            else:
                operation = operator.lt
            section = ["title", "author", "updated"][self.view.header().sortIndicatorSection()]

            i = next((i for (i, v) in enumerate(self.articles) if operation(getattr(article, section), getattr(v, section))), len(self.articles))
            self.beginInsertRows(qtc.QModelIndex(), i, i + 1)
            self.articles.insert(i, article)
            self.endInsertRows()


    def update_all_data(self):
        """Emits a signal that all data has changed in the model."""
        self.dataChanged.emit(qtc.QModelIndex(), qtc.QModelIndex())
