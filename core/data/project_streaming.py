import os
import numpy as np
import shelve
import sqlite3
from core.data.interfaces import IConcurrentJob, IProjectChangeNotify
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QThread

STREAM_DATA_IPROJECT_CONTAINER = 0
STREAM_DATA_ARBITRARY = 1


class ProjectStreamer(IProjectChangeNotify):
    def __init__(self, main_window):
        super(ProjectStreamer, self).__init__()
        self.main_window = main_window
        self.project = None

    def asynch_store(self, id: int, data_dict, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        pass

    def async_load(self, id: int, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        pass

    def sync_store(self,  id: int, data_dict,data_type = STREAM_DATA_IPROJECT_CONTAINER):
        self.dump(id, data_dict, data_type)

    def sync_load(self, id: int, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        return self.load(id, data_type)

    def dump(self, key, data_dict, data_type):
        pass

    def load(self, key, data_type):
        pass

    #region IProjectChangeNotify
    def on_loaded(self, project):
        self.project = project

    def on_changed(self, project, item):
        pass

    def on_selected(self, sender, selected):
        pass

    #endregion
    pass


class ProjectStreamerSingals(QObject):
    on_async_store = pyqtSignal(int, object, int, object)
    on_async_load = pyqtSignal(int, int, object)


#region ShelveProjectStreamer
class ProjectStreamerShelve(ProjectStreamer):
    def __init__(self, main_window):
        super(ProjectStreamer, self).__init__()
        self.stream_path = ""
        self.stream = None
        self.main_window = main_window
        self.thread_pool = main_window.thread_pool
        self.project = None

        self.store_dir = None
        self.container_db = None
        self.arbitrary_db = None
        self.signals = ProjectStreamerSingals()

        self.async_stream_worker = AsyncShelveStream()
        self.signals.on_async_store.connect(self.async_stream_worker.store)
        self.signals.on_async_load.connect(self.async_stream_worker.load)

        self.async_stream_thread = QThread()
        self.async_stream_worker.moveToThread(self.async_stream_thread)

    def set_store_dir(self, store_dir):
        self.store_dir = store_dir + "/"
        self.container_db = self.store_dir + "container"
        self.arbitrary_db = self.store_dir + "arbitrary"

        self.async_stream_worker.set_paths(self.container_db, self.arbitrary_db)

    def async_store(self, id: int, data_dict, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        self.on_async_store.emit(id, data_dict, data_type, proceed_slot)

    def async_load(self, id: int, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        self.on_async_store.emit(id, data_type, proceed_slot)

    def sync_store(self,  id: int, obj,data_type = STREAM_DATA_IPROJECT_CONTAINER):
        if data_type == STREAM_DATA_ARBITRARY:
            path = self.arbitrary_db
        else:
            path = self.container_db

        with shelve.open(path) as db:
            db[str(id)] = obj

    def sync_load(self, id: int, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        if data_type == STREAM_DATA_ARBITRARY:
            path = self.arbitrary_db
        else:
            path = self.container_db
        with shelve.open(path) as db:
            obj = db[str(id)]

        return obj

    def clean_up(self):
        try:
            os.remove(self.container_db)
            os.remove(self.arbitrary_db)
        except Exception as e:
            print(e)


    #region IProjectChangeNotify
    def on_loaded(self, project):
        self.clean_up()
        self.project = project
        self.set_store_dir(self.project.data_dir)

    def on_changed(self, project, item):
        pass

    def on_selected(self, sender, selected):
        pass
    #endregion
    pass


class AsyncShelveStreamSignals(QObject):
    finished = pyqtSignal(object)


class AsyncShelveStream(QObject):
    def __init__(self):
        super(AsyncShelveStream, self).__init__()
        self.container_db = ""
        self.arbitrary_db = ""

        self.signals = AsyncShelveStreamSignals()

    @pyqtSlot(str, str)
    def set_paths(self, container_db, arbitrary_db):
        self.container_db = container_db
        self.arbitrary_db = arbitrary_db

    @pyqtSlot(int, object, int, object)
    def store(self, unique_id, obj, data_type, slot = None):
        try:
            if slot is not None:
                self.signals.finished.connect(slot)

            if data_type == STREAM_DATA_ARBITRARY:
                path = self.arbitrary_db
            else:
                path = self.container_db

            with shelve.open(path) as db:
                db[str(unique_id)] = obj

            if slot is not None:
                self.signals.finished.emit()
                self.signals.finished.disconnect()
        except Exception as e:
            print(e)

    @pyqtSlot(int, int, object)
    def load(self, unique_id, data_type, slot):
        try:
            self.signals.finished.connect(slot)
            if data_type == STREAM_DATA_ARBITRARY:
                path = self.arbitrary_db
            else:
                path = self.container_db

            with shelve.open(path) as db:
                obj = db[str(unique_id)]

            self.signals.finished.emit(obj)
            self.signals.finished.disconnect()
        except Exception as e:
            print(e)

        finally:
            self.signals.finished.emit(None)
            self.signals.finished.disconnect()

#endregion


class NumpyDataManager(ProjectStreamer):
    def __init__(self, main_window):
        super(NumpyDataManager, self).__init__(main_window)

    def dump(self, key, data_dict, data_type):
        np.savez(self.project.data_dir + "/" +str(key) + ".npz", **data_dict)

    def load(self, key, data_type):
        try:
            res =np.load(self.project.data_dir + "/" + str(key) + ".npz")
            print(res)
            return res
        except:
            print("Tried to load ", key, "from ", self.project.data_dir + "/" + str(key) + ".npy")
            return None

    #endregion
    pass
