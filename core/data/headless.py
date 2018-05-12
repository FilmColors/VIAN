from core.data.containers import *
from core.data.settings import UserSettings
from core.data.project_streaming import *

class HeadlessUserSettings():
    def __init__(self):
        self.PROJECT_FILE_EXTENSION = ".eext"
        self.SCREENSHOTS_STATIC_SAVE = False


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


def create_project_headless(name, location, movie_path, screenshots_frame_pos = None, segmentations = None, move_movie="None") -> VIANProject:
    """
    Creates a VIANProject without the need of a MainWindow
    :param name: name of the project
    :param movie_path: path to the movie
    :param screenshots_frame_pos: a list of frame positions for the screenshots
    :param segmentations: a list of lists [name, [segments]], each containing [start_ms, end_ms, body]
    :param is_eaf: if the segmentation is a .eaf project
    :param move_movie: how to handle the movie file "None", "move" or "copy"
    :return: a VIANProject created from the input or None if failed
    """
    try:
        project = VIANProject(HeadlessMainWindow(), name=name, folder=location, path=location + "/" + name)
        project.inhibit_dispatch = True
        project.movie_descriptor.set_movie_path(movie_path)

        os.mkdir(project.folder)
        project.create_file_structure()
        # Import Segmentation
        if segmentations is not None:
            for s in segmentations:
                segmentat = project.create_segmentation(s[0])
                for segm in s[1]:
                    segmentat.create_segment2(segm[0], segm[1], body = segm[2])
        # Import Screenshots
        if screenshots_frame_pos is not None:
            for i, s in enumerate(screenshots_frame_pos):
                project.create_screenshot("Screenshot_" + str(i).zfill(3), frame_pos=s)

        # Store the project
        #TODO
        project.store_project(HeadlessUserSettings(), project.path)
        return project
    except Exception as e:
        raise e
        return None

if __name__ == '__main__':
    # p = load_project_headless("C:/Users/Gaudenz Halter/Documents/VIAN/229_1_1_Jigokumon_1953_BF/229_1_1_Jigokumon_1953_BF.eext")
    segmentations = [["Main", [
        [0, 1000, "Hello"],
        [1001, 5000, "World"]]]]
    screenshots = [300, 500, 800]
    p = create_project_headless("TestHeadlessCreation", "C:/Users/Gaudenz/Documents/VIAN/TestHeadlessCreation/",
                                "C:/Users/Gaudenz/Documents/VIAN/229_1_1_Jigokumon_1953_DVD.mov",
                                screenshots, segmentations)
