import operator
import logging

import PySide6.QtWidgets as qtw
import PySide6.QtCore as qtc
import PySide6.QtGui as qtg

from feed import Feed, Article, apply_action
from feed_manager import FeedManager
from settings import settings

QtModelIndex = qtc.QModelIndex | qtc.QPersistentModelIndex

class ArticleFilter(qtw.QWidget):
    """A view for displaying articles, and a textbox for filtering them.

    article_selected_event fires when an article is selected.
    """
    article_selected_event = qtc.Signal(str)

    def __init__(self, fm: FeedManager):
        super().__init__()

        layout = qtw.QVBoxLayout()
        self.setLayout(layout)


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
        self.current_feed: None | Feed = None

        # model used by this treeview
        self.article_view_model = ArticleViewModel(self)

        self.setModel(self.article_view_model)
        # self.header().setStretchLastSection(False)
        # self.setRootIsDecorated(False)
        # self.setSortingEnabled(True)
        self.selectionModel().selectionChanged.connect(self.selection_changed)
        # self.setAlternatingRowColors(True)

        self.feed_manager.article_updated_event.connect(self.article_view_model.update_article_data)
        self.feed_manager.new_article_event.connect(self.article_view_model.new_article)

        self.setContextMenuPolicy(qtc.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.handle_article_context_menu)
        self.doubleClicked.connect(self.handle_double_click)

        # these settings are what the default settings should be. They will be overwritten when restore is called
        self.header().setStretchLastSection(True)
        # self.header().setSectionResizeMode(0, qtw.QHeaderView.ResizeMode.Fixed)
        # self.header().setSectionResizeMode(1, qtw.QHeaderView.ResizeMode.Fixed)
        # self.header().setSectionResizeMode(2, qtw.QHeaderView.ResizeMode.ResizeToContents)
        self.setSortingEnabled(True)
        self.setRootIsDecorated(False)



    def refresh(self) -> None:
        """Refreshes the data in the ArticleView using feed_manager."""
        if self.current_feed is None:
            self.article_view_model.set_articles([])
            return
        self.article_view_model.set_articles(self.feed_manager.get_articles(self.current_feed.db_id))
        return


    def select_feed(self, feed: None | Feed = None) -> None:
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


    def recieve_new_articles(self, articles: list[Article], feed_id: int) -> None:
        """Recieves new article data from the feed manager and adds them to the views.

        Only adds articles which are the same as the currently highlighted feed
        """
        pass


    def update_all_data(self) -> None:
        """Updates all rows."""
        self.article_view_model.update_all_data()


    def handle_article_context_menu(self, mouse_position: qtc.QPoint) -> None:
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

            action = menu.exec(self.viewport().mapToGlobal(mouse_position))

            if action == toggle_action:
                if article.unread:
                    self.feed_manager.set_article_unread_status(self.current_feed, article, False)
                else:
                    self.feed_manager.set_article_unread_status(self.current_feed, article, True)
                self.article_view_model.update_row_unread_status(index)
            elif action == flag_action:
                self.feed_manager.toggle_article_flag(article)
                self.article_view_model.update_row_unread_status(index)


    def handle_double_click(self, index: qtc.QModelIndex) -> None:

        if index.isValid():
            # menu = qtw.QMenu()
            article: Article = index.internalPointer()

            if self.current_feed:
                apply_action(self.current_feed, article)


    def restore(self):
        # restore state
        if settings.article_view_headers != "":
            self.header().restoreState(qtc.QByteArray.fromBase64(bytes(settings.article_view_headers, "utf-8")))


    def resizeEvent(self, event: qtg.QResizeEvent):
        remaining_width = event.size().width() - self.columnWidth(2)
        self.setColumnWidth(0, round(remaining_width * 2 / 3))
        self.setColumnWidth(1, round(remaining_width / 3))
        # self.setColumnWidth(2, round(self.columnWidth(2) * remaining_width / ))


    def cleanup(self):
        # max_width = self.maximumViewportSize().width()
        # current_width = self.viewport().width()

        # save widths as if there were no scrollbar, since the view starts without one.
        # if there is a scrollbar, modify widths to be what they would be without it.
        # if self.viewport().width() < max_width:
        #     self.setColumnWidth(0, round(self.columnWidth(0) * max_width / current_width))
        #     self.setColumnWidth(1, round(self.columnWidth(1) * max_width / current_width))
        #     self.setColumnWidth(2, round(self.columnWidth(2) * max_width / current_width))
        settings.article_view_headers = str(self.header().saveState().toBase64(), 'utf-8')





