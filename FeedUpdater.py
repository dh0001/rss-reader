
from feed import Feed, Folder, get_feed
import time
import threading
import datetime
import queue
import logging
from typing import List, Union
from PySide2 import QtCore as qtc
from sortedcontainers import SortedKeyList


class UpdateThread(qtc.QThread):
    data_downloaded_event = qtc.Signal(Feed, Feed, list)
    download_error_event = qtc.Signal()


    class Entry():
        """Entries in the scheduler.
        
        Holds a feed, and the time it should be refreshed.
        A value of `None` for feed indicates it the entry for global refresh."""
        __slots__ = 'scheduled', 'time'
        def __init__(self, scheduled: Union[Feed, None], time: int):
            self.scheduled = scheduled  # a value of None indicates global refresh
            self.time = time


    def __init__(self, feeds: Folder, settings):
        """
        Parameters
        ----------

        feeds
            a Folder containing all the feeds that will be in the scheduler.

        settings
            the settings for the application.
        """
        qtc.QThread.__init__(self)

        self.schedule = SortedKeyList(key=lambda x: x.time)
        self.schedule_update_event = threading.Event()
        self.feeds = feeds
        self.settings = settings
        self.schedule_lock = threading.Lock()
        self.queue = queue.SimpleQueue()

        for feed in self.feeds:
            if feed.refresh_rate != None:
                self.schedule.add(UpdateThread.Entry(feed, time.time() + feed.refresh_rate))

        # entry for global refresh
        self.schedule.add(UpdateThread.Entry(None, self.settings["refresh_time"] + time.time()))


    def run(self):
        while True:
            if self.isInterruptionRequested():
                return

            with self.schedule_lock:

                if self.schedule[0].time <= time.time():

                    if type(self.schedule[0].scheduled) is Feed:
                        feed = self.schedule[0].scheduled
                        self.queue.put(feed)
                        self.schedule.add(UpdateThread.Entry(feed, time.time() + feed.refresh_rate))
                    
                    else:
                        # global refresh
                        self.global_refresh_folder(self.feeds)
                        self.schedule.add(UpdateThread.Entry(None, self.settings["refresh_time"] + time.time()))
                    
                    del self.schedule[0]

            while not self.queue.empty():
                feed = self.queue.get_nowait()
                self.update_feed(feed)
                if self.isInterruptionRequested():
                    return

            self.schedule_update_event.wait(self.schedule[0].time - time.time())
            self.schedule_update_event.clear()

        
    def global_refresh_folder(self, folder):
        for node in folder:
            if type(node) is Folder:
                self.global_refresh_folder(node)
            else:
                if node.refresh_rate == None:
                    self.queue.put(node)


    def update_feed(self, feed: Feed):
        try:
            updated_feed, articles = get_feed(feed.uri, feed.template)
            self.data_downloaded_event.emit(feed, updated_feed, articles)
        except Exception:
            logging.error(f"Error parsing feed {feed.uri}")

        time.sleep(self.settings["global_refresh_rate"])


    def force_refresh_folder(self, folder):

        def folder_refresh(folder):
            for node in folder:
                if type(node) is Folder:
                    folder_refresh(node)
                else:
                    self.queue.put(node)

        folder_refresh(folder)
        self.schedule_update_event.set()


    def force_refresh_feed(self, feed):
        self.queue.put(feed)
        self.schedule_update_event.set()


    def global_refresh_time_updated(self):
        with self.schedule_lock:
            i = next((i for i,v in enumerate(self.schedule) if v.scheduled == None))
            del self.schedule[i]
            self.schedule.add(UpdateThread.Entry(None, self.settings["refresh_time"] + time.time()))
            self.schedule_update_event.set()


    def update_refresh_rate(self, feed: Feed, rate: Union[int, None]):

        with self.schedule_lock:
            if feed.refresh_rate != None:
                i = next((i for i,v in enumerate(self.schedule) if v.scheduled and v.scheduled.db_id == feed.db_id))
                del self.schedule[i]

            feed.refresh_rate = rate
            if rate != None:
                self.schedule.add(UpdateThread.Entry(feed, time.time() + feed.refresh_rate))

        self.schedule_update_event.set()
