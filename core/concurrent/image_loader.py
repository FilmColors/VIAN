from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from core.data.interfaces import *
from core.gui.ewidgetbase import *
from core.analysis.informative import select_rows
from core.data.computation import ms_to_frames
from core.container.project import *


class ClassificationObjectChangedJob(IConcurrentJob):
    def __init__(self, project:VIANProject, hdf5_manager, cl_obj, recompute=False, hdf5_cache = None):
        super(ClassificationObjectChangedJob, self).__init__(project)
        self.project = project
        self.hdf5_manager = hdf5_manager
        self.cl_obj = cl_obj
        self.hdf5_cache = hdf5_cache
        self.recompute = recompute

    def prepare(self, project):
        super(ClassificationObjectChangedJob, self).prepare(project)

    def run_concurrent(self, args, sign_progress):
        for scr in self.project.screenshots: #type: Screenshot
            scr.set_classification_object(clobj=self.cl_obj, recompute=self.recompute, hdf5_cache=self.hdf5_cache)
        return True

    def modify_project(self, project:VIANProject, result, sign_progress=None, main_window = None):
        super(ClassificationObjectChangedJob, self).modify_project(project, result, sign_progress, main_window)