class ArticleViewModel(qtc.QAbstractItemModel):
    """Item model which describes a list of articles."""

    definedrows = {
        0: "Name",
        1: "Author",
        2: "Updated"
    }

    def __init__(self, view: ArticleView):
        qtc.QAbstractItemModel.__init__(self)
        self.articles: list[Article] = []
        self.view = view


    def rowCount(self, parent: QtModelIndex = qtc.QModelIndex()) -> int:
        """Returns the number of rows."""
        # so index points to an article
        if parent.isValid():
            return 0

        # must be the root index
        return len(self.articles)


    def index(self, row: int, column: int, parent: QtModelIndex = qtc.QModelIndex()):
        """Returns QModelIndex for given row/column."""
        if not self.hasIndex(row, column, parent):
            return qtc.QModelIndex()
        return self.createIndex(row, column, self.articles[row])


    def parent(self, _):
        """Returns parent of a node.

        Articles do not have children so returns an invalid index.
        """
        return qtc.QModelIndex()


    def columnCount(self, parent: QtModelIndex = qtc.QModelIndex()):
        """Returns the number of columns in the model.

        ArticleModel only has 3 columns, title, author, and last updated.
        """
        return 3


    def data(self, index: QtModelIndex, role: int = 0):
        """Returns data about an index."""
        if not index.isValid():
            return None

        article: Article = index.internalPointer()
        if role in (qtc.Qt.DisplayRole, qtc.Qt.ToolTipRole):
            if index.column() == 0:
                return article.title
            if index.column() == 1:
                return article.author
            if index.column() == 2:
                return article.updated.astimezone().strftime('%a %b %d, %Y %I:%M %p')

        elif role == qtc.Qt.FontRole:
            font = qtg.QFont()
            font.setPointSize(settings.font_size)
            if article.unread is True:
                font.setBold(True)
            return font

        elif role == qtc.Qt.ForegroundRole:
            if article.flag is True:
                return qtg.QColor(qtc.Qt.red)

        return None


    def headerData(self, section: int, orientation: qtc.Qt.Orientation, role: int=qtc.Qt.DisplayRole):
        if role == qtc.Qt.DisplayRole:
            if orientation == qtc.Qt.Horizontal:
                return self.definedrows.get(section, None)
        return None


    def sort(self, column: int, order: qtc.Qt.SortOrder = qtc.Qt.AscendingOrder):
        self.beginResetModel()
        reverse = order == qtc.Qt.AscendingOrder
        if column == 0:
            self.articles.sort(key=lambda e: e.title, reverse=reverse)
        elif column == 1:
            self.articles.sort(key=lambda e: e.author, reverse=reverse)
        elif column == 2:
            self.articles.sort(key=lambda e: e.updated, reverse=reverse)
        self.endResetModel()


    def set_articles(self, articles: list[Article]) -> None:
        """Resets whats in the display with new articles.

        Causes unselecting.
        """
        self.articles = articles
        self.sort(self.view.header().sortIndicatorSection(), self.view.header().sortIndicatorOrder())


    def update_row_unread_status(self, index: qtc.QModelIndex):
        """Emits a change in the unread status for a row in the article view."""
        row = index.row()
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.FontRole])


    def update_row_flag_status(self, index: qtc.QModelIndex):
        """Emits a change in the flag status for a row in the article view."""
        row = index.row()
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [qtc.Qt.ForegroundRole])


    def update_article_data(self, article: Article):
        """Updates an existing article in the model with data."""
        if self.view.current_feed is not None and self.view.current_feed.db_id == article.feed_id:
            i = next((i for i, v in enumerate(self.articles) if v.identifier == article.identifier), None)
            if i is not None:
                self.articles[i].__dict__ = article.__dict__
                self.dataChanged.emit(self.index(i, 0), self.index(i, self.columnCount()))
            else:
                logging.error("Article was updated in manager, but not already in view")


    def new_article(self, article: Article):
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
