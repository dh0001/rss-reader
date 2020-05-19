import logging


logging.basicConfig(filename="log.txt", filemode="a", format="%(asctime)s %(levelname)s:%(message)s")
logging.error("abc")

try:
    raise Exception("abc")
except:
    logging.exception("Exception Thrown")
logging.shutdown()