# packages
import sqlite3
import requests
import PySide2.QtWidgets as qtw
import logging


# own modules
import feed_manager
import view
import settings


# initialization
app = qtw.QApplication([])

logging.basicConfig(filename="log.txt", filemode="a", format="%(asctime)s %(levelname)s:%(message)s")
settings.init_settings()
feed_manager = feed_manager.FeedManager(settings.settings)
view = view.View(feed_manager)


try:
    # start program
    feed_manager.refresh_all()
    app.exec_()

    # cleanup
    feed_manager.cleanup()
    view.cleanup()
    settings.save_settings()
except:
    logging.exception("Exception thrown!")

app.quit()
logging.shutdown()