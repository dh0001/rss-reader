import logging
from PySide6.QtWidgets import QApplication

import feed_manager
import view


# initialization
app = QApplication([])

logging.basicConfig(filename="data/log.txt", filemode="a", format="%(asctime)s %(levelname)s:%(message)s")
feed_manager = feed_manager.FeedManager()
view = view.View(feed_manager)


try:
    # start program
    app.exec()

    # cleanup
    feed_manager.cleanup()
    view.cleanup()

except BaseException as e:
    logging.exception("Exception thrown!, ", e)

app.quit()
logging.shutdown()
