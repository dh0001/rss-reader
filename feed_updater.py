from __future__ import annotations
from heapq import heapify, heappop, heappush
import time
import threading
import queue
import logging
from typing import NamedTuple, Union


from PySide6 import QtCore as qtc

from feed import Feed, Folder, get_feed
from settings import Settings


class Entry(NamedTuple):
    time: float
    scheduled: Feed | None  # a value of None indicates global refresh

    def __lt__(self, other: Entry):
        return self.time <= other.time

# Entry = NamedTuple('Entry', ['scheduled', 'time'])


class UpdateThread(qtc.QThread):
    """Thread which fetches data for the feed manager on a schedule.

    Parameters
    ----------

    feeds
        a Folder containing all the feeds that will be in the scheduler.

    settings
        the settings for the application.
    """
    data_downloaded_event = qtc.Signal(Feed, Feed, list)
    download_error_event = qtc.Signal()


    def __init__(self, feeds: Folder, settings: Settings):
        qtc.QThread.__init__(self)

        self.schedule: list[Entry] = []
        self.schedule_update_event = threading.Event()
        self.feeds = feeds
        self.settings = settings
        self.schedule_lock = threading.Lock()
        self.queue: queue.SimpleQueue[Feed] = queue.SimpleQueue()

        for feed in self.feeds:
            if feed.refresh_rate is not None and feed.refresh_rate != 0:
                self.schedule.append(Entry(time.time() + feed.refresh_rate, feed))

        # entry for global refresh
        self.schedule.append(Entry(self.settings.refresh_time + time.time(), None))

        heapify(self.schedule)


    def run(self):
        while True:
            if self.isInterruptionRequested():
                return

            with self.schedule_lock:
                
                if self.schedule[0].time <= time.time():

                    if type(self.schedule[0].scheduled) is Feed:
                        heappop(self.schedule)
                        feed = self.schedule[0].scheduled
                        self.queue.put(feed)
                        if feed.refresh_rate is not None and feed.refresh_rate != 0:
                            heappush(self.schedule, Entry(feed.refresh_rate + time.time(), feed))

                    else:
                        # global refresh
                        self.queue_default_refresh(self.feeds)
                        if self.settings.refresh_time != 0:
                            heappush(self.schedule, Entry(self.settings.refresh_time + time.time(), None))

                    del self.schedule[0]

            while not self.queue.empty():
                feed = self.queue.get_nowait()
                self.update_feed(feed)
                if self.isInterruptionRequested():
                    return

            self.schedule_update_event.wait(self.schedule[0].time - time.time())
            self.schedule_update_event.clear()


    def queue_default_refresh(self, folder: Folder | Feed):
        """Adds all feeds which refresh at the default rate to the queue."""
        for node in folder:
            if type(node) is Folder:
                self.queue_default_refresh(node)
            else:
                if node.refresh_rate is None:
                    self.queue.put(node)


    def update_feed(self, feed: Feed):
        """Gets data for a feed in the queue.

        Emits data_downloaded_event when the data is retrieved, then sleeps the thread
        for the duration of the global_refresh_rate."""
        try:
            logging.debug(f"Fetching {feed.uri}")
            updated_feed, articles = get_feed(feed.uri, feed.analyzer)
            self.data_downloaded_event.emit(feed, updated_feed, articles)
        except Exception as exc:
            logging.error(f"Error parsing feed {feed.uri}, {exc}")

        time.sleep(self.settings.global_refresh_rate)


    def force_refresh_folder(self, folder: Folder):
        """Adds all feeds in a folder to the update queue recursively."""

        def folder_refresh(folder: Folder):
            for node in folder:
                if type(node) is Folder:
                    folder_refresh(node)
                else:
                    self.queue.put(node)

        folder_refresh(folder)
        self.schedule_update_event.set()


    def force_refresh_feed(self, feed: Feed):
        """Adds a feed to the update queue."""
        self.queue.put(feed)
        self.schedule_update_event.set()


    def update_global_refresh_rate(self, rate: int):
        """Updates the global refresh rate to the new value.

        Updates to the value should be changed using this function to avoid threading issues.
        """
        with self.schedule_lock:
            # delete the default refresh scheduler entry
            if self.settings.refresh_time != 0:
                i = next(i for (i, v) in enumerate(self.schedule) if v.scheduled is None)
                del self.schedule[i]

            self.settings.refresh_time = rate
            if self.settings.refresh_time != 0:
                heappush(self.schedule, Entry(self.settings.refresh_time + time.time(), None))

        self.schedule_update_event.set()


    def update_refresh_rate(self, feed: Feed, rate: Union[int, None]):
        """Updates the feed's refresh rate to the new value.

        Updates to the value should be changed using this function to avoid threading issues."""

        with self.schedule_lock:
            if feed.refresh_rate is not None and feed.refresh_rate != 0:
                i = next(i for (i, v) in enumerate(self.schedule) if v.scheduled is not None and v.scheduled.db_id == feed.db_id)
                del self.schedule[i]

            feed.refresh_rate = rate
            if feed.refresh_rate is not None and feed.refresh_rate != 0:
                heappush(self.schedule, Entry(time.time() + feed.refresh_rate, feed))

        self.schedule_update_event.set()


    def remove_feed(self, feed: Feed) -> None:
        """Removes an item from the refresh schedule."""
        i = next(i for (i, v) in enumerate(self.schedule) if v.scheduled is not None and v.scheduled.db_id == feed.db_id)
        del self.schedule[i]
        self.schedule_update_event.set()
