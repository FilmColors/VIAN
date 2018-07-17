import os
import numpy as np
import shelve
import glob
import sqlite3
from core.data.interfaces import IConcurrentJob, IProjectChangeNotify
from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot, QThread, Qt
import dataset as ds
from core.data.enums import DataSerialization
STREAM_DATA_IPROJECT_CONTAINER = 0
STREAM_DATA_ARBITRARY = 1
NUMPY_NO_OVERWRITE = 2
NUMPY_OVERWRITE = 3


class ProjectStreamer(IProjectChangeNotify, QObject):
    def __init__(self, main_window):
        QObject.__init__(self, main_window)
        IProjectChangeNotify.__init__(self)

        self.main_window = main_window
        self.project = None

    def asynch_store(self, id: int, data_dict, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        pass

    def async_load(self, id: int, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        pass

    def sync_store(self,  id: int, data_dict, data_type = STREAM_DATA_IPROJECT_CONTAINER):
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


class ProjectStreamerSignals(QObject):
    on_async_store = pyqtSignal(str, object, int, object, object)
    on_async_load = pyqtSignal(str, int, object, object)


#region ShelveProjectStreamer
class ProjectStreamerShelve(ProjectStreamer):
    def __init__(self, main_window):
        ProjectStreamer.__init__(self, main_window)
        self.stream_path = ""
        self.stream = None
        self.main_window = main_window
        self.thread_pool = main_window.thread_pool
        self.project = None

        self.store_dir = None
        self.container_db = None
        self.arbitrary_db = None
        self.signals = ProjectStreamerSignals()

        self.async_stream_worker = AsyncShelveStream()
        self.signals.on_async_store.connect(self.async_stream_worker.store)
        self.signals.on_async_load.connect(self.async_stream_worker.load)

        self.async_stream_thread = QThread()
        self.async_stream_worker.moveToThread(self.async_stream_thread)
        self.async_stream_thread.start()

    def set_store_dir(self, store_dir):
        self.store_dir = store_dir + "/"
        self.container_db = self.store_dir + "container"
        self.arbitrary_db = self.store_dir + "arbitrary"
        self.async_stream_worker.set_paths(self.container_db, self.arbitrary_db)

    def async_store(self, id: int, data_dict, data_type = STREAM_DATA_IPROJECT_CONTAINER, proceed_slot = None, proceed_slot_args = None):
        self.signals.on_async_store.emit(str(id), data_dict, data_type, proceed_slot, proceed_slot_args)

    def async_load(self, id: int, proceed_slot, proceed_slot_args = None, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        self.signals.on_async_load.emit(str(id), data_type, proceed_slot, proceed_slot_args)

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
            try:
                obj = db[str(id)]
            except Exception as e:
                print("Error in Streamer.sync_load()", str(e))
                self.main_window.print_message("Error in Streamer: " + str(e), "Orange")
                self.main_window.print_message("If you have just loaded the Project please wait some seconds and try again", "Orange")
                return None

        return obj

    def clean_up(self):
        try:
            os.remove(self.container_db)
            os.remove(self.arbitrary_db)
        except Exception as e:
            print("Exception in ProjectStreamerShelve.clean_up()", str(e))

    #region IProjectChangeNotify
    def on_loaded(self, project):
        if self.project is not None:
            self.clean_up()

        self.project = project

        if self.project is not None:
            self.set_store_dir(self.project.data_dir)

    def on_changed(self, project, item):
        pass

    def on_selected(self, sender, selected):
        pass

    def on_closed(self):
        try:
            files = glob.glob(self.arbitrary_db + ".*")
            files.extend(glob.glob(self.container_db + ".*"))
            for f in files:
                try:
                    os.remove(f)
                except Exception as e:
                    print(e)
        except:
            pass
    #endregion
    pass


class AsyncShelveStreamSignals(QObject):
    finished = pyqtSignal(object, object)


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

    @pyqtSlot(str, object, int, object, object)
    def store(self, unique_id, obj, data_type, slot = None, slot_arguments = None):
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
                self.signals.finished.emit(slot_arguments, None)

        except Exception as e:
            print("Exception in AsyncShelveStream.store()", str(e))
            try:
                self.signals.finished.disconnect()
            except Exception as e:
                print("Exception during Exception handling in AsyncShelveStream.store()", str(e))

    @pyqtSlot(str, int, object, object)
    def load(self, unique_id, data_type, slot, slot_arguments):
        try:
            self.signals.finished.connect(slot)

            if data_type == STREAM_DATA_ARBITRARY:
                path = self.arbitrary_db
            else:
                path = self.container_db

            with shelve.open(path) as db:
                obj = db[unique_id]

            self.signals.finished.emit(obj, slot_arguments)
            self.signals.finished.disconnect(slot)

        except Exception as e:
            print("Exception in AsyncShelveStream.load()", str(e))
            try:
                self.signals.finished.disconnect()
            except Exception as e:
                print("Exception during Exception Handling in AsyncShelveStream.load()", str(e))

    @pyqtSlot()
    def run(self):
        pass

#endregion

SQ_TABLE_JSON = "TABLE_ANALYSIS_JSON"
SQ_TABLE_MASKS = "TABLE_ANALYSIS_MASKS"

class SQLiteStreamer(ProjectStreamer):
    def __init__(self, main_window):
        super(SQLiteStreamer, self).__init__(main_window)
        self.signals = ProjectStreamerSignals()
        self.store_dir = ""
        self.store_path = ""
        self.db = None

    def set_store_dir(self, store_dir):
        self.store_dir = store_dir + "/"

    def async_store(self, id: int, data_dict, data_type =  DataSerialization.JSON, proceed_slot = None, proceed_slot_args = None):
        self.sync_store(id, data_dict, data_type)
        proceed_slot(proceed_slot_args)

    def async_load(self, id: int, proceed_slot, proceed_slot_args = None, data_type =  DataSerialization.JSON):
        self.signals.on_async_load.emit(str(id), data_type, proceed_slot, proceed_slot_args)

    def sync_store(self,  id: int, obj,data_type =  DataSerialization.JSON):
        if self.db is not None:
            try:
                self.db.begin()

                if data_type == DataSerialization.MASKS:
                    table = SQ_TABLE_MASKS
                else:
                    table = SQ_TABLE_JSON

                if self.db[table].find_one(key=id) == None:
                    self.db[table].insert(dict(key=id, json=obj))
                else:
                    self.db[table].update(dict(key=id, json=obj), ['key'])

                self.db.commit()
            except Exception as e:
                print("SQLite Exception", str(e))
                self.db.rollback()

    def bulk_store(self, ids, objs, data_types):
        if self.db is not None:
            try:
                self.db.begin()

                for i in range(len(ids)):
                    if data_types[i] == DataSerialization.MASKS:
                        table = SQ_TABLE_MASKS
                    else:
                        table = SQ_TABLE_JSON

                    if self.db[table].find_one(key=id) == None:
                        self.db[table].insert(dict(key=id, json=objs[i]))
                    else:
                        self.db[table].update(dict(key=id, json=objs[i]), ['key'])

                self.db.commit()
            except Exception as e:
                print("SQLite Exception", str(e))
                self.db.rollback()

    def sync_load(self, id: int, data_type = DataSerialization.JSON):
        if self.db is not None:
            if data_type == DataSerialization.MASKS:
                table = SQ_TABLE_MASKS
            else:
                table = SQ_TABLE_JSON
            try:
                ret = self.db[table].find_one(key=id)
                return dict(ret)['json']
            except Exception as e:
                print("SQLite Exception", str(e))
        else:
            return None

    def clean_up(self):
        if self.project is not None and self.db is not None:
            project_all = self.project.get_all_ids()
            for t in [SQ_TABLE_JSON]:
                all = t.all()
                for t in all:
                    if t['key'] not in project_all:
                        print("Not Found")
                    else:
                        print("Found")

    #region IProjectChangeNotify
    def on_loaded(self, project):
        self.clean_up()
        self.store_path = "sqlite:///" + project.data_dir + "/" + "database.sqlite"
        print("SQLite Database Path:", self.store_path)
        self.db = ds.connect(self.store_path)
        pass

    def on_changed(self, project, item):
        pass

    def on_selected(self, sender, selected):
        pass

    def on_closed(self):
        pass
    #endregion


class NumpyDataManager(ProjectStreamer):
    def __init__(self, main_window):
        super(NumpyDataManager, self).__init__(main_window)

    def dump(self, key, data_dict, data_type):
        temp_indic = "_temp"
        temp_file_path = self.project.data_dir + "/" +str(key) + temp_indic +".npz"
        dest_file_path = self.project.data_dir + "/" + str(key) + ".npz"

        if data_dict is None:
            return

        if data_type == NUMPY_NO_OVERWRITE and os.path.isfile(dest_file_path):
            return

        try:
            # Save the new data in a temporary file
            with open(temp_file_path, "wb") as f:
                np.savez(f, **data_dict)

            # If this key alreay exists, remove it
            if os.path.isfile(dest_file_path):
                os.remove(dest_file_path)

            # Rename the temporary file to the correct key
            try:
                os.rename(temp_file_path, dest_file_path)
            except Exception as e:
                print("Error in NumpyDataManager.dump.rename(): ", str(e))

        except Exception as e:
            print("Error in NumpyDataManager.dump: ", str(e))

    def load(self, key, data_type):
        try:
            with open(self.project.data_dir + "/" + str(key) + ".npz", "rb") as f:
                res = dict(np.load(f).items())

            return res
        except Exception as e:
            print("Tried to load ", key, "from ", self.project.data_dir + "/" + str(key) + ".npz")
            print(e)
            return None

    def remove_item(self, unique_id):
        if os.path.isfile(self.project.data_dir + "/" + str(unique_id) + ".npz"):
            try:
                os.remove(self.project.data_dir + "/" + str(unique_id) + ".npz")
            except Exception as e:
                print("Error in NumpyDataManager.remove_item:", str(e))

    def clean_up(self, ids):
        if self.project is not None:
            try:
                ids = [str(id) for id in ids]
                files = glob.glob(self.project.data_dir + "/*.npz*")
                file_names = [f.replace("\\", "/").split("/").pop().split(".")[0] for f in files]
                for i, n in enumerate(file_names):
                    if n not in ids:
                        try:
                            os.remove(files[i])
                            print("Cleanup: ", files[i])
                        except Exception as e:
                            print(str(e))
            except Exception as e:
                print("Error in NumpyDataManager.CleanUp:", str(e))
                pass

    #endregion
    pass


class IStreamableContainer():
    """
    Without overriding the functions, this may only be used together with a class that has 
    an attribute "project" of type containers.ELANExtensionProject
    """
    def apply_loaded(self, obj):
        pass

    @pyqtSlot(object, object)
    def on_data_loaded(self, obj, args):
        self.apply_loaded(obj)

        # Perform a Callback if handed into Load Container
        # Either with argumens or without
        if len(args) > 1 and args[1] is not None:
            args[0](args[1])
        else:
            args[0]()

    def load_container(self, callback=None, args = None, sync = False):
        if not sync:
            self.project.main_window.project_streamer.async_load(id=self.unique_id,
                                                                 proceed_slot=self.on_data_loaded,
                                                                 proceed_slot_args=[callback, args],
                                                                 data_type=STREAM_DATA_IPROJECT_CONTAINER)
        else:
            obj = self.project.main_window.project_streamer.sync_load(id=self.unique_id,
                                                                 data_type=STREAM_DATA_IPROJECT_CONTAINER)
            if obj is None:
                print("Shelve Loading Failed, try Numpy")
                obj = self.project.main_window.numpy_data_manager.load(self.unique_id, STREAM_DATA_IPROJECT_CONTAINER)
                if obj is not None:
                    print("Success")
                else:
                    print("Failed")


            if obj is not None:
                self.on_data_loaded(obj, [callback, args])

    def unload_container(self, data = None, sync = False):
        if sync:
            self.project.main_window.project_streamer.sync_store(self.unique_id, data)
        else:
            self.project.main_window.project_streamer.async_store(self.unique_id, data)



