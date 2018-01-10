import os
import numpy as np
import shelve
import sqlite3
from core.data.interfaces import IConcurrentJob, IProjectChangeNotify

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
        pass

    def set_store_dir(self, store_dir):
        self.store_dir = store_dir + "/"
        self.container_db = self.store_dir + "container"
        self.arbitrary_db = self.store_dir + "arbitrary"

    def asynch_store(self, id: int, data_dict, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        if data_type == STREAM_DATA_ARBITRARY:
            path = self.arbitrary_db
        else:
            path = self.container_db

        job = ASyncStoreJob([id, data_dict, path], proceed_slot)
        self.main_window.run_job_concurrent(job)

    def async_load(self, id: int, proceed_slot, data_type = STREAM_DATA_IPROJECT_CONTAINER):
        if data_type == STREAM_DATA_ARBITRARY:
            path = self.arbitrary_db
        else:
            path = self.container_db

        job = ASyncLoadJob([id, path], proceed_slot)
        self.main_window.run_job_concurrent(job)

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

    #region IProjectChangeNotify
    def on_loaded(self, project):
        self.project = project
        self.set_store_dir(self.project.data_dir)

    def on_changed(self, project, item):
        pass

    def on_selected(self, sender, selected):
        pass
    #endregion
    pass


class ASyncStoreJob(IConcurrentJob):
    def __init__(self, args, proceed_slot):
        super(ASyncStoreJob, self).__init__(args, show_modify_progress=False)
        self.proceed_slot = proceed_slot

    def run_concurrent(self, args, sign_progress):
        unique_id = args[0]
        obj = args[1]
        path = args[2]
        is_arbitrary = args[3]

        with shelve.open(path) as db:
            db[str(unique_id)] = obj

        return [True]

    def modify_project(self, project, result, sign_progress = None):
        if self.proceed_slot is not None:
            self.proceed_slot()


class ASyncLoadJob(IConcurrentJob):
    def __init__(self, args, proceed_slot):
        super(ASyncLoadJob, self).__init__(args, show_modify_progress=False)
        self.proceed_slot = proceed_slot

    def run_concurrent(self, args, sign_progress):
        unique_id = args[0]
        path = args[1]

        with shelve.open(path) as db:
            obj = db[str(unique_id)]

        return [obj]

    def modify_project(self, project, result, sign_progress=None):
        if self.proceed_slot is not None:
            self.proceed_slot(result[0])
#endregion
pass


class NumpyStreamer(ProjectStreamer):
    def __init__(self, main_window):
        super(NumpyStreamer, self).__init__(main_window)

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
