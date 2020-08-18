"""
This Module enables a headless opening and closing of VIANProjects, 
this it can be used to perform operations in a batch process without having the gui enabled. 

"""

from core.data.settings import Contributor
from core.container.hdf5_manager import *
from shutil import move
# from core.gui.main_window import *
from typing import Dict
from core.analysis.analysis_import import *
from threading import Lock, Thread
from random import sample
from core.data.corpus_client import WebAppCorpusInterface

PROJECT_LOCK = Lock()
_INIT_LOCK = Lock()

VERSION = "0.6.6"
MAIN_WINDOW = None
PAL_WIDTH = 720
PNG_COMPRESSION_RATE = 9

attributes = None



class PlotWindow(QMainWindow):
    def __init__(self):
        super(PlotWindow, self).__init__()

    @pyqtSlot(object)
    def on_plot(self, analysis):
        if isinstance(analysis, list):
            for x in analysis:
                for v in x.get_visualization():
                    mw = QMainWindow(MAIN_WINDOW)
                    mw.setCentralWidget(v.widget)
                    mw.show()
        else:
            for v in analysis.get_visualization():
                mw = QMainWindow(MAIN_WINDOW)
                mw.setCentralWidget(v.widget)
                mw.show()


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print((exctype, value, traceback))
    # Call the normal Exception hook after
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)

def _init_application():
    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("qt_ui/images/main.png"))

    style_sheet = open("E:\\Programming\\Git\\visual-movie-annotator\\qt_ui\\themes\\qt_stylesheet_very_dark.css", 'r')
    style_sheet = style_sheet.read()
    app.setStyleSheet(style_sheet)

    global MAIN_WINDOW
    MAIN_WINDOW = PlotWindow()
    print("Running", MAIN_WINDOW)
    sys.exit(app.exec_())


_window_thread = thread = Thread(target=_init_application)
_window_thread.start()
while(MAIN_WINDOW is None): pass


class HeadlessUserSettings():
    def __init__(self):
        self.PROJECT_FILE_EXTENSION = ".eext"
        self.SCREENSHOTS_STATIC_SAVE = False


class HeadlessMainWindow(QObject):
    onShowPlot = pyqtSignal(object)
    def __init__(self):
        super(HeadlessMainWindow, self).__init__()
        self.thread_pool = QThreadPool()
        # self.numpy_data_manager = NumpyDataManager(self)
        # self.project_streamer = SQLiteStreamer(self)
        self.version = VERSION
        self.project = None
        self.settings = HeadlessUserSettings()
        self.onShowPlot.connect(MAIN_WINDOW.on_plot)

        # self.thread_pool = QThreadPool(self)
        # self.corpus_interface = LocalCorpusInterface()

    def print_message(self, msg, color):
        print(msg)

    def close(self):
        self.project = None
        # self.project_streamer.on_closed()

    #region Analysis
    # def start_worker(self, worker, name = "New Task"):
    #     self.thread_pool.start(worker)

    def run_analysis(self, analysis:IAnalysisJob, targets:List[IProjectContainer], parameters:Dict, class_objs:List[ClassificationObject], fps):
        for clobj in class_objs:
            args = analysis.prepare(self.project, targets, parameters, fps, clobj)

            res = []
            if analysis.multiple_result:
                for i, arg in enumerate(args):
                    res.append(analysis.process(arg, self.worker_progress))
            else:
                res = analysis.process(args, self.worker_progress)

            if isinstance(res, list):
                for r in res:
                    with PROJECT_LOCK:
                        analysis.modify_project(self.project, r )
                        self.project.add_analysis(r)
            else:
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
        pass

    def worker_error(self, args):
        print("Error", args)

    def worker_finished(self, args):
        print("Error", args)
    #endregion


    #region Dispatcher
    def dispatch_on_changed(self, receiver=None, item=None):
        pass

    def dispatch_on_loaded(self, *args):
        if self.project is not None:
            pass
            # self.project_streamer.on_loaded(self.project)
            # self.numpy_data_manager.on_loaded(self.project)

    def dispatch_on_closed(self, *args):
        pass

    #endregion

    def eval_class(self, name):
        return eval(name)

    def load_screenshots(self):
        if self.project is None:
            return
        print(self.project.movie_descriptor.movie_path)
        cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        for i, s in enumerate(self.project.screenshots):
            if i % 10 == 0:
                sys.stdout.write("\r" + str(round(i / len(self.project.screenshots), 2) * 100) + "% Loaded Screenshots")
            cap.set(cv2.CAP_PROP_POS_FRAMES, s.frame_pos)
            ret, frame = cap.read()
            s.set_img_movie(frame)

    def plot(self, analysis:IAnalysisJobAnalysis):
        self.onShowPlot.emit(analysis)



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
        project.headless_mode = True
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
        raise e
        print(e)
        return None, None


