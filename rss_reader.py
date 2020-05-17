# packages
import sqlite3
import requests
import PySide2.QtWidgets as qtw
import logging


# own modules
import feed_manager
import view as view_class
import settings as settings_class


# initialization
app = qtw.QApplication([])

logging.basicConfig(filename="log.txt", filemode="a", format="%(asctime)s %(levelname)s:%(message)s")
settings = settings_class.Settings("settings.json")
feed_manager = feed_manager.FeedManager(settings)
view = view_class.View(feed_manager, settings)


try:
    # start program
    feed_manager.refresh_all()
    app.exec_()

    # cleanup
    feed_manager.cleanup()
    view.cleanup()
    settings.cleanup()
except:
    logging.exception("Exception thrown!")

app.quit()
logging.shutdown()