"""
This Module enables a headless opening and closing of VIANProjects, 
this it can be used to perform operations in a batch process without having the gui enabled. 

"""

from core.container.project import *
from core.data.settings import UserSettings
from core.data.project_streaming import *
from core.data.hdf5_manager import *
from shutil import copy2, move
# from core.gui.main_window import *
from typing import Dict, Tuple
from core.analysis.analysis_import import *
from threading import Lock, Thread


PROJECT_LOCK = Lock()


VERSION = "0.6.6"
class HeadlessUserSettings():
    def __init__(self):
        self.PROJECT_FILE_EXTENSION = ".eext"
        self.SCREENSHOTS_STATIC_SAVE = False


class HeadlessMainWindow(QObject):
    def __init__(self):
        super(HeadlessMainWindow, self).__init__()
        self.thread_pool = QThreadPool()
        # self.numpy_data_manager = NumpyDataManager(self)
        self.project_streamer = SQLiteStreamer(self)
        self.version = VERSION
        self.project = None
        self.settings = HeadlessUserSettings()

        self.thread_pool = QThreadPool(self)
        # self.corpus_interface = LocalCorpusInterface()

    def print_message(self, msg, color):
        print(msg)

    def close(self):
        self.project = None
        self.project_streamer.on_closed()

    #region Analysis
    def start_worker(self, worker, name = "New Task"):
        self.thread_pool.start(worker)

    def run_analysis(self, analysis:IAnalysisJob, targets:List[IProjectContainer], parameters:Dict, class_objs:List[ClassificationObject], fps):
        args = analysis.prepare(self.project, targets, parameters, fps, class_objs)

        if analysis.multiple_result:
            for i, arg in enumerate(args):
                res = analysis.process(arg, self.worker_progress)
                with PROJECT_LOCK:
                    analysis.modify_project(self.project, res)
                    self.project.add_analysis(res)
        else:
            res = analysis.process(args, self.worker_progress)
            with PROJECT_LOCK:
                analysis.modify_project(self.project, res)
                self.project.add_analysis(res)

    def run_analysis_threaded(self, analysis:IAnalysisJob, targets:List[IProjectContainer], parameters:Dict, class_objs:List[ClassificationObject], fps, n_threads = 5, n_targets = 1):
        threads = []
        targets_thread = []
        for i, s in enumerate(targets):
            targets_thread.append(s)
            if i % n_targets == 0:
                thread = Thread(target=self.run_analysis,
                                args=(analysis, targets_thread, parameters, class_objs, fps))
                thread.start()
                threads.append(thread)
                targets_thread = []

            if i % n_threads * n_targets == 0 or i == len(targets) - 1:
                print(i, "/", len(targets))
                for t in threads:
                    t.join()

    def worker_progress(self, tpl):
        return
        print(tpl)

    def worker_error(self, args):
        print("Error", args)

    def worker_finished(self, args):
        print("Error", args)



    #endregion

    # #region Corpus
    # def connect_local_corpus(self, user, path):
    #     self.corpus_interface.connect_user(user, path)
    # def commit_local(self, user, project):
    #     self.corpus_interface.commit_project(user, project)
    # #endregion

    #region Dispatcher
    def dispatch_on_changed(self, receiver=None, item=None):
        pass

    def dispatch_on_loaded(self, *args):
        if self.project is not None:
            self.project_streamer.on_loaded(self.project)
            # self.numpy_data_manager.on_loaded(self.project)

    def dispatch_on_closed(self, *args):
        pass
    #endregion

    def eval_class(self, name):
        return eval(name)

    def load_screenshots(self):
        if self.project is None:
            return
        cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        for i, s in enumerate(self.project.screenshots):
            if i % 10 == 0:
                sys.stdout.write("\r" + str(round(i / len(self.project.screenshots), 2) * 100) + "% Loaded Screenshots")
            cap.set(cv2.CAP_PROP_POS_FRAMES, s.frame_pos)
            ret, frame = cap.read()
            s.img_movie = frame


def load_project_headless(path) -> Tuple[VIANProject, HeadlessMainWindow]:
    """
    Loads a VIAN project without needing a VIAN instance running by emulating VIAN. 
    :param path: The path to the project to load
    :return: a loaded VIANProject or None if failed
    """
    try:
        mw = HeadlessMainWindow()
        project = VIANProject(mw)
        mw.project = project
        project.inhibit_dispatch = True
        project.load_project(HeadlessUserSettings(), path)
        project.hdf5_manager.initialize_all([SemanticSegmentationAnalysis,
                                             ColorPaletteAnalysis,
                                             ColorFeatureAnalysis,
                                             BarcodeAnalysisJob,
                                             MovieMosaicAnalysis])
        mw.dispatch_on_loaded()
        return project, mw
    except Exception as e:
        print(e)
        return None, None


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


        if os.path.isdir(project.folder):
            c = 0
            while(os.path.isdir(project.folder + "_" +str(c).zfill(2))):
                c += 1
            project.folder = project.folder + "_" +str(c).zfill(2)

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
        cap = cv2.VideoCapture(movie_path)
        if screenshots_frame_pos is not None:
            fps = cap.get(cv2.CAP_PROP_FPS)
            for i, s in enumerate(screenshots_frame_pos):
                project.create_screenshot_headless("Screenshot_" + str(i).zfill(3), frame_pos=s, fps=fps)
        # Store the project
        project.store_project(HeadlessUserSettings(), project.path)
        project.connect_hdf5()
        project.hdf5_manager.initialize_all([SemanticSegmentationAnalysis, ColorPaletteAnalysis, ColorFeatureAnalysis, BarcodeAnalysisJob, MovieMosaicAnalysis])
        project.hdf5_manager.initialize_colorimetry(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / 30))
        return project
    except Exception as e:
        try:
            pass
            # shutil.rmtree(location)
        except:
            print("Could not remove folder: ", location)
        raise e


if __name__ == '__main__':
    pass
    # Analysis Example
    # (p, mw) = load_project_headless("F:/_projects//107_1_1_Leave Her to Heaven_1945//107_1_1_Leave Her to Heaven_1945.eext")
    # obj_fg = p.experiments[0].get_classification_object_by_name("Foreground")
    # mw.run_analysis(ColorFeatureAnalysis(), p.screenshots, dict(resolution=50), class_objs=[obj_fg], fps = p.movie_descriptor.fps)
    # mw.thread_pool.waitForDone()
