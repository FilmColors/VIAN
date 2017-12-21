import os
import shelve

from core.data.interfaces import IConcurrentJob, IProjectChangeNotify


class ProjectStreamer(IProjectChangeNotify):
    def __init__(self):
        super(ProjectStreamer, self).__init__()
        self.project = None

        self.store_dir = None
        pass

    def set_store_dir(self, store_dir):
        self.store_dir = store_dir

    def sync_store(self,  id: int, obj):
        print(self.store_dir)
        with shelve.open(self.store_dir + str(id)) as db:
            db[str(id)] = obj
            keys = list(db.keys())
            print(keys)


    def sync_load(self, id: int):
        print(self.store_dir)
        with shelve.open(self.store_dir + str(id)) as db:
            keys = list(db.keys())
            print(keys)
            obj = db[str(id)]
        return obj

    #region IProjectChangeNotify
    def on_loaded(self, project):
        self.project = project
        self.store_dir = project.data_dir + "/"

    def on_changed(self, project, item):
        pass

    def on_selected(self, sender, selected):
        pass
    #endregion
    pass


