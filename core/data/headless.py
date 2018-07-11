"""
This Module enables a headless opening and closing of VIANProjects, 
this it can be used to perform operations in a batch process without having the gui enabled. 

"""

from core.container.project import *
from core.data.settings import UserSettings
from core.data.project_streaming import *
from core.gui.main_window import VERSION
from shutil import copy2, move
from core.gui.main_window import *

class HeadlessUserSettings():
    def __init__(self):
        self.PROJECT_FILE_EXTENSION = ".eext"
        self.SCREENSHOTS_STATIC_SAVE = False


class HeadlessMainWindow(QObject):
    def __init__(self):
        super(HeadlessMainWindow, self).__init__()
        self.thread_pool = QThreadPool()
        self.numpy_data_manager = NumpyDataManager(self)
        self.project_streamer = SQLiteStreamer(self)
        self.version = VERSION
        self.project = None


    def print_message(self, msg, color):
        print(msg)

    def dispatch_on_changed(self, receiver=None, item=None):
        pass

    def dispatch_on_loaded(self, *args):
        if self.project is not None:
            self.project_streamer.on_loaded(self.project)
            self.numpy_data_manager.on_loaded(self.project)

    def dispatch_on_closed(self, *args):
        pass

    def eval_class(self, name):
        return eval(name)


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


def create_project_headless(name, location, movie_path, screenshots_frame_pos = None, segmentations = None, move_movie="None", template_path = "") -> VIANProject:
    """
    Creates a VIANProject without the need of a MainWindow
    :param name: name of the project
    :param movie_path: path to the movie
    :param screenshots_frame_pos: a list of frame positions for the screenshots
    :param segmentations: a list of lists [name, [segments]], each containing [start_ms, end_ms, body]
    :param move_movie: how to handle the movie file "None", "move" or "copy"
    :return: a VIANProject created from the input or None if failed
    """
    try:
        if not os.path.isfile(movie_path):
            print("Movie Not found: ", movie_path)
            return

        mw = HeadlessMainWindow()
        project = VIANProject(mw, name=name, folder=location, path=location + "/" + name)
        mw.project = project
        project.inhibit_dispatch = False

        os.mkdir(project.folder)
        project.create_file_structure()

        # Move the Movie if set
        if move_movie == "copy":
            new_path = project.folder + "/" + os.path.split(movie_path)[1]
            copy2(movie_path, new_path)
            movie_path = new_path
        elif move_movie == "move":
            new_path = project.folder + "/" + os.path.split(movie_path)
            move(movie_path, new_path)
            movie_path = new_path

        project.movie_descriptor.set_movie_path(movie_path)

        # Apply Template if set
        if template_path is not None:
            project.apply_template(template_path)

        mw.dispatch_on_loaded()

        # Import Segmentation
        if segmentations is not None:
            for s in segmentations:
                print(s)

                segmentat = None
                # Check if there already exists a segmentation with this name
                for segm in project.segmentation:
                    if segm.get_name() == s[0]:
                        segmentat = s
                        break
                # if not create a new Segentation
                if segmentat is None:
                    segmentat = project.create_segmentation(s[0])

                for segm in s[1]:
                    segmentat.create_segment2(segm[0], segm[1], body = segm[2])

        # Import Screenshots
        if screenshots_frame_pos is not None:
            cap = cv2.VideoCapture(movie_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            for i, s in enumerate(screenshots_frame_pos):
                project.create_screenshot_headless("Screenshot_" + str(i).zfill(3), frame_pos=s, fps=fps)

        # Store the project
        project.store_project(HeadlessUserSettings(), project.path)
        return project
    except Exception as e:
        try:
            shutil.rmtree(location)
        except:
            print("Could not remove folder: ", location)
        raise e
        return None




if __name__ == '__main__':
    # p = load_project_headless("C:/Users/Gaudenz Halter/Documents/VIAN/229_1_1_Jigokumon_1953_BF/229_1_1_Jigokumon_1953_BF.eext")
    segmentations = [
        ["Main", [
            [0, 1000, "Hello"],
            [1001, 5000, "World"]
            ]
         ]
    ]
    screenshots = [300, 500, 800]
    p = create_project_headless("TestHeadlessCreation", "C:/Users/Gaudenz Halter/Documents/VIAN/TestHeadlessCreation/",
                                "C:/Users/Gaudenz Halter/Desktop/229_1_1_Jigokumon_1953_DVD.mov",
                                screenshots, segmentations)
