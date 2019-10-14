import feed as feedutility
import feed_manager
import settings
from FeedView import FeedView, VerifyDialog
from ArticleView import ArticleView

import PySide2.QtWidgets as qtw
import PySide2.QtCore as qtc
import PySide2.QtGui as qtg

from typing import List, Union
import json


class View(qtw.QMainWindow):
    """
    Handles all interaction with the user.
    """

    def __init__(self, mgr: feed_manager.FeedManager, settings: settings.Settings):

        super().__init__()

        self.feed_manager = mgr
        self.settings_manager = settings

        self.article_view = ArticleView(self.feed_manager)
        self.feed_view = FeedView(self.feed_manager)
        self.content_view = TBrowser()
        self.splitter1 = qtw.QSplitter(qtc.Qt.Vertical)
        self.splitter2 = qtw.QSplitter(qtc.Qt.Horizontal)
        self.tray_icon = qtw.QSystemTrayIcon()

        self.gui()


    def cleanup(self) -> None:
        """
        Saves panel states into settings.
        """
        self.settings_manager.settings["geometry"] = str(self.saveGeometry().toBase64(), 'utf-8')
        self.settings_manager.settings["splitter1"] = str(self.splitter1.saveState().toBase64(), 'utf-8')
        self.settings_manager.settings["splitter2"] = str(self.splitter2.saveState().toBase64(), 'utf-8')
        self.settings_manager.settings["article_view_headers"] = str(self.article_view.header().saveState().toBase64(), 'utf-8')
        self.settings_manager.settings["feed_view_headers"] = str(self.feed_view.header().saveState().toBase64(), 'utf-8')


    def gui(self) -> None:
        """
        Starts the GUI. Initializes the window, views, and sets up interactions.
        """

        self.setWindowTitle('RSS Reader')
        # self.main_window.resize(800, 600)

        main_widget = qtw.QWidget()   
        self.setCentralWidget(main_widget)

        self.content_view.setOpenExternalLinks(True)

        self.splitter1.addWidget(self.article_view)
        self.splitter1.addWidget(self.content_view)
        self.splitter2.addWidget(self.feed_view)
        self.splitter2.addWidget(self.splitter1)
        # self.splitter1.setSizes([200, 300])
        # self.splitter2.setSizes([200, 500])

        hbox = qtw.QHBoxLayout(main_widget)
        hbox.addWidget(self.splitter2)
        main_widget.setLayout(hbox)

        menu_bar = self.menuBar().addMenu('Options')
        menu_bar.addAction("Add feed...").triggered.connect(self.feed_view.prompt_add_feed)
        menu_bar.addAction("Add folder...").triggered.connect(self.feed_view.prompt_add_folder)
        menu_bar.addAction("Update All Feeds").triggered.connect(self.refresh_all)
        menu_bar.addAction("Set Global Update Rate").triggered.connect(self.prompt_set_refresh_rate)
        menu_bar.addSeparator()
        menu_bar.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)

        # Designed by https://www.flaticon.com/authors/freepik from www.flaticon.com
        self.update_icon()
        tray_menu = qtw.QMenu()
        tray_menu.addAction("Update All Feeds").triggered.connect(self.refresh_all)
        tray_menu.addAction("Set Global Update Rate").triggered.connect(self.prompt_set_refresh_rate)
        tray_menu.addSeparator()
        tray_menu.addAction("Exit").triggered.connect(qtc.QCoreApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.restoreGeometry(qtc.QByteArray.fromBase64(bytes(self.settings_manager.settings["geometry"], "utf-8")))
        self.splitter1.restoreState(qtc.QByteArray.fromBase64(bytes(self.settings_manager.settings["splitter1"], "utf-8")))
        self.splitter2.restoreState(qtc.QByteArray.fromBase64(bytes(self.settings_manager.settings["splitter2"], "utf-8")))
        self.feed_view.header().restoreState(qtc.QByteArray.fromBase64(bytes(self.settings_manager.settings["feed_view_headers"], "utf-8")))
        self.article_view.header().restoreState(qtc.QByteArray.fromBase64(bytes(self.settings_manager.settings["article_view_headers"], "utf-8")))
        
        self.feed_view.header().setSectionResizeMode(qtw.QHeaderView.Interactive)
        self.feed_view.feed_selected_event.connect(self.article_view.select_feed)
        self.article_view.article_content_event.connect(self.output_content)
        self.tray_icon.activated.connect(self.tray_activated)
        self.feed_manager.feeds_updated_event.connect(self.update_icon)

        self.show()

    def refresh_all(self) -> None:
        """
        Called when the refresh all button is pressed. Tells the feed manager to update all the feeds.
        """
        self.feed_manager.refresh_all()

    
    def hideEvent(self, event):
        self.hide()


    def update_icon(self):
        if self.get_folder_unread_count(self.feed_view.feeds_cache) > 0:
            self.tray_icon.setIcon(qtg.QIcon("new.png"))
        else:
            self.tray_icon.setIcon(qtg.QIcon("download.png"))


    def get_folder_unread_count(self, folder):
        count = 0
        for node in folder:
            if type(node) is feedutility.Feed:
                count += node.unread_count
            else:
                count += self.get_folder_unread_count(node)
        return count



    def tray_activated(self, reason):
        if reason == qtw.QSystemTrayIcon.Trigger or reason == qtw.QSystemTrayIcon.DoubleClick:
            self.show()
            self.setWindowState(self.windowState() & ~qtc.Qt.WindowMinimized)
            self.activateWindow()
        

    def output_content(self, content) -> None:
        """
        Gets highlighted article in article_display, then outputs the content into content_display.
        """
        self.content_view.setHtml(content)


    def prompt_set_refresh_rate(self) -> None:
        """
        Opens a dialog which allows the user to set the global refresh rate.
        """
        dialog = VerifyDialog(lambda x: x.isdigit() and int(x) > 0, "Refresh Rate (seconds):", "Set Global Refresh Rate", str(self.settings_manager.settings["refresh_time"]))
        if (dialog.exec_() == qtw.QDialog.Accepted):
            response = int(dialog.get_response())
            self.feed_manager.set_default_refresh_rate(response)




class TBrowser(qtw.QTextBrowser):
    def loadResource(self, type: int, url: str):
        return None

    def __init__(self):
        super().__init__()
        self.zoomIn(2)