def create_project_headless(name, location, movie_path, screenshots_frame_pos = None,
                            segmentations = None, move_movie="None", template_path = "") -> VIANProject:
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
        project.connect_hdf5()

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
        project.store_project(project.path)
        project.connect_hdf5()
        project.hdf5_manager.initialize_all()
        project.hdf5_manager.initialize_colorimetry(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / 30))

        return project
    except Exception as e:
        raise e


def ping_webapp(email, password, webapp_url = "http://ercwebapp.westeurope.cloudapp.azure.com:5000/api/"):
    contributor = Contributor(email=email, password=password)
    interface = WebAppCorpusInterface(webapp_url)
    interface.login(contributor)


def to_webapp(project, email = "", password = "", webapp_url = "http://ercwebapp.westeurope.cloudapp.azure.com:5000/api/", bake_only = False):
    contributor = Contributor(email=email, password=password)
    if bake_only:
        interface = WebAppCorpusInterface(webapp_url)
        interface.commit_project(project, None)
    else:
        interface = WebAppCorpusInterface(webapp_url)
        interface.login(contributor)
        interface.commit_project(project, contributor)


def to_corpus(project):
    """
            Here we actually commit the project, 
            this includes to prepare the project, baking screenshots and masks into image files 
            and upload them to the Server
            :param user: 
            :param project: 
            :return: 
            """
    try:
        export_root = project.folder + "/corpus_export/"
        export_project_dir = export_root + "project/"
        scr_dir = export_project_dir + "/scr/"
        mask_dir = export_project_dir + "/masks/"
        export_hdf5_path = os.path.join(export_project_dir, os.path.split(project.hdf5_path)[1])
        # Create the temporary directories
        try:
            if os.path.isdir(export_root):
                shutil.rmtree(export_root, ignore_errors=True)
            if not os.path.isdir(export_root):
                os.mkdir(export_root)
            if not os.path.isdir(export_project_dir):
                os.mkdir(export_project_dir)
                # if not os.path.isdir(scr_dir):
                #     os.mkdir(scr_dir)
                # if not os.path.isdir(mask_dir):
                #     os.mkdir(mask_dir)
        except Exception as e:
            QMessageBox.Information("Commit Error", "Could not modify \\corpus_export\\ directory."
                                                    "\nPlease make sure the Folder is not open in the Explorer/Finder.")
            return False, None
        # -- Create a HDF5 File for the Export -- #
        shutil.copy2(project.hdf5_path, export_hdf5_path)
        h5_file = h5py.File(export_hdf5_path, "r+")

        # -- Thumbnail --
        if len(project.screenshots) > 0:
            thumb = sample(project.screenshots, 1)[0].get_img_movie(True)
            cv2.imwrite(export_project_dir + "thumbnail.jpg", thumb)

        # -- Export all Screenshots --

        # Maps the unique ID of the screenshot to it's mask path -> dict(key:unique_id, val:dict(scene_id, segm_shot_id, group, path))
        mask_index = dict()
        shots_index = dict()

        for i, scr in enumerate(project.screenshots):
            sys.stdout.write(
                "\r" + str(round(i / len(project.screenshots), 2) * 100).rjust(3) + "%\t Baking Screenshots")

            img = cv2.cvtColor(scr.get_img_movie(True), cv2.COLOR_BGR2BGRA)
            # # Export the Screenshot as extracted from the movie
            grp_name = scr.screenshot_group
            name = scr_dir + grp_name + "_" \
                   + str(scr.scene_id) + "_" \
                   + str(scr.shot_id_segm) + ".jpg"
            if img.shape[1] > PAL_WIDTH:
                fx = PAL_WIDTH / img.shape[1]
                img = cv2.resize(img, None, None, fx, fx, cv2.INTER_CUBIC)

            if i == 0:
                h5_file.create_dataset("screenshots", shape=(len(project.screenshots),) + img.shape, dtype=np.uint8)
            # cv2.imwrite(name, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            h5_file['screenshots'][i] = img

            shots_index[scr.unique_id] = dict(
                scene_id=scr.scene_id,
                shot_id_segm=scr.shot_id_segm,
                group=grp_name,
                hdf5_idx=i,
                path=name
            )

            # Export the Screenshots with all masks applied
            for e in project.experiments:
                # First we have to find all experiments that have Classification Objects with Mask Labels
                masks_to_export = []
                for cobj in e.get_classification_objects_plain():
                    sem_labels = cobj.semantic_segmentation_labels[1]
                    ds_name = cobj.semantic_segmentation_labels[0]
                    if ds_name != "":
                        masks_to_export.append(dict(obj_name=cobj.name, ds_name=ds_name, labels=sem_labels))
                masks_to_export_names = [m['ds_name'] for m in masks_to_export]

                for counter, entry in enumerate(masks_to_export):
                    # Find the correct Mask Analysis
                    for a in scr.connected_analyses:
                        if isinstance(a,
                                      SemanticSegmentationAnalysisContainer) and a.analysis_job_class == SemanticSegmentationAnalysis.__name__:
                            # table = SQ_TABLE_MASKS
                            data = a.get_adata()
                            dataset = a.dataset
                            mask_idx = project.hdf5_manager._uid_index[a.unique_id]
                            # data = dict(db[table].find_one(key=a.unique_id))['json']
                            # data = project.main_window.eval_class(a.analysis_job_class)().from_json(data)

                            if dataset in masks_to_export_names:
                                # mask = cv2.resize(data.astype(np.uint8), (img.shape[1], img.shape[0]),
                                #                   interpolation=cv2.INTER_NEAREST)

                                mask_path = mask_dir + dataset + "_" + str(scr.scene_id) + "_" + str(
                                    scr.shot_id_segm) + ".png"
                                # cv2.imwrite(mask_path, mask, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_RATE])

                                if scr.unique_id not in mask_index:
                                    mask_index[str(scr.unique_id)] = []

                                mask_index[scr.unique_id].append((dict(
                                    scene_id=scr.scene_id,
                                    dataset=dataset,
                                    shot_id_segm=scr.shot_id_segm,
                                    group=grp_name,
                                    path=mask_path.replace(project.folder, ""),
                                    hdf5_index=mask_idx,
                                    scr_region=a.entry_shape)
                                ))

        with open(export_project_dir + "image_linker.json", "w") as f:
            json.dump(dict(masks=mask_index, shots=shots_index), f)

        h5_file.close()

        # -- Creating the Archive --
        print("Export to:", export_project_dir)
        project.store_project(os.path.join(export_project_dir, project.name + ".eext"))
        archive_file = os.path.join(export_root, project.name)
        shutil.make_archive(archive_file, 'zip', export_project_dir)
    except Exception as e:
        print(e)




if __name__ == '__main__':
    pass
    # Analysis Example
    # (p, mw) = load_project_headless("F:/_projects//107_1_1_Leave Her to Heaven_1945//107_1_1_Leave Her to Heaven_1945.eext")
    # obj_fg = p.experiments[0].get_classification_object_by_name("Foreground")
    # mw.run_analysis(ColorFeatureAnalysis(), p.screenshots, dict(resolution=50), class_objs=[obj_fg], fps = p.movie_descriptor.fps)
    # mw.thread_pool.waitForDone()
