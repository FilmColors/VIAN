import pkgutil
import sys
import os
import inspect
import importlib
import glob
from functools import partial
from PyQt5.QtWidgets import QMenu
from core.data.interfaces import IAnalysisJob
from core.data.plugin import GAPlugin


class ExtensionList:
    def __init__(self, main_window):
        self.analyses = []
        self.plugins = []
        self.import_paths = []
        self.main_window = main_window
        self.load_plugins()
        self.load_analysis()
        print("Loaded Analyses:", self.analyses)
        print("Loaded Plugins: ", self.plugins)

    def load_plugins(self):
        file_list = []
        print (os.path.abspath(os.path.curdir))
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
                print(e)
                continue

        # for f in glob.glob("extensions" + "/*/*"):
        #     if ".py" in f and (not "__init__" in f) and not ("extension_list" in f) and (not ".pyc" in f):
        #         p = f.replace(os.path.abspath(os.path.curdir), "")
        #         p = p.replace("\\", "/")
        #         files.append(p.replace("/", ".").replace(".py", ""))

    def load_analysis(self):
        file_list = []
        print (os.path.abspath(os.path.curdir))
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
                print(e)
                continue


    # def load_all_modules_from_dir(self):
    #     print("## Loading Plugins ##")
    #
    #     files = []
    #
    #     for f in glob.glob("extensions" + "/*/*"):
    #         if ".py" in f and (not "__init__" in f)and not ("extension_list" in f) and (not ".pyc" in f) :
    #             p = f.replace(os.path.abspath(os.path.curdir), "")
    #             p = p.replace("\\", "/")
    #             files.append(p.replace("/", ".").replace(".py", ""))
    #
    #
    #     modules = []
    #
    #     for f in files:
    #         try:
    #             my_module = importlib.import_module(f)
    #             modules.append(my_module)
    #
    #             for name, obj in inspect.getmembers(sys.modules[my_module.__name__]):
    #                 if inspect.isclass(obj) and issubclass(obj, IAnalysisJob):
    #                     if obj is not IAnalysisJob and obj is not ExtensionList:
    #                         self.analyses.append(obj(0))
    #
    #                 if inspect.isclass(obj) and issubclass(obj, GAPlugin):
    #                     if obj is not GAPlugin and obj is not ExtensionList:
    #                         self.plugins.append(obj(self.main_window))
    #         except:
    #             continue
    #
    #
    #     print("Loaded Analyses:", self.analyses)
    #     print("Loaded Plugins: ", self.plugins)

    def get_plugin_menu(self, parent):
        result = QMenu("Extensions", parent)
        result.setTitle("Plugins")

        for p in self.plugins:
            action = result.addAction(p.plugin_name)
            action.triggered.connect(partial(p.get_window, self.main_window))
        print("## Done ##")
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


