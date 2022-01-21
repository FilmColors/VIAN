import pkgutil
import sys
import os
import inspect
import importlib
import glob
from functools import partial
from PyQt6.QtWidgets import QMenu
from vian.core.data.interfaces import IAnalysisJob
from vian.core.data.plugin import GAPlugin
from vian.core.data.log import log_warning, log_error, log_info, log_debug


class ExtensionList:
    def __init__(self, main_window):
        self.analyses = []
        self.plugins = []
        self.import_paths = []
        self.main_window = main_window
        self.load_plugins()
        self.load_analysis()
        self.load_pipelines("extensions/pipelines/")
        # self.load_pipelines(main_window.settings.DIR_SCRIPTS)

        log_info("\n")
        log_info("#### --- Extensions --- #####")
        if len(self.analyses) > 0:
            log_info("Loaded Analyses")
            for a in self.analyses:
                log_info(" --", a.__class__.__name__)
        if len(self.plugins) > 0:
            log_info("Loaded Plugins")
            for a in self.plugins:
                log_info(" --", a.__class__.__name__)
        log_info("\n")

    def load_plugins(self):
        file_list = []
        for root, dirs, files in os.walk("extensions/plugins/", topdown=False):
            for name in files:
                if ".py" in name and not "__init__.py" in name and not "__pycache__" in root:
                    path = os.path.join(root, name)
                    path = path.replace("\\", "/")
                    path = path.replace(".py", "")
                    path = path.replace("/", ".")

                    file_list.append(path)

        for f in file_list:
            try:

                my_module = importlib.import_module(f)

                for name, obj in inspect.getmembers(sys.modules[my_module.__name__]):
                    if inspect.isclass(obj) and issubclass(obj, GAPlugin):
                        if obj is not GAPlugin and obj is not ExtensionList:
                            self.plugins.append(obj(self.main_window))
            except Exception as e:
                continue

    def load_analysis(self):
        file_list = []
        for root, dirs, files in os.walk("extensions/analysis/", topdown=False):
            for name in files:
                if ".py" in name and not "__init__.py" in name and not "__pycache__" in name:
                    path = os.path.join(root, name)
                    path = path.replace("\\", "/")
                    path = path.replace(".py", "")
                    path = path.replace("/", ".")

                    file_list.append(path)

        for f in file_list:
            try:

                my_module = importlib.import_module(f)

                for name, obj in inspect.getmembers(sys.modules[my_module.__name__]):
                    if inspect.isclass(obj) and issubclass(obj, IAnalysisJob):
                        if obj is not IAnalysisJob and obj is not ExtensionList:
                            self.analyses.append(obj)
                            self.import_paths.append([name, f])

            except Exception as e:
                # print(e)
                continue

    def load_pipelines(self, ddir="extensions/pipelines/"):
        file_list = []
        # print (os.path.abspath(os.path.curdir))
        for root, dirs, files in os.walk(ddir, topdown=False):
            for name in files:
                if "py" in name:
                    path = os.path.join(root, name)
                    path = path.replace("\\", "/")
                    path = path.replace(".py", "")
                    path = path.replace("/", ".")
                    if not "__init__" in path and not "__pycache__" in path:
                        file_list.append(path)

        for f in file_list:
            try:
                importlib.import_module(f)
            except Exception as e:
                log_error("Exception in load_pipelines():" ,e)
                continue

    def get_plugin_menu(self, parent):

        result = QMenu("Extensions", parent)
        result.setTitle("Plugins")

        for p in self.plugins:
            action = result.addAction(p.plugin_name)
            action.triggered.connect(partial(p.get_window, self.main_window))
        return result

    def get_analysis_menu(self, parent, main_window):
        result = QMenu("Extensions", parent)
        result.setTitle("Extensions")
        for a in self.analyses:
            inst = a()
            action = result.addAction(inst.get_name())
            action.triggered.connect(partial(main_window.analysis_triggered, a()))

        return result

    def get_importables(self):
        return self.import_paths


