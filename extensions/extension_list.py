import pkgutil
import sys
import os
import inspect
import importlib
import glob
from PyQt5.QtWidgets import QMenu
from core.data.interfaces import IAnalysisJob
from core.data.plugin import GAPlugin


class ExtensionList:
    def __init__(self, main_window):
        self.analyses = []
        self.plugins = []
        self.main_window = main_window
        self.load_all_modules_from_dir()


    def load_all_modules_from_dir(self):
        print("## Loading Plugins ##")

        files = []

        for f in glob.glob("extensions" + "/*/*"):
            if ".py" in f and (not "__init__" in f)and not ("extension_list" in f) and (not ".pyc" in f):
                p = f.replace(os.path.abspath(os.path.curdir), "")
                p = p.replace("\\", "/")
                files.append(p.replace("/", ".").replace(".py", ""))


        modules = []

        for f in files:
            try:
                my_module = importlib.import_module(f)
                modules.append(my_module)

                for name, obj in inspect.getmembers(sys.modules[my_module.__name__]):
                    if inspect.isclass(obj) and issubclass(obj, IAnalysisJob):
                        if obj is not IAnalysisJob and obj is not ExtensionList:
                            self.analyses.append(obj(0))

                    if inspect.isclass(obj) and issubclass(obj, GAPlugin):
                        if obj is not GAPlugin and obj is not ExtensionList:
                            self.plugins.append(obj(self.main_window))
            except:
                continue


        print("Loaded Analyses:", self.analyses)
        print("Loaded Plugins: ", self.plugins)

    def get_plugin_menu(self, parent):
        result = QMenu("Extensions", parent)
        result.setTitle("Plugins")

        for p in self.plugins:
            action = result.addAction(p.plugin_name)
            action.triggered.connect(p.get_window)
        print("## Done ##")
        return result



