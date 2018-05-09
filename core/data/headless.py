from core.data.containers import *
from core.data.settings import UserSettings
from core.data.project_streaming import *

class HeadlessUserSettings():
    def __init__(self):
        self.PROJECT_FILE_EXTENSION = ".eext"

class HeadlessMainWindow(QObject):
    def __init__(self):
        super(HeadlessMainWindow, self).__init__()
        self.thread_pool = QThreadPool()
        self.numpy_data_manager = NumpyDataManager(self)
        self.project_streamer = ProjectStreamerShelve(self)


    def print_message(self, msg, color):
        print(msg)

    def dispatch_on_changed(self, receiver=None, item=None):
        pass

def load_project_headless(path) -> VIANProject:
    project = VIANProject(HeadlessMainWindow())
    project.inhibit_dispatch = True
    project.load_project(HeadlessUserSettings(), path)
    project.print_all()
    return project


if __name__ == '__main__':
    p = load_project_headless("C:/Users/Gaudenz Halter/Documents/VIAN/229_1_1_Jigokumon_1953_BF/229_1_1_Jigokumon_1953_BF.eext")

