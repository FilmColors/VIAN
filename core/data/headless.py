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
    """
    Loads a VIAN project without needing a VIAN instance running by emulating VIAN. 
    :param path: The path to the project to load
    :return: a loaded VIANProject or None if failed
    """
    try:
        project = VIANProject(HeadlessMainWindow())
        project.inhibit_dispatch = True
        project.load_project(HeadlessUserSettings(), path)
        project.print_all()
        return project
    except Exception as e:
        return None


def create_project_headless(name, location, movie_path, screenshots_paths, segmentation_path, is_eaf = False, move_movie="None") -> VIANProject:
    """
    Creates a VIANProject without the need of a MainWindow
    :param name: name of the project
    :param movie_path: path to the movie
    :param screenshots_paths: a list of path to all screenshots
    :param segmentation_path: the path to the segmentation
    :param is_eaf: if the segmentation is a .eaf project
    :param move_movie: how to handle the movie file "None", "move" or "copy"
    :return: a VIANProject created from the input or None if failed
    """
    try:
        project = VIANProject(HeadlessMainWindow(), name=name, folder=location, path=location + "/" + name)
        project.inhibit_dispatch = True
        project.movie_descriptor.set_movie_path(movie_path)
        project.create_file_structure()
        # Import Segmentation

        # Import Screenshots

        # Store the project
        #TODO
        return project
    except:
        return None

if __name__ == '__main__':
    p = load_project_headless("C:/Users/Gaudenz Halter/Documents/VIAN/229_1_1_Jigokumon_1953_BF/229_1_1_Jigokumon_1953_BF.eext")

