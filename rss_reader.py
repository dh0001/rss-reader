# packages
import logging

import PySide2.QtWidgets as qtw

# own modules
import feed_manager
import view


# initialization
app = qtw.QApplication([])

logging.basicConfig(filename="log.txt", filemode="a", format="%(asctime)s %(levelname)s:%(message)s")
feed_manager = feed_manager.FeedManager()
view = view.View(feed_manager)


try:
    # start program
    app.exec_()

    # cleanup
    feed_manager.cleanup()
    view.cleanup()

except BaseException as e:
    logging.exception("Exception thrown!, ", e)

app.quit()
logging.shutdown()
