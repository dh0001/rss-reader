
import feed as feedutility
import time
import threading
import settings
import datetime
import queue
from typing import List, Union
from PySide2 import QtCore as qtc
from sortedcontainers import SortedKeyList
from feed_manager import FeedManager


class UpdateThread(qtc.QThread):
    data_downloaded_event = qtc.Signal(feedutility.CompleteFeed, object)
    scheduled_default_refresh_event = qtc.Signal()
    download_error_event = qtc.Signal()

    class Entry():
        """
        Small class holding a feed, and its entry in the scheduler.
        """
        __slots__ = 'scheduled', 'time'
        def __init__(self, scheduled: Union[feedutility.Feed, None], time: float):
            self.scheduled = scheduled
            self.time = time


    def __init__(self, feed_manager):
        qtc.QThread.__init__(self)

        self.schedule = SortedKeyList(key=lambda x: x.time)
        self.schedule_update_event = threading.Event()
        self.feed_manager = feed_manager
        self.schedule_lock = threading.Lock()
        self.queue = queue.SimpleQueue()

        for feed in self.feed_manager.feed_cache:
            if feed.refresh_rate != None:
                self.schedule.add(UpdateThread.Entry(feed, time.time() + feed.refresh_rate))

        # entry for global refresh
        self.schedule.add(UpdateThread.Entry(None, self.feed_manager._settings.settings["refresh_time"] + time.time()))


    def run(self):

        while True:
            if self.isInterruptionRequested():
                return

            with self.schedule_lock:

                if self.schedule[0].time <= time.time():

                    if type(self.schedule[0].scheduled) is feedutility.Feed:
                        feed = self.schedule[0].scheduled
                        self.queue.put(feed)
                        self.schedule.add(UpdateThread.Entry(feed, time.time() + feed.refresh_rate))
                    
                    else:
                        # global refresh
                        self.global_refresh_folder(self.feed_manager.feed_cache)
                        self.schedule.add(UpdateThread.Entry(None, self.feed_manager._settings.settings["refresh_time"] + time.time()))
                    
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
            if type(node) is feedutility.Folder:
                self.global_refresh_folder(node)
            else:
                if node.refresh_rate == None:
                    self.queue.put(node)


    def update_feed(self, feed: feedutility.Feed):
        try:
            completefeed = feedutility.get_feed(feed.uri, feed.template)
            self.data_downloaded_event.emit(feed, completefeed)
        except Exception:
            print("Error parsing feed", feed.uri)

        time.sleep(self.feed_manager._settings.settings["global_refresh_rate"])


    def force_refresh_folder(self, folder):
        self.force_refresh_folder_noset(folder)
        self.schedule_update_event.set()


    def force_refresh_folder_noset(self, folder):
        for node in folder:
            if type(node) is feedutility.Folder:
                self.force_refresh_folder_noset(node)
            else:
                self.queue.put(node)


    def force_refresh_feed(self, feed):
        self.queue.put(feed)
        self.schedule_update_event.set()


    def global_refresh_time_updated(self):
        with self.schedule_lock:
            i = next((i for i,v in enumerate(self.schedule) if v.scheduled == None))
            del self.schedule[i]
            self.schedule.add(UpdateThread.Entry(None, self.feed_manager._settings.settings["refresh_time"] + time.time()))
            self.schedule_update_event.set()


    def update_refresh_rate(self, feed, rate):

        with self.schedule_lock:
            if feed.refresh_rate != None:
                i = next((i for i,v in enumerate(self.schedule) if v.scheduled and v.scheduled.db_id == feed.db_id))
                del self.schedule[i]

            feed.refresh_rate = rate
            if rate != None:
                self.schedule.add(UpdateThread.Entry(feed, time.time() + feed.refresh_rate))

        self.schedule_update_event.set()
