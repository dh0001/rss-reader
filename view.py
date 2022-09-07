import PySide6.QtWidgets as qtw
import PySide6.QtCore as qtc
import PySide6.QtGui as qtg
import PySide6.QtUiTools as qut

from feed import Feed, Article, Folder
import feed_manager
from settings import settings
from feed_view import FeedView
from article_view import ArticleView


class View(qtw.QMainWindow):
    """Handles all interaction with the user."""

    def __init__(self, mgr: feed_manager.FeedManager):

        super().__init__()

        self.feed_manager = mgr

        self.article_view = ArticleView(self.feed_manager)
        self.feed_view = FeedView(self.feed_manager)
        self.content_view = TBrowser()
        self.article_content_splitter = qtw.QSplitter(qtc.Qt.Vertical)
        self.feed_rhs_splitter = qtw.QSplitter(qtc.Qt.Horizontal)
        self.tray_icon = qtw.QSystemTrayIcon()

        # initialize GUI
        self.setWindowTitle('RSS Reader')
        # self.main_window.resize(800, 600)

        root_widget = qtw.QWidget()
        self.setCentralWidget(root_widget)

        self.content_view.setOpenExternalLinks(True)

        self.article_content_splitter.addWidget(self.article_view)
        self.article_content_splitter.addWidget(self.content_view)
        self.feed_rhs_splitter.addWidget(self.feed_view)
        self.feed_rhs_splitter.addWidget(self.article_content_splitter)
        # self.article_content_splitter.setSizes([200, 300])
        # self.feed_rhs_splitter.setSizes([200, 500])

        hbox = qtw.QHBoxLayout(root_widget)
        hbox.addWidget(self.feed_rhs_splitter)
        root_widget.setLayout(hbox)

        # add menu bar
        menu_bar = self.menuBar().addMenu('Options')
        menu_bar.addAction("Add root feed...").triggered.connect(self.feed_view.prompt_add_feed)
        menu_bar.addAction("Add root folder...").triggered.connect(self.feed_view.prompt_add_folder)
        menu_bar.addAction("Update All Feeds").triggered.connect(self.refresh_all)
        menu_bar.addAction("Settings...").triggered.connect(self.settings_dialog)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)


        # add tray icon
        self.update_icon()
        tray_menu = qtw.QMenu()
        tray_menu.addAction("Update All Feeds").triggered.connect(self.refresh_all)
        tray_menu.addSeparator()
        tray_menu.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()


        # restore geometry in the proper order
        if settings.state != "":
            self.restoreState(qtc.QByteArray.fromBase64(bytes(settings.state, "utf-8")))
        if settings.geometry != "":
            self.restoreGeometry(qtc.QByteArray.fromBase64(bytes(settings.geometry, "utf-8")))
        if settings.splitter1 != "":
            self.article_content_splitter.restoreState(qtc.QByteArray.fromBase64(bytes(settings.splitter1, "utf-8")))
        if settings.splitter2 != "":
            self.feed_rhs_splitter.restoreState(qtc.QByteArray.fromBase64(bytes(settings.splitter2, "utf-8")))
        self.feed_view.restore()
        self.article_view.restore()

        self.feed_view.feed_selected_event.connect(self.article_view.select_feed)
        self.article_view.article_selected_event.connect(self.output_content)
        self.tray_icon.activated.connect(self.tray_activated)
        self.feed_manager.feeds_updated_event.connect(self.update_icon)

        self.show()


    def cleanup(self) -> None:
        """Saves panel states into settings."""
        settings.geometry = str(self.saveGeometry().toBase64(), 'utf-8')
        settings.state = str(self.saveState().toBase64(), 'utf-8')
        settings.splitter1 = str(self.article_content_splitter.saveState().toBase64(), 'utf-8')
        settings.splitter2 = str(self.feed_rhs_splitter.saveState().toBase64(), 'utf-8')
        self.article_view.cleanup()
        self.feed_view.cleanup()


    def refresh_all(self) -> None:
        """Tells the feed manager to update all the feeds.

        Should only be called when the refresh all button is pressed.
        """
        self.feed_manager.refresh_all()



    def hideEvent(self, event: qtg.QHideEvent):
        self.hide()


    def update_icon(self):
        """Updates the tray icon for the application.

        Checks if there are any unread articles, and changes the tray icon accordingly.
        """
        # Icon designed by https://www.flaticon.com/authors/freepik from www.flaticon.com
        # check if there are any unread articles
        for node in self.feed_manager.feed_cache:
            if type(node) is Feed and not node.ignore_new and node.unread_count > 0:
                self.tray_icon.setIcon(qtg.QIcon("assets/new.png"))
                return

        self.tray_icon.setIcon(qtg.QIcon("assets/download.png"))


    def get_folder_unread_count(self, folder: Folder):
        """Returns the total number of unread articles of all feeds in a folder."""
        count = 0
        for node in folder:
            count += node.unread_count
        return count



    def tray_activated(self, reason: qtw.QSystemTrayIcon.ActivationReason):
        """Minimizes or maximizes the application to tray depending on if window is visible.

        Should only be called by an event."""
        if reason in (qtw.QSystemTrayIcon.Trigger, qtw.QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.show()
                # unminimize if minimized
                self.setWindowState(self.windowState() & ~qtc.Qt.WindowMinimized)
                self.activateWindow()


    def output_content(self, article: Article) -> None:
        """Outputs html content to the content view."""
        self.content_view.setHtml(article.content)


    def settings_dialog(self) -> None:
        """Opens a dialog that allows changing settings."""

        window = qut.QUiLoader().load("ui/settings.ui")

        window.globalRefresh.setValue(settings.refresh_time)
        window.globalRefreshDelay.setValue(settings.global_refresh_rate)
        window.deleteTime.setValue(settings.default_delete_time)
        window.fontSize.setValue(settings.font_size)
        window.startupUpdate.setChecked(settings.startup_update)

        window.setWindowFlags(qtc.Qt.WindowCloseButtonHint | qtc.Qt.WindowTitleHint)

        window.show()
        if window.exec() == qtw.QDialog.Accepted:

            if window.globalRefresh.value() != settings.refresh_time:
                self.feed_manager.set_default_refresh_rate(window.globalRefresh.value())

            if window.globalRefreshDelay.value() != settings.global_refresh_rate:
                settings.global_refresh_rate = window.globalRefreshDelay.value()

            if window.deleteTime.value() != settings.default_delete_time:
                settings.default_delete_time = window.deleteTime.value()

            if window.fontSize.value() != settings.font_size:
                settings.font_size = window.fontSize.value()
                self.article_view.update_all_data()
                self.feed_view.update_all_data()

            if window.startupUpdate.isChecked() != settings.startup_update:
                settings.startup_update = window.startupUpdate.isChecked()


class TBrowser(qtw.QTextBrowser):
    """HTML browser with resource fetching disabled."""

    def loadResource(self, type: int, name: str | qtc.QUrl):
        return None

    def __init__(self):
        super().__init__()
        self.zoomIn(2)
