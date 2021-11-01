from vian.core.concurrent.worker_functions import *
from vian.core.concurrent.update_erc_template import ERCUpdateJob
from vian.core.concurrent.timestep_update import TimestepUpdateWorkerSingle
from vian.core.concurrent.worker import WorkerManager, MinimalThreadWorker
from vian.core.concurrent.image_loader import ClassificationObjectChangedJob
from vian.core.concurrent.auto_screenshot import DialogAutoScreenshot
from vian.core.concurrent.auto_segmentation import DialogAutoSegmentation
from vian.core.analysis.analysis_import import *
from vian.core.data.computation import is_vian_light

from vian.core.gui.vian_webapp import *
from vian.core.data.cache import HDF5Cache
from vian.core.data.exporters import *
from vian.core.data.importers import *
from vian.core.data.corpus_client import WebAppCorpusInterface, get_vian_version
from vian.core.data.computation import version_check
from vian.core.data.settings import UserSettings, Contributor
from vian.core.data.audio_handler2 import AudioHandler
from vian.core.data.creation_events import VIANEventHandler, ALL_REGISTERED_PIPELINES
from vian.flask_server.server import FlaskServer, FlaskWebWidget, VIAN_PORT

from vian.core.gui.dialogs.csv_vocabulary_importer_dialog import CSVVocabularyImportDialog
from vian.core.gui.dialogs.export_segmentation_dialog import ExportSegmentationDialog
from vian.core.gui.dialogs.export_template_dialog import ExportTemplateDialog
from vian.core.gui.dialogs.new_project_dialog import NewProjectDialog
from vian.core.gui.dialogs.preferences_dialog import DialogPreferences
from vian.core.gui.dialogs.screenshot_exporter_dialog import DialogScreenshotExporter
from vian.core.gui.dialogs.screenshot_importer_dialog import DialogScreenshotImport
from vian.core.gui.dialogs.letterbox_widget import LetterBoxWidget
from vian.core.gui.dialogs.analyses_dialog import AnalysisDialog
from vian.core.gui.analysis_results import AnalysisResultsDock, AnalysisResultsWidget
from vian.core.gui.classification import ClassificationWindow
from vian.core.gui.colormetry_widget import *
from vian.core.gui.concurrent_tasks import ConcurrentTaskDock
from vian.core.gui.drawing_widget import DrawingOverlay, DrawingEditorWidget, AnnotationToolbar, AnnotationOptionsDock, \
    ALWAYS_VLC
from vian.core.analysis.analysis_import import *
from vian.core.gui.search_window import SearchWindow
from vian.core.gui.experiment_editor import ExperimentEditorDock
# from vian.core.gui.face_identificator import FaceIdentificatorDock
from vian.core.gui.history import HistoryView
from vian.core.gui.inspector import Inspector
from vian.core.gui.outliner import Outliner
from vian.core.gui.perspectives import PerspectiveManager, Perspective
from vian.core.gui.player_controls import PlayerControls
from vian.core.gui.player_vlc import Player_VLC, PlayerDockWidget

from vian.core.gui.screenshot_manager import ScreenshotsManagerWidget, ScreenshotsToolbar, ScreenshotsManagerDockWidget
from vian.core.gui.status_bar import StatusBar, OutputLine, StatusProgressBar, StatusVideoSource
from vian.core.gui.timeline.timeline import TimelineContainer
from vian.core.gui.vocabulary import VocabularyManager #VocabularyExportDialog
from vian.core.gui.pipeline_widget import PipelineDock, PipelineToolbar
from vian.core.gui.corpus_widget import CorpusDockWidget
from vian.core.gui.misc.filmography_widget import query_initial

from vian.core.node_editor.node_editor import NodeEditorDock
from vian.core.node_editor.script_results import NodeEditorResults
from vian.extensions.extension_list import ExtensionList

from vian.core.container.vocabulary_library import VocabularyLibrary
from vian.core.concurrent.worker import Worker
from vian.core.container.hdf5_manager import print_registered_analyses, get_all_analyses
from vian.core.gui.toolbar import WidgetsToolbar
from vian.core.data.log import log_info

from vian.core.data.settings import get_vian_data
from pathlib import Path
import cProfile

try:
    import keras.backend as K
    from vian.core.analysis.semantic_segmentation import *
    log_info("KERAS Found, Deep Learning available.")
    KERAS_AVAILABLE = True
except Exception as e:
    from vian.core.analysis.deep_learning.labels import *
    log_info("Could not import Deep-Learning Module, features disabled.")
    log_info(e)
    KERAS_AVAILABLE = False

VERSION = "0.8.0"

PROFILE = False


class MainWindow(QtWidgets.QMainWindow):
    onTimeStep = pyqtSignal(int)
    onUpdateFrame = pyqtSignal(int, int)
    onSegmentStep = pyqtSignal(object)
    currentSegmentChanged = pyqtSignal(int)
    abortAllConcurrentThreads = pyqtSignal()
    onOpenCVFrameVisibilityChanged = pyqtSignal(bool)
    onCorpusConnected = pyqtSignal(object)
    onCorpusDisconnected = pyqtSignal(object)
    currentClassificationObjectChanged = pyqtSignal(object)
    onAnalysisIntegrated = pyqtSignal()

    onProjectOpened = pyqtSignal(object)
    onMovieOpened = pyqtSignal(object)
    onProjectClosed = pyqtSignal()

    onMultiExperimentChanged = pyqtSignal(bool)
    onSave = pyqtSignal()

    onStartFlaskServer = pyqtSignal()
    onStopFlaskServer = pyqtSignal()

    def __init__(self, loading_screen:QSplashScreen, file = None):
        super(MainWindow, self).__init__()
        path = os.path.abspath("qt_ui/MainWindow.ui")
        uic.loadUi(path, self)
        log_info("VIAN: ", version.__version__)

        loading_screen.setStyleSheet("QWidget{font-family: \"Helvetica\"; font-size: 10pt;}")

        if PROFILE:
            self.profiler = cProfile.Profile()
            self.profiler.enable()

        self.setAcceptDrops(True)
        self.has_open_project = False
        self.version = version.__version__
        self.forced_overlay_hidden = False

        self.extension_list = ExtensionList(self)
        log_info("Registered Pipelines:")
        for k, v in ALL_REGISTERED_PIPELINES.items():
            log_info("\t---", k.ljust(30),v)
        print_registered_analyses()
        log_info("\n")
        self.is_darwin = False

        self.application_in_focus = True

        # for MacOS
        if sys.platform == "darwin":
            self.is_darwin = True
            self.setAttribute(Qt.WA_MacFrameworkScaled)
            self.setAttribute(Qt.WA_MacOpaqueSizeGrip)


        self.plugin_menu = self.extension_list.get_plugin_menu(self.menuWindows)
        self.menuBar().addMenu(self.plugin_menu)
        self.menuAnalysis.addMenu(self.extension_list.get_analysis_menu(self.menuAnalysis, self))
        if is_vian_light():
            self.plugin_menu.menuAction().setVisible(False)

        QApplication.instance().setAttribute(Qt.AA_DontUseNativeMenuBar)
        self.dock_widgets = []
        self.open_dialogs = []

        self.settings = UserSettings()
        self.settings.load()

        self.hdf5_cache = HDF5Cache(self.settings.DIR_ROOT + "/scr_cache.hdf5")

        self.clipboard_data = []
        # loading_screen.showMessage("Checking ELAN Connection", Qt.AlignHCenter|Qt.AlignBottom,
        #                            QColor(200,200,200,100))

        # self.updater = VianUpdater(self, self.version)

        # Central Widgets
        self.video_player = None
        self.screenshots_manager = None
        self.allow_dispatch_on_change = True

        self.thread_pool = QThreadPool.globalInstance()
        self.vian_event_handler_thread = QThread()
        self.vian_event_handler = VIANEventHandler(None)
        self.vian_event_handler.moveToThread(self.vian_event_handler_thread)
        self.vian_event_handler_thread.start()

        self.colormetry_running = False
        self.colormetry_job = None

        self.video_capture = None

        self.current_perspective = Perspective.Annotation.name

        self.analysis_list = []
        self.create_analysis_list()

        # DockWidgets
        self.player_controls = None
        self.elan_status = None
        self.source_status = None
        self.phonon_player = None
        self.annotation_toolbar = None
        self.annotation_options = None
        self.drawing_overlay = None
        self.timeline = None
        self.output_line = None
        self.perspective_manager = None
        self.screenshot_toolbar = None
        self.outliner = None
        self.progress_bar = None
        self.inspector = None
        self.history_view = None
        self.analyses_widget = None
        self.screenshots_manager_dock = None
        self.node_editor_dock = None
        self.node_editor_results = None
        self.vocabulary_manager = None
        self.vocabulary_matrix = None
        self.analysis_results_widget = None
        self.analysis_results_widget_dock = None
        self.experiment_dock = None
        self.corpus_client_toolbar = None
        self.facial_identification_dock = None
        self.pipeline_widget = None
        self.script_editor = None
        self.corpus_widget = None
        self.summary_dock = None

        self.progress_popup = None

        self.colorimetry_live = None
        self.query_widget = None

        # This is the Widget created when Double Clicking on a SVGAnnotation
        # This is store here, because is has to be removed on click, and because the background of the DrawingWidget
        # is Transparent
        self.drawing_editor = None
        self.concurrent_task_viewer = None

        self.player = Player_VLC(self)
        self.player_dock_widget = None

        self.project = VIANProject(name="Default Project", path=None)
        self.corpus_client = CorpusClient()

        self.frame_update_worker = TimestepUpdateWorkerSingle(self.settings)
        self.frame_update_thread = QThread()
        self.frame_update_worker.moveToThread(self.frame_update_thread)
        self.onUpdateFrame.connect(self.frame_update_worker.perform)
        self.frame_update_thread.start()

        self.audio_handler = AudioHandler(resolution=0.1, callback=print)
        if not is_vian_light():
            self.audio_handler_thread = QThread()
            self.audio_handler.moveToThread(self.audio_handler_thread)
            self.audio_handler_thread.start()

        self.flask_server = FlaskServer(None)
        if not is_vian_light():
            self.flask_server_thread = QThread()
            self.flask_server.moveToThread(self.flask_server_thread)
            self.flask_server_thread.start()
            self.onStartFlaskServer.connect(self.flask_server.run_server)
            self.onStartFlaskServer.emit()


        self.vocabulary_library = VocabularyLibrary().load(os.path.join(self.settings.DIR_TEMPLATES, "library.json"))
        self.vocabulary_library.onLibraryChanged.connect(self.on_vocabulary_library_changed)

        self.web_view = FlaskWebWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.web_view, Qt.Horizontal)
        self.web_view.set_url("http://127.0.0.1:{p}/screenshot_vis".format(p=VIAN_PORT))
        # self.web_view.set_url("https://threejs.org/examples/#webgl_camera")

        self.web_view.hide()

        print("OK")
        self.create_widget_elan_status()
        self.create_widget_video_player()
        self.drawing_overlay = DrawingOverlay(self, self.player.videoframe, self.project)
        self.create_annotation_toolbar()
        self.create_annotation_dock()
        self.annotation_options.optionsChanged.connect(self.annotation_toolbar.on_options_changed)
        self.annotation_options.optionsChanged.connect(self.drawing_overlay.on_options_changed)
        self.create_screenshot_manager()
        self.create_node_editor_results()
        self.create_node_editor()
        self.create_screenshots_toolbar()
        self.create_outliner()
        self.create_screenshot_manager_dock_widget()
        self.create_inspector()
        self.create_timeline()
        self.create_widget_player_controls()
        self.create_perspectives_manager()
        self.create_history_view()
        self.create_concurrent_task_viewer()
        self.create_vocabulary_manager()
        self.create_vocabulary_matrix()
        self.create_query_widget()
        self.create_analysis_results_widget()

        self.create_colorimetry_live()
        self.create_experiment_editor()
        self.create_corpus_widget()
        self.create_summary_dock()

        self.pipeline_toolbar = PipelineToolbar(self)

        self.search_window = SearchWindow(self)
        self.search_window.hide()

        self.create_corpus_client_toolbar()
        self.create_pipeline_widget()
        self.script_editor = self.pipeline_widget.editor

        self.window_toolbar = WidgetsToolbar(self)
        self.addToolBar(Qt.RightToolBarArea, self.window_toolbar)

        self.addToolBar(Qt.RightToolBarArea, self.pipeline_toolbar)

        self.splitDockWidget(self.player_controls, self.perspective_manager, Qt.Horizontal)
        self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)

        self.tabifyDockWidget(self.inspector, self.history_view)
        self.tabifyDockWidget(self.screenshots_manager_dock, self.vocabulary_matrix)

        self.tabifyDockWidget(self.inspector, self.concurrent_task_viewer)

        self.annotation_toolbar.raise_()
        self.inspector.raise_()
        self.screenshots_manager_dock.raise_()

        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.East)
        self.history_view.hide()
        self.concurrent_task_viewer.hide()

        self.frame_update_worker.signals.onSpatialDatasetsChanged.connect(
            self.player_dock_widget.on_spatial_datasets_changed)
        self.player_dock_widget.onCurrentSpatialDatasetSelected.connect(
            self.frame_update_worker.on_set_spatial_dataset)

        self.worker_manager = WorkerManager(self)

        self.concurrent_task_viewer.onTotalProgressUpdate.connect(self.progress_bar.set_progress)
        self.audio_handler.audioProcessed.connect(self.timeline.timeline.add_visualization)

        self.actionNew.triggered.connect(self.action_new_project)
        self.actionLoad.triggered.connect(self.on_load_project)
        self.actionSave.triggered.connect(self.on_save_project)
        self.actionSaveAs.triggered.connect(self.on_save_project_as)
        self.actionBackup.triggered.connect(self.on_backup)
        self.actionCleanUpRecent.triggered.connect(self.cleanup_recent)
        self.actionCompare_Project_with.triggered.connect(self.on_compare)

        self.actionNew_Corpus.triggered.connect(self.corpus_widget.on_new_corpus)
        self.actionLoad_Corpus.triggered.connect(self.corpus_widget.on_load_corpus)
        self.actionClose_Corpus.triggered.connect(self.corpus_widget.on_close_corpus)

        ## IMPORT
        self.actionImportELANSegmentation.triggered.connect(self.import_segmentation)
        self.actionImportElanNewProject.triggered.connect(partial(self.import_elan_project, "", True))
        self.actionImportElanThisProject.triggered.connect(partial(self.import_elan_project, "", False))
        self.actionImportVocabulary.triggered.connect(partial(self.import_vocabulary, None))
        self.actionImportCSVVocabulary.triggered.connect(self.import_csv_vocabulary)
        self.actionImportScreenshots.triggered.connect(self.import_screenshots)
        self.actionImportVIANExperiment.triggered.connect(self.import_experiment)
        self.actionImportWebApp.triggered.connect(self.import_webapp)
        self.actionSRT_File.triggered.connect(self.import_srt)
        self.actionSelectTemplate_File.triggered.connect(partial(self.import_template, None))
        self.actionImportEyetracking_Dataset.triggered.connect(self.import_eyetracking)

        import glob

        templates = glob.glob(self.settings.DIR_TEMPLATES + "*.viant")
        templates.extend(glob.glob(get_vian_data("templates/" + "*.viant")))
        for t in templates:
            a = self.menuVIAN_Template.addAction(os.path.split(t)[1].split(".")[0])
            a.triggered.connect(partial(self.import_template, t))


        ## EXPORT
        self.action_ExportSegmentation.triggered.connect(self.export_segmentation)
        self.actionExportTemplate.triggered.connect(self.export_template)
        self.actionExportVocabulary.triggered.connect(self.export_vocabulary)
        self.actionClose_Project.triggered.connect(self.close_project)
        self.actionZip_Project.triggered.connect(self.on_zip_project)
        self.actionExit.triggered.connect(self.on_exit)
        self.actionScreenshotsExport.triggered.connect(self.on_export_screenshots)
        self.actionExportMovie_Segment.triggered.connect(self.on_export_movie_segments)
        self.actionExportCSV.triggered.connect(self.on_export_csv)
        self.actionExportExcel.triggered.connect(self.on_export_excel)
        self.actionExportColorimetry.triggered.connect(self.on_export_colorimetry)
        self.actionProject_Summary.triggered.connect(self.on_export_summary)
        self.actionExportVIANWebApp.triggered.connect(self.on_export_vianwebapp)
        self.actionSequence_Protocol.triggered.connect(self.on_export_sequence_protocol)

        # Edit Menu
        self.actionUndo.triggered.connect(self.on_undo)
        self.actionRedo.triggered.connect(self.on_redo)
        self.actionCopy.triggered.connect(self.on_copy)
        self.actionPaste.triggered.connect(self.on_paste)
        self.actionDelete.triggered.connect(self.on_delete)
        self.actionDelete.setShortcuts([QKeySequence(Qt.Key_Delete), QKeySequence(Qt.Key_Backspace)])
        self.actionRun_Pipeline_for_Selection.triggered.connect(self.pipeline_widget.pipeline.run_selection)
        self.actionRun_Complete_Pipeline.triggered.connect(self.pipeline_widget.pipeline.run_all)
        self.actionDelete_all_Analyses.triggered.connect(self.on_remove_all_analyses)
        self.actionFind.triggered.connect(self.on_search)

        # Tab Windows
        self.actionScreenshot_Manager.triggered.connect(self.create_screenshot_manager_dock_widget)
        self.actionPreferences.triggered.connect(self.open_preferences)
        self.actionAnnotation_Toolbox.triggered.connect(self.create_annotation_toolbar)
        self.actionScreenshot_Toolbox.triggered.connect(self.create_screenshots_toolbar)
        self.actionPlayerControls.triggered.connect(self.create_widget_player_controls)
        self.actionPerspectivesToggle.triggered.connect(self.create_perspectives_manager)
        self.actionOutliner.triggered.connect(self.create_outliner)
        self.actionVocabularyManager.triggered.connect(self.create_vocabulary_manager)
        self.actionInspector.triggered.connect(self.create_inspector)
        self.actionTimeline.triggered.connect(self.create_timeline)
        self.actionFullscreen.triggered.connect(self.toggle_fullscreen)
        self.actionToggleStatusBar.triggered.connect(self.toggle_statusbar)
        self.actionScriptEditor.triggered.connect(self.pipeline_widget.show)
        self.actionClassification.triggered.connect(self.create_vocabulary_matrix)
        self.actionWebApp_Upload.triggered.connect(self.create_corpus_client_toolbar)

        # self.menuBar().actionAnnotationPersp.hide()

        self.actionExperimentSetupPersp.triggered.connect(partial(self.switch_perspective, Perspective.ExperimentSetup))
        self.actionPlayerPersp.triggered.connect(partial(self.switch_perspective, Perspective.VideoPlayer))
        self.actionAnnotationPersp.triggered.connect(partial(self.switch_perspective, Perspective.Annotation))
        self.actionScreenshotsPersp.triggered.connect(partial(self.switch_perspective, Perspective.ScreenshotsManager))
        self.actionNodeEditorPerspective.triggered.connect(partial(self.switch_perspective, Perspective.Analyses))
        self.actionSegmentationPersp.triggered.connect(partial(self.switch_perspective, Perspective.Segmentation))
        self.actionResultsPersp.triggered.connect(partial(self.switch_perspective, Perspective.Results))
        self.actionVocabularyPersp.triggered.connect(partial(self.switch_perspective, Perspective.Classification))
        self.actionQuick_Annotation.triggered.connect(partial(self.switch_perspective, Perspective.QuickAnnotation))

        self.actionHistory.triggered.connect(self.create_history_view)
        self.actionTaksMonitor.triggered.connect(self.create_concurrent_task_viewer)
        self.actionAdd_Annotation_Layer.triggered.connect(self.on_new_annotation_layer)
        self.actionAdd_Segmentation.triggered.connect(self.on_new_segmentation)

        self.actionScreenshot.triggered.connect(self.on_screenshot)
        self.actionAdd_Key.triggered.connect(self.on_key_annotation)
        self.actionAdd_Segment.triggered.connect(self.on_new_segment)
        self.actionCreateExperiment.triggered.connect(self.on_create_experiment)
        self.actionAbout.triggered.connect(self.on_about)
        self.actionWelcome.triggered.connect(self.show_welcome)
        self.actionIncreasePlayRate.triggered.connect(self.increase_playrate)
        self.actionDecreasePlayRate.triggered.connect(self.decrease_playrate)
        self.actionUpdate.triggered.connect(self.check_update)

        self.actionCorpus.triggered.connect(self.corpus_client_toolbar.show)

        #TOOLS
        self.actionAuto_Segmentation.triggered.connect(self.on_auto_segmentation)
        self.actionAuto_Screenshots.triggered.connect(self.on_auto_screenshot)


        #ANALYSES
        analysis_menues = dict(
            Color=self.menuColor,
            Audio=self.menuAudio,
            Movement=self.menuMovement,
            Eyetracking=self.menuEyetracking
        )

        for k, v in get_all_analyses().items():
            inst = v()
            if inst.menu not in analysis_menues:
                analysis_menues[inst.menu] = self.menuAnalysis.addMenu(inst.menu)
            a = analysis_menues[inst.menu].addAction(inst.name)
            a.triggered.connect(partial(self.analysis_triggered, v()))

        if is_vian_light():
            for k, v in analysis_menues.items():
                v.menuAction().setVisible(False)

        self.actionColormetry.triggered.connect(self.toggle_colormetry)
        self.actionClearColormetry.triggered.connect(self.clear_colormetry)

        self.actionStart_AudioExtraction.triggered.connect(partial(self.audio_handler.extract))

        self.actionBrowserVisualizations.triggered.connect(partial(self.on_browser_visualization))
        self.actionProjectSummary.triggered.connect(partial(self.on_project_summary))

        # Keras is optional, if available create Actions
        if KERAS_AVAILABLE:
            self.actionSemanticSegmentation = self.menuAnalysis.addAction("Semantic Segmentation")
            self.actionSemanticSegmentation.triggered.connect(partial(self.analysis_triggered, SemanticSegmentationAnalysis()))

        self.actionSave_Perspective.triggered.connect(self.on_save_custom_perspective)
        self.actionLoad_Perspective.triggered.connect(self.on_load_custom_perspective)
        self.actionDocumentation.triggered.connect(self.open_documentation)


        self.actionPlay_Pause.triggered.connect(self.player.play_pause)
        self.actionFrame_Forward.triggered.connect(partial(self.player.frame_step, False))
        self.actionFrame_Backward.triggered.connect(partial(self.player.frame_step, True))
        self.actionSetMovie.triggered.connect(self.on_set_movie_path)
        self.actionReload_Movie.triggered.connect(self.on_reload_movie)
        self.actionClearRecent.triggered.connect(self.clear_recent)
        self.actionSet_Letterbox.triggered.connect(self.on_set_letterbox)

        self.audio_handler.audioExtractingStarted.connect(partial(self.set_audio_extracting, True))
        self.audio_handler.audioExtractingProgress.connect(self.set_audio_extracting_progress)
        self.audio_handler.audioExtractingEnded.connect(partial(self.set_audio_extracting, False))

        self.onMultiExperimentChanged.connect(self.outliner.on_multi_experiment_changed)
        self.onMultiExperimentChanged.connect(self.experiment_dock.experiment_editor.on_multi_experiment_changed)
        self.onMultiExperimentChanged.connect(self.vocabulary_matrix.on_multi_experiment_changed)
        self.onMultiExperimentChanged.emit(self.settings.MULTI_EXPERIMENTS)

        self.settings.apply_dock_widgets_settings(self.dock_widgets)

        qApp.focusWindowChanged.connect(self.on_application_lost_focus)
        self.i_project_notify_reciever = [self.player,
                                    self.drawing_overlay,
                                    self.screenshots_manager_dock,
                                    self.screenshots_manager,
                                    self.outliner,
                                    self.timeline.timeline,
                                    self.inspector,
                                    self.history_view,
                                    self.node_editor_dock.node_editor,
                                    self.vocabulary_manager,
                                    self.vocabulary_matrix,
                                    # self.numpy_data_manager,
                                    # self.project_streamer,
                                    self.analysis_results_widget,
                                    self.annotation_options,
                                    self.experiment_dock.experiment_editor,
                                    # self.corpus_client,
                                    self.colorimetry_live,
                                    self.query_widget,
                                    self.worker_manager,
                                    self.corpus_client_toolbar,
                                    self.flask_server
                                          ]

        self.menus_list = [
            self.menuFile,
            self.menuHelp,
            self.menuEdit,
            self.menuWindows,
            self.menuPlayer,
            self.menuCreate,
            self.menuAnalysis,
            self.menuTools
        ]

        # Autosave
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.on_save_project, False)
        self.update_autosave_timer(do_start=False)

        self.time_update_interval = 50
        self.update_timer = QtCore.QTimer()
        self.update_timer.setTimerType(Qt.PreciseTimer)
        self.update_timer.setInterval(self.time_update_interval)
        self.update_timer.timeout.connect(self.signal_timestep_update)

        self.time = 0
        self.time_counter = 0
        self.clock_synchronize_step = 100
        self.last_segment_index = 0

        self.player.movieOpened.connect(self.on_movie_opened, QtCore.Qt.QueuedConnection)
        self.player.started.connect(self.start_update_timer, QtCore.Qt.QueuedConnection)
        self.player.stopped.connect(self.update_timer.stop, QtCore.Qt.QueuedConnection)
        self.player.timeChanged.connect(self.dispatch_on_timestep_update, QtCore.Qt.AutoConnection)
        self.onMovieOpened.connect(self.audio_handler.project_changed)

        self.player.started.connect(partial(self.frame_update_worker.set_opencv_frame, False))
        self.player.stopped.connect(self.on_pause)

        self.player.started.connect(partial(self.drawing_overlay.on_opencv_frame_visibilty_changed, False))
        self.player.started.connect(partial(self.drawing_overlay.on_opencv_frame_visibilty_changed, True))

        self.drawing_overlay.onSourceChanged.connect(self.source_status.on_source_changed)
        self.onOpenCVFrameVisibilityChanged.connect(self.on_frame_source_changed)
        self.dispatch_on_changed()

        self.frame_update_worker.signals.onColormetryUpdate.connect(self.colorimetry_live.update_timestep)
        self.player_dock_widget.onSpacialFrequencyChanged.connect(self.frame_update_worker.toggle_spacial_frequency)

        self.onProjectClosed.connect(self.vian_event_handler.on_close)
        self.vian_event_handler.onException.connect(self.script_editor.print_exception)
        self.vian_event_handler.onCurrentPipelineChanged.connect(self.pipeline_toolbar.on_current_pipeline_changed)
        self.vian_event_handler.onCurrentPipelineChanged.connect(self.pipeline_widget.on_pipeline_loaded)
        self.vian_event_handler.onLockPipelineGUIForLoading.connect(partial(self.pipeline_toolbar.setEnabled, False))
        self.vian_event_handler.onReleasePipelineGUIAfterLoading.connect(partial(self.pipeline_toolbar.setEnabled, True))
        self.vian_event_handler.onLockPipelineGUIForLoading.connect(partial(self.pipeline_widget.set_is_loading, True))
        self.vian_event_handler.onReleasePipelineGUIAfterLoading.connect(partial(self.pipeline_widget.set_is_loading, False))

        self.pipeline_widget.pipeline.onToComputeChanged.connect(self.vian_event_handler.to_compute_changed)
        self.pipeline_widget.pipeline.onToComputeChanged.connect(self.pipeline_toolbar.set_to_compute)
        self.pipeline_widget.pipeline.onPipelineActivated.connect(self.vian_event_handler.set_current_pipeline)
        self.pipeline_widget.pipeline.onPipelineFinalize.connect(self.vian_event_handler.run_on_finalize_event)
        self.pipeline_widget.pipeline.onRunAnalysis.connect(self.on_start_analysis)
        self.pipeline_widget.pipeline.onProgress.connect(self.pipeline_toolbar.progress_widget.on_progress)

        self.pipeline_toolbar.onToComputeChanged.connect(self.pipeline_widget.pipeline.set_to_compute)
        self.pipeline_toolbar.runAll.connect(self.pipeline_widget.pipeline.run_all)

        self.corpus_widget.onCorpusChanged.connect(self.outliner.on_corpus_loaded)
        self.corpus_client_toolbar.onRunAnalysis.connect(self.on_start_analysis)

        self.update_recent_menu()


        self.player_controls.setState(False)

        self.source_status.on_source_changed(self.settings.OPENCV_PER_FRAME)

        self.project.undo_manager.clear()
        self.close_project()

        query_initial(WebAppCorpusInterface())
        self.show()
        self.on_multi_experiment_changed(self.settings.MULTI_EXPERIMENTS)
        self.on_pipeline_settings_changed()

        self.switch_perspective(Perspective.Segmentation)
        loading_screen.hide()
        self.setWindowState(Qt.WindowMaximized)
        self.settings.apply_ui_settings()

        # self.set_overlay_visibility(False)
        # This can be used for a oneshot forced command.
        force_file_path = os.path.abspath("install/force.txt")
        if os.path.isfile(force_file_path):
            try:
                os.remove(force_file_path)
                self.settings.GRID_SIZE = 1
                self.settings.store(self.dock_widgets)
                self.show_welcome()
            except Exception as e:
                log_error(e)

        if self.settings.SHOW_WELCOME:
            self.show_welcome()

        if self.settings.CONTRIBUTOR is None:
            self.show_first_start()
        else:
            try:
                log_info("Contributor:", self.settings.CONTRIBUTOR.full_name)
                log_info("Contributor:", self.settings.CONTRIBUTOR.email)
            except:
                pass
        if file is not None:
            self.load_project(file)

    def toggle_colormetry(self):
        log_debug("toggle colormetry", self.project.movie_descriptor.fps / 2)
        if self.colormetry_running is False:
            job = ColormetryJob2(int(self.project.movie_descriptor.fps / 2), self, self.settings.PROCESSING_WIDTH)
            args = job.prepare(self.project)
            self.actionColormetry.setText("Pause Colormetry")
            worker = MinimalThreadWorker(job.run_concurrent, args, True)
            worker.signals.callback.connect(self.on_colormetry_push_back)
            worker.signals.finished.connect(self.on_colormetry_finished)
            self.abortAllConcurrentThreads.connect(job.abort)
            self.thread_pool.start(worker, QThread.HighPriority)
            self.colormetry_job = job
            self.colormetry_running = True
        else:
            self.actionColormetry.setText("Start Colormetry")
            self.colormetry_job.abort()
            self.colormetry_running = False

    def on_colormetry_push_back(self, data):
        if self.project is not None and self.project.colormetry_analysis is not None:
            self.project.colormetry_analysis.append_data(data[0])
            self.timeline.timeline.set_colormetry_progress(data[1])

    def on_colormetry_finished(self, res):
        try:
            self.project.colormetry_analysis.check_finished()
            if self.project.colormetry_analysis.has_finished:
                self.timeline.timeline.set_colormetry_progress(1.0)
                log_debug(self.project.colormetry_analysis.resolution)
                res = self.project.colormetry_analysis.resolution
                fps = self.project.movie_descriptor.fps
                ms_to_idx = 1000 / (fps / res)
                log_debug(ms_to_idx, fps, res)
                self.timeline.timeline.add_visualization(
                    TimelineDataset("Colorimetry: Luminance",
                         self.project.hdf5_manager.get_colorimetry_feat()[:,0],
                         ms_to_idx=ms_to_idx,
                         vis_type=TimelineDataset.VIS_TYPE_LINE, vis_color=QColor(255, 166, 0)))
                lch = lab_to_lch(self.project.hdf5_manager.get_colorimetry_feat()[:, :3], human_readable=True)
                self.timeline.timeline.add_visualization(
                    TimelineDataset("Colorimetry: Chroma",
                                    lch[:,1],
                                    ms_to_idx=ms_to_idx,
                                    vis_type=TimelineDataset.VIS_TYPE_LINE, vis_color=QColor(188, 80, 144)))

                self.timeline.timeline.add_visualization(
                    TimelineDataset("Colorimetry: Hue",
                                    lch[:,2],
                                    ms_to_idx=ms_to_idx,
                                    vis_type=TimelineDataset.VIS_TYPE_LINE,  vis_color=QColor(47, 75, 124)))


        except Exception as e:
            log_error("Exception in MainWindow.on_colormetry_finished(): ", str(e))

    def set_audio_extracting_progress(self, flt):
        self.concurrent_task_viewer.update_progress("audio-extraction-task", flt)

    def set_audio_extracting(self, state):
        if state:
            self.concurrent_task_viewer.add_task("audio-extraction-task", "Audio Extracion", None, job = None)
            self.actionColormetry.setText("Start Colorimetry (blocked)")
            self.actionClearColormetry.setText("Clear Colorimetry (blocked)")
            self.actionColormetry.setEnabled(False)
            self.actionClearColormetry.setEnabled(False)
        else:
            self.concurrent_task_viewer.remove_task("audio-extraction-task")
            self.actionColormetry.setText("Start Colorimetry")
            self.actionClearColormetry.setText("Clear Colorimetry")
            self.actionColormetry.setEnabled(True)
            self.actionClearColormetry.setEnabled(True)

    def clear_colormetry(self):
        if self.project is not None:
            if self.colormetry_job is not None:
                self.colormetry_running = True
                self.toggle_colormetry()
            if self.project.colormetry_analysis is not None:
                self.project.colormetry_analysis.clear()
            self.timeline.timeline.set_colormetry_progress(0.0)

    def on_copy(self):
        if self.project is not None:
            self.clipboard_data = self.project.selected
        log_debug("Copy:", self.clipboard_data)

    def on_paste(self):
        log_debug("Paste:", self.clipboard_data, self.project, len(self.clipboard_data))
        if self.project is not None and len(self.clipboard_data) > 0:
            for s in self.clipboard_data:
                s.copy_event(self.project.selected[0])

    def on_pause(self):
        if self.settings.OPENCV_PER_FRAME != ALWAYS_VLC:
            self.frame_update_worker.set_opencv_frame(True)
            self.onUpdateFrame.emit(self.player.get_media_time(), self.player.get_frame_pos_by_time(self.player.get_media_time()))
            self.check_overlay_visibility()

    #region WidgetCreation

    def show_welcome(self):
        open_web_browser("https://www.vian.app/static/manual/whats_new/latest.html")
        self.settings.SHOW_WELCOME = False
        self.settings.store(self.dock_widgets)

    def show_first_start(self):
        dialog = DialogFirstStart(self)
        dialog.raise_()

    def start_update_timer(self):
        self.time = self.player.get_media_time()
        self.time_counter = 0
        self.update_timer.start()
        self.timeline.update()

    def create_widget_player_controls(self):
        if self.player_controls is None:
            self.player_controls = PlayerControls(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.player_controls, Qt.Vertical)
        else:
            if not self.player_controls.visibleRegion().isEmpty():
                self.player_controls.hide()
            else:
                self.player_controls.show()
                self.player_controls.raise_()
                self.player_controls.activateWindow()

    def create_widget_elan_status(self):
        if self.elan_status is None:
            self.source_status = StatusVideoSource(self)
            self.elan_status = StatusBar(self)
            self.output_line = OutputLine(self)
            self.progress_bar = StatusProgressBar(self)

            self.statusBar().addWidget(self.source_status)
            self.statusBar().addPermanentWidget(self.output_line)
            self.statusBar().addPermanentWidget(self.progress_bar)
            self.statusBar().addPermanentWidget(self.elan_status)
            self.statusBar().setFixedHeight(45)

    def create_annotation_dock(self):
        if self.annotation_options is None:
            self.annotation_options = AnnotationOptionsDock(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.annotation_options, Qt.Horizontal)
        else:
            if not self.annotation_options.visibleRegion().isEmpty():
                self.annotation_options.hide()
            else:
                self.annotation_options.show()
                self.annotation_options.raise_()
                self.annotation_options.activateWindow()

    def create_widget_video_player(self):
        if self.player_dock_widget is None:
            self.player_dock_widget = PlayerDockWidget(self)
            self.player_dock_widget.set_player(self.player)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.player_dock_widget, Qt.Horizontal)

        else:
            if not self.player_dock_widget.visibleRegion().isEmpty():
                self.player_dock_widget.hide()
            else:
                self.player_dock_widget.show()
                self.player_dock_widget.raise_()
                self.player_dock_widget.activateWindow()
        if self.drawing_overlay is not None:
            self.check_overlay_visibility()

    def create_annotation_toolbar(self):
        if self.annotation_toolbar is None:
            self.annotation_toolbar = AnnotationToolbar(self, self.drawing_overlay)
            self.addToolBar(self.annotation_toolbar)
        else:
            self.annotation_toolbar.show()

    def create_inspector(self):
        if self.inspector is None:
            self.inspector = Inspector(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
        else:
            if not self.inspector.visibleRegion().isEmpty():
                self.inspector.hide()
            else:
                self.inspector.show()
                self.inspector.raise_()
                self.inspector.activateWindow()

    def create_concurrent_task_viewer(self):
        if self.concurrent_task_viewer is None:
            self.concurrent_task_viewer = ConcurrentTaskDock(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.concurrent_task_viewer)
        else:
            if not self.concurrent_task_viewer.visibleRegion().isEmpty():
                self.concurrent_task_viewer.hide()
            else:
                self.concurrent_task_viewer.show()
                self.concurrent_task_viewer.raise_()
                self.concurrent_task_viewer.activateWindow()

    def create_history_view(self):
        if self.history_view is None:
            self.history_view = HistoryView(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.history_view)
        else:
            if not self.history_view.visibleRegion().isEmpty():
                self.history_view.hide()
            else:
                self.history_view.show()

    def create_screenshots_toolbar(self):
        if self.screenshot_toolbar is None:
            self.screenshot_toolbar = ScreenshotsToolbar(self, self.screenshots_manager)
            self.addToolBar(self.screenshot_toolbar)
            #self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.screenshot_toolbar)
        else:
            self.screenshot_toolbar.show()

    def create_perspectives_manager(self):
        if self.perspective_manager is None:
            self.perspective_manager = PerspectiveManager(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.perspective_manager, Qt.Horizontal)
            self.perspective_manager.hide()
        else:
            self.perspective_manager.show()
            self.perspective_manager.raise_()
            self.perspective_manager.activateWindow()

    def create_outliner(self):
        if self.outliner is None:
            self.outliner = Outliner(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.outliner)
        else:
            if not self.outliner.visibleRegion().isEmpty():
                self.outliner.hide()
            else:
                self.outliner.show()
                self.outliner.raise_()
                self.outliner.activateWindow()

    def create_timeline(self):
        if self.timeline is None:
            self.timeline = TimelineContainer(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.timeline, QtCore.Qt.Vertical)
            # self.on_movie_updated()
        else:
            if not self.timeline.visibleRegion().isEmpty():
                self.timeline.hide()
            else:
                self.timeline.show()
                self.timeline.raise_()
                self.timeline.activateWindow()

    def create_screenshot_manager(self):
        if self.screenshots_manager is None:
            self.screenshots_manager = ScreenshotsManagerWidget(self, parent=None)
        else:
            self.screenshots_manager.activateWindow()

    def create_screenshot_manager_dock_widget(self):
        if self.screenshots_manager_dock is None:
            self.screenshots_manager_dock = ScreenshotsManagerDockWidget(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.screenshots_manager_dock, QtCore.Qt.Horizontal)
            self.screenshots_manager_dock.set_manager(self.screenshots_manager)
        else:
            if not self.screenshots_manager_dock.visibleRegion().isEmpty():
                self.screenshots_manager_dock.hide()
            else:
                self.screenshots_manager_dock.show()
                self.screenshots_manager_dock.raise_()
                self.screenshots_manager_dock.activateWindow()

    def create_node_editor(self):
        if self.node_editor_dock is None:
            self.node_editor_dock = NodeEditorDock(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.node_editor_dock, QtCore.Qt.Horizontal)
        else:
            self.node_editor_dock.show()
            self.node_editor_dock.activateWindow()

    def create_node_editor_results(self):
        if self.node_editor_results is None:
            self.node_editor_results = NodeEditorResults(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.node_editor_results, QtCore.Qt.Vertical)
        else:
            self.node_editor_results.show()
            self.node_editor_results.activateWindow()

    def create_vocabulary_manager(self):
        if self.vocabulary_manager is None:
            self.vocabulary_manager = VocabularyManager(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.vocabulary_manager, QtCore.Qt.Vertical)
        else:
            if not self.vocabulary_manager.visibleRegion().isEmpty():
                self.vocabulary_manager.hide()
            else:
                self.vocabulary_manager.show()
                self.vocabulary_manager.raise_()
                self.vocabulary_manager.activateWindow()

    def create_experiment_editor(self):
        if self.experiment_dock is None:
            self.experiment_dock = ExperimentEditorDock(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.experiment_dock, QtCore.Qt.Vertical)
        else:
            if not self.experiment_dock.visibleRegion().isEmpty():
                self.experiment_dock.hide()
            else:
                self.experiment_dock.show()
                self.experiment_dock.raise_()
                self.experiment_dock.activateWindow()

    def create_vocabulary_matrix(self):
        if self.vocabulary_matrix is None:
            self.vocabulary_matrix = ClassificationWindow(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.vocabulary_matrix, QtCore.Qt.Vertical)
        else:
            if not self.vocabulary_matrix.visibleRegion().isEmpty():
                self.vocabulary_matrix.hide()
            else:
                self.vocabulary_matrix.show()
                self.vocabulary_matrix.raise_()
                self.vocabulary_matrix.activateWindow()

    def create_query_widget(self):
        if self.query_widget is None:
            self.query_widget = ClassificationWindow(self, behaviour="query")
            self.tabifyDockWidget(self.player_dock_widget, self.query_widget)
        else:
            if not self.query_widget.visibleRegion().isEmpty():
                self.query_widget.hide()
            else:
                self.query_widget.show()
                self.query_widget.raise_()
                self.query_widget.activateWindow()

    def create_pipeline_widget(self):
        if self.pipeline_widget is None:
            self.pipeline_widget = PipelineDock(self, self.vian_event_handler)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.pipeline_widget)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.pipeline_widget)
            if self.settings.USE_PIPELINES is False:
                self.pipeline_widget.hide()
        else:
            if not self.pipeline_widget.visibleRegion().isEmpty() or self.settings.USE_PIPELINES:
                self.pipeline_widget.hide()
            else:
                self.pipeline_widget.show()
                self.pipeline_widget.raise_()
                self.pipeline_widget.activateWindow()

    def create_analysis_results_widget(self):
        if self.analysis_results_widget is None:
            self.analysis_results_widget_dock = AnalysisResultsDock(self)
            self.analysis_results_widget = AnalysisResultsWidget(self.analysis_results_widget_dock, self)
            self.analysis_results_widget_dock.set_analysis_widget(self.analysis_results_widget)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.analysis_results_widget_dock, Qt.Vertical)
        else:
            if not self.analysis_results_widget_dock.visibleRegion().isEmpty():
                self.analysis_results_widget_dock.hide()
            else:
                self.analysis_results_widget_dock.show()
                self.analysis_results_widget_dock.raise_()
                self.analysis_results_widget_dock.activateWindow()

    def create_analysis_results_widget2(self):
        if self.web_view is None:
            self.web_view = FlaskWebWidget(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.web_view, Qt.Vertical)
        else:
            if not self.web_view.visibleRegion().isEmpty():
                self.web_view.hide()
            else:
                self.web_view.show()
                self.web_view.raise_()
                self.web_view.activateWindow()


    def create_colorimetry_live(self):
        if self.colorimetry_live is None:
            self.colorimetry_live = ColorimetryLiveWidget(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.colorimetry_live, Qt.Vertical)
        else:
            if not self.colorimetry_live.visibleRegion().isEmpty():
                self.colorimetry_live.hide()
            else:
                self.colorimetry_live.show()
                self.colorimetry_live.raise_()
                self.colorimetry_live.activateWindow()

    def create_corpus_widget(self):
        if self.corpus_widget is None:
            self.corpus_widget = CorpusDockWidget(self)
            self.onSave.connect(self.corpus_widget.on_save_triggered)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.corpus_widget, Qt.Vertical)
            # self.corpus_widget.hide()
        else:
            if not self.corpus_widget.visibleRegion().isEmpty():
                self.corpus_widget.hide()
            else:
                self.corpus_widget.show()
                self.corpus_widget.raise_()
                self.corpus_widget.activateWindow()

    def create_corpus_client_toolbar(self):
        if self.corpus_client_toolbar is None:
            self.corpus_client_toolbar = WebAppCorpusDock(self, self.corpus_client)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.corpus_client_toolbar)
            self.corpus_client_toolbar.show()

        else:
            if not self.corpus_client_toolbar.visibleRegion().isEmpty():
                self.corpus_client_toolbar.hide()
            else:
                self.corpus_client_toolbar.show()
                self.corpus_client_toolbar.raise_()
                self.corpus_client_toolbar.activateWindow()

    def create_summary_dock(self):
        if self.summary_dock is None:
            self.summary_dock = FlaskWebWidget(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.summary_dock, Qt.Vertical)

            self.summary_dock.hide()
        else:
            if not self.summary_dock.visibleRegion().isEmpty():
                self.summary_dock.hide()
            else:
                self.summary_dock.show()
                self.summary_dock.raise_()
                self.summary_dock.activateWindow()
    #endregion

    #region QEvent Overrides
    def moveEvent(self, *args, **kwargs):
        QtWidgets.QMainWindow.moveEvent(self, *args, **kwargs)
        if self.drawing_overlay is not None and self.drawing_overlay.isVisible():
            self.drawing_overlay.synchronize_transforms()
        self.update()

    def closeEvent(self, a0: QtGui.QCloseEvent):
        exit = self.on_exit()
        if not exit:
            a0.ignore()
            super(MainWindow, self).closeEvent(a0)

    def resizeEvent(self, *args, **kwargs):
        QtWidgets.QMainWindow.resizeEvent(self, *args, **kwargs)
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.screenshots_manager.ctrl_is_pressed = True
            self.timeline.timeline.is_scaling = True
        elif event.key() == Qt.Key_Shift:
            pass

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.screenshots_manager.ctrl_is_pressed = False
            self.timeline.timeline.is_scaling = False
        elif event.key() == Qt.Key_Shift:
            pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            file_extension = str(event.mimeData().urls()[0].toLocalFile()).split(".").pop()
            if file_extension in ["eaf", "png", "jpg"]:
                event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            file_extension = str(event.mimeData().urls()[0]).split(".").pop()
            files = event.mimeData().urls()
            if "eaf" in file_extension:
                log_debug("Importing ELAN Project")
                self.import_elan_project(str(event.mimeData().urls()[0]), False)
            elif "png" in file_extension or "jpg" in file_extension:
                res_files = []
                for f in files:
                    if "png" in str(f).split(".").pop() or "jpg" in str(f).split(".").pop():
                        res_files.append(f.toLocalFile())
                self.import_screenshots(res_files)

    def mousePressEvent(self, event):
        self.close_drawing_editor()
        self.update()

    def paintEvent(self, *args, **kwargs):
        super(MainWindow, self).paintEvent(*args, **kwargs)

    def update(self, *__args):
        super(MainWindow, self).update(*__args)

    #endregion

    #region MainWindow Event Handlers

    @pyqtSlot(object)
    def on_vocabulary_library_changed(self, library):
        if self.project is not None:
            self.project.sync_with_library(library)

    def on_pipeline_settings_changed(self):
        if self.settings.USE_PIPELINES:
            self.pipeline_widget.show()
            self.pipeline_toolbar.show()
        else:
            self.pipeline_widget.hide()
            self.pipeline_toolbar.hide()

    @pyqtSlot(float, str)
    def on_progress_popup(self, value, str):
        try:
            if self.progress_popup is None:
                self.progress_popup = EProgressPopup(self)
                self.progress_popup.show()
            self.progress_popup.on_progress(value, str)
            if value == 1.0:
                self.progress_popup.close()
                self.progress_popup = None
        except:
            pass

    def open_recent(self, index):
        path = self.settings.recent_files_path[index]
        if os.path.isfile(path):
            self.load_project(path)
        else:
            try:
                self.settings.remove_from_recent_files(path)
                self.update_recent_menu()
            except:
                pass
            self.print_message("Project not Found", "Red")

    def cleanup_recent(self):
        self.settings.clean_up_recent()
        self.update_recent_menu()

    def on_compare(self):
        if self.project is None:
            return
        from vian.core.visualization.bokeh_timeline import compare_with_project
        f2 = QFileDialog.getOpenFileName(self, filter="*.eext")[0]
        compare_with_project(self.project, f2)


    def clear_recent(self):
        self.settings.recent_files_name = []
        self.settings.recent_files_path = []
        self.update_recent_menu()

    def update_recent_menu(self):
        for r in self.menuRecently_Opened.actions():
            if r.text() not in ["Clean Up", "Clear List"]:
                self.menuRecently_Opened.removeAction(r)

        self.menuRecently_Opened.addSeparator()
        try:
            for i, recent in enumerate(self.settings.recent_files_name):
                if recent is None:
                    continue
                action = self.menuRecently_Opened.addAction(recent)
                action.triggered.connect(partial(self.open_recent, i))
        except:
            self.settings.recent_files_path = []
            self.settings.recent_files_name = []

    def eval_class(self, class_name):
        try:
            return eval(class_name)
        except:
            try:
                for c in self.extension_list.get_importables():
                    if c[0] == class_name:
                        module = importlib.import_module(c[1])
                        return getattr(module, class_name)
            except Exception as e:
                log_error(e)

    def open_preferences(self):
        dialog = DialogPreferences(self)
        dialog.onSettingsChanged.connect(self.frame_update_worker.on_settings_changed)
        dialog.show()

    def on_movie_opened(self):
        # TODO What is this for??
        self.player_controls.on_play()

    def on_remove_all_analyses(self):
        if self.project is not None:
            to_remove = [a for a in self.project.analysis]
            print(to_remove)
            for a in to_remove:
                self.project.remove_analysis(a)

    def on_exit(self):
        self.set_overlay_visibility(False)
        if self.project is not None and self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project(sync=True)
            elif answer == QMessageBox.No:
                pass
            else:
                self.set_overlay_visibility(True)
                return False

        self.dispatch_on_closed()
        self.settings.store(self.dock_widgets)

        log_info("Closing Frame Update")
        self.frame_update_thread.quit()
        log_info("Closing flask_server_thread")
        if not is_vian_light():
            self.flask_server_thread.quit()
            log_info("Closing audio_handler_thread")
            self.audio_handler_thread.quit()

        log_info("Closing vian_event_handler_thread")
        self.vian_event_handler_thread.quit()

        log_info("Closing player")
        self.player.on_closed()

        log_info("Closing abortAllConcurrentThreads")
        self.abortAllConcurrentThreads.emit()

        if PROFILE:
            self.profiler.disable()
            self.profiler.dump_stats("Profile.prof")

        QCoreApplication.quit()
        return True

    def on_undo(self):
        self.project.undo_manager.undo()

    def on_redo(self):
        self.project.undo_manager.redo()

    def on_delete(self):
        self.project.inhibit_dispatch = True
        to_delete = self.project.selected
        try:
            for d in to_delete:
                d.save_delete()
        except Exception as e:
            log_error(e)
        self.project.inhibit_dispatch = False
        self.dispatch_on_changed()

    def update_overlay(self):
        if self.drawing_overlay is not None and self.drawing_overlay.isVisible():
            self.drawing_overlay.update()

    def on_new_segment(self):
        self.timeline.timeline.create_segment(None)

    def on_screenshot(self):
        time = self.player.get_media_time()
        
        frame_pos = self.player.get_frame_pos_by_time(time)

        annotation_dicts = []
        for l in self.project.annotation_layers:
            if l.is_visible:
                for a in l.annotations:
                    a_dict = a.serialize()
                    annotation_dicts.append(a_dict)

        job = CreateScreenshotJob([frame_pos, self.project.movie_descriptor.get_movie_path(), annotation_dicts, time])
        self.run_job_concurrent(job)

    def get_frame(self, time):
        if time <= 0:
            time = 1
        fps = self.player.get_fps()
        path = self.player.movie_path.replace("file:///", "")
        pos = float(time) / 1000 * fps
        vid = cv2.VideoCapture(path)
        vid.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = vid.read()

        return frame, pos

    def on_screenshot_finished(self, shot):
        try:
            if self.project.has_segmentation():
                segm = self.project.get_main_segmentation()
                if len(segm.segments) > 0:
                    shot.update_scene_id(self.project.get_main_segmentation())
            else:
                self.print_message("Segmentation could not be assigned, no Segmentation has been found", color="red")
        except RuntimeError as e:
            self.print_message("Segmentation could not be assigned", color="red")

        self.project.add_screenshot(shot)
        self.outliner.add_screenshot(shot)
        self.screenshots_manager.update_manager()

        # self.screenshots_editor.set_current_screenshot(shot)
        # self.screenshots_editor.raise_()

        self.print_message("Screenshot added", "green")

    def worker_finished(self, tpl):
        self.concurrent_task_viewer.remove_task(tpl[0])
        self.print_message(tpl[1], "green")
        self.progress_bar.on_finished()

    def worker_error(self, error):
        log_error("*********ERROR**IN**WORKER***********")
        log_error(error)
        log_error("*************************************")

    def worker_progress(self, tpl):
        # self.progress_bar.set_progress(float)
        total = self.concurrent_task_viewer.update_progress(tpl[0],tpl[1])
        self.progress_bar.set_progress(float(total))

    def worker_abort(self, int):
        self.concurrent_task_viewer.remove_task(int)
        self.print_message("Task:" + str(int) + " aborted.", "orange")
        self.progress_bar.on_finished()

    def run_job_concurrent(self, job):
        job.prepare(self.project)
        worker = Worker(job.run_concurrent, self, self.on_job_concurrent_result, job.args, msg_finished=str(job.__class__.__name__) + " finished", concurrent_job=job)
        self.abortAllConcurrentThreads.connect(job.abort)
        self.start_worker(worker, "Job")

    def on_job_concurrent_result(self, result):
        res = result[0]
        job = result[1]
        self.allow_dispatch_on_change = False

        if not job.aborted:
            job.modify_project(project=self.project, result=res, main_window = self)

        self.allow_dispatch_on_change = True
        self.dispatch_on_changed()
        if isinstance(job, LoadScreenshotsJob):
            self.web_view.reload()
        # print(self.thread_pool.)
        # progress.deleteLater()

    def scale_screenshots(self, scale = 0.1):
        job = ScreenshotStreamingJob([self.project.screenshots, scale])
        self.run_job_concurrent(job)

    def on_key_annotation(self):
        selected = self.project.get_selected([ANNOTATION])
        for s in selected:
            self.key_annotation(s)

    def key_annotation(self, s):
        time = self.player.get_media_time()
        pos = tuple2point(s.get_position())
        s.add_key(time, [pos.x(), pos.y()])
        self.print_message("Key added", "Green")
        self.dispatch_on_changed([self.drawing_overlay, self.timeline.timeline])

    def on_new_segmentation(self):
        self.project.create_segmentation("Segmentation")

    def on_new_annotation_layer(self):
        curr_time = self.player.get_media_time()
        self.project.create_annotation_layer("New Layer", curr_time, curr_time + 10000)

    def on_backup(self):
        answer = QMessageBox.question(self, "Backup", "Do you want to store the Backup into the default Directory?",
                                      buttons=QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
        if answer == QMessageBox.No:
            path = QFileDialog.getExistingDirectory(self, caption="Select Directory to store Backup", directory = self.settings.DIR_ROOT)[0] + "/"
        elif answer == QMessageBox.Yes:
            path = self.settings.DIR_BACKUPS
        else:
            return

        if path is None or path == "":
            self.print_message("The Path: " + str(path) + " does not exist, please choose it manually.", "Orange")
            return

        filename = time.strftime("%Y_%m_%d_%H_%M_%S", time.gmtime(time.time()))+"_"+self.project.name + "_backup"
        try:
            log_debug(path + filename)
            zip_project(path + filename, self.project.folder)
            self.print_message("Backup sucessfully stored to: " + path + filename + ".zip", "Green")
        except Exception as e:
            self.print_message("Backup Failed", "Red")
            self.print_message(str(e), "Red")

    def on_search(self):
        self.search_window.show()
        self.search_window.resize(QSize(int(self.width() * 0.8), int(self.height() * 0.8)))
        self.search_window.move(QPoint(int(self.width() * 0.1), int(self.height() * 0.1)))

    def print_message(self, msg, color = "green"):
        self.output_line.print_message(msg, color)

    def default_dock_locations(self):
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.timeline, QtCore.Qt.Vertical)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.player_controls, QtCore.Qt.Vertical)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.screenshots_manager_dock, QtCore.Qt.Vertical)
        self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)

    def dummy_func(self, *args):
        pass

    def switch_perspective(self, perspective):
        log_debug("Switch Perspective", perspective)
        self.centralWidget().setParent(None)
        self.statusBar().show()

        self.hide_all_widgets()
        self.current_perspective = perspective
        self.elan_status.stage_selector.set_stage(perspective, False)

        self.default_dock_locations()

        central = QWidget(self)
        central.setFixedWidth(0)

        if perspective == Perspective.VideoPlayer:
            self.player_dock_widget.show()

        elif perspective == Perspective.Segmentation:
            self.timeline.show()
            self.player_controls.show()
            self.screenshots_manager_dock.show()
            self.player_dock_widget.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner, Qt.Horizontal)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.player_dock_widget, Qt.Horizontal)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.tabifyDockWidget(self.inspector, self.history_view)
            self.tabifyDockWidget(self.inspector, self.concurrent_task_viewer)

            self.addDockWidget(Qt.RightDockWidgetArea, self.vocabulary_matrix)
            self.addDockWidget(Qt.RightDockWidgetArea, self.corpus_client_toolbar)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.colorimetry_live)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.corpus_client_toolbar)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.vocabulary_manager)
            if self.settings.USE_PIPELINES:
                self.tabifyDockWidget(self.screenshots_manager_dock, self.pipeline_widget)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.vocabulary_matrix)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.analysis_results_widget_dock)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.corpus_widget)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.experiment_dock)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.query_widget)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.web_view)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.summary_dock)
            

            if self.facial_identification_dock is not None:
                self.tabifyDockWidget(self.screenshots_manager_dock, self.facial_identification_dock)

            # self.screenshot_toolbar.show()
            self.screenshots_manager_dock.raise_()

        elif perspective == Perspective.Annotation:
            self.outliner.show()
            self.timeline.show()
            self.inspector.show()
            self.player_dock_widget.show()
            self.annotation_options.show()

            self.annotation_toolbar.show()

            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector)
            self.splitDockWidget(self.inspector, self.outliner, Qt.Vertical)
            self.tabifyDockWidget(self.inspector, self.annotation_options)
            self.screenshots_manager_dock.raise_()

        elif perspective == Perspective.ScreenshotsManager:
            self.screenshots_manager.update_manager()
            self.screenshots_manager_dock.show()
            self.inspector.show()
            self.outliner.show()

            self.screenshot_toolbar.show()

            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.splitDockWidget(self.inspector, self.outliner, Qt.Vertical)

        elif perspective == Perspective.Analyses:
            self.inspector.show()
            self.outliner.show()
            self.node_editor_results.show()
            self.node_editor_dock.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)

        elif perspective == Perspective.Results:
            self.inspector.show()
            self.outliner.show()

            self.analysis_results_widget_dock.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.analysis_results_widget_dock, Qt.Horizontal)
            self.splitDockWidget(self.outliner, self.inspector, Qt.Vertical)

        elif perspective == Perspective.Classification:

            self.timeline.show()
            self.screenshots_manager_dock.show()
            self.vocabulary_matrix.show()
            self.player_dock_widget.show()
            self.drawing_overlay.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.screenshots_manager_dock, Qt.Vertical)
            self.addDockWidget(Qt.RightDockWidgetArea, self.vocabulary_matrix)
            self.addDockWidget(Qt.RightDockWidgetArea, self.timeline, Qt.Vertical)

            # self.statusBar().hide()

        elif perspective == Perspective.ExperimentSetup:

            self.outliner.show()
            self.vocabulary_manager.show()
            # self.inspector.show()
            self.experiment_dock.show()
            if self.settings.USE_PIPELINES:
                self.pipeline_widget.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.experiment_dock)
            self.tabifyDockWidget(self.experiment_dock, self.pipeline_widget)
            self.tabifyDockWidget(self.experiment_dock, self.vocabulary_manager)
            # self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)


        elif perspective == Perspective.Query:
            self.timeline.show()
            self.screenshots_manager_dock.show()
            self.player_dock_widget.show()
            self.colorimetry_live.show()
            self.query_widget.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner, Qt.Horizontal)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.player_dock_widget, Qt.Horizontal)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.colorimetry_live)
            self.tabifyDockWidget(self.player_dock_widget, self.query_widget)
            if self.facial_identification_dock is not None:
                self.tabifyDockWidget(self.screenshots_manager_dock, self.facial_identification_dock)

            self.screenshot_toolbar.show()
            self.screenshots_manager_dock.raise_()

        # elif perspective == Perspective.CorpusVisualizer:
        #     self.corpus_visualizer_result_dock.show()
        #     self.corpus_visualizer_dock.show()
        #     self.addDockWidget(Qt.RightDockWidgetArea, self.corpus_visualizer_result_dock, Qt.Horizontal)
        #     self.addDockWidget(Qt.LeftDockWidgetArea, self.corpus_visualizer_dock, Qt.Horizontal)

        elif perspective == Perspective.WebApp:
            self.timeline.show()
            self.inspector.show()
            self.player_dock_widget.show()
            self.tabifyDockWidget(self.inspector, self.corpus_client_toolbar)
            self.corpus_client_toolbar.show()
            self.corpus_client_toolbar.raise_()

        self.setCentralWidget(central)

        self.centralWidget().show()
        # self.centralWidget().setBaseSize(size_central)

        self.check_overlay_visibility()
        self.set_default_dock_sizes(self.current_perspective)

    def hide_all_widgets(self):
        if self.annotation_toolbar.isVisible():
            self.annotation_toolbar.hide()
        if self.screenshot_toolbar.isVisible():
            self.screenshot_toolbar.hide()
        if self.corpus_client_toolbar.isVisible():
            self.corpus_client_toolbar.hide()

        # self.create_widget_video_player()
        self.query_widget.hide()
        self.drawing_overlay.hide()
        self.outliner.hide()
        self.perspective_manager.hide()
        self.inspector.hide()
        self.history_view.hide()
        self.concurrent_task_viewer.hide()
        self.node_editor_dock.hide()
        self.node_editor_results.hide()
        self.vocabulary_manager.hide()
        self.vocabulary_matrix.hide()
        self.analysis_results_widget_dock.hide()
        self.timeline.hide()
        self.pipeline_widget.hide()
        self.player_controls.hide()
        self.corpus_widget.hide()
        self.screenshots_manager_dock.hide()
        self.player_dock_widget.hide()
        self.annotation_options.hide()
        # self.corpus_visualizer_dock.hide()
        # self.corpus_visualizer_result_dock.hide()

        if self.facial_identification_dock is not None:
            self.facial_identification_dock.hide()

        self.experiment_dock.hide()

        self.colorimetry_live.hide()

    def set_default_dock_sizes(self, perspective):
        if perspective == Perspective.Segmentation:
            self.timeline.resize_dock(h=300)
            self.screenshots_manager_dock.resize_dock(w=self.width() / 2)

        elif perspective == Perspective.Annotation:
            self.timeline.resize_dock(h=300)

        elif perspective == Perspective.Classification:
            self.timeline.resize_dock(h=100)
            self.player_dock_widget.resize_dock(w=800, h=400)
            self.screenshots_manager_dock.resize_dock(h=self.height() / 2)
            self.player_dock_widget.resize_dock(h=self.height() / 2)

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow() == False and self.drawing_overlay.isActiveWindow()==False:
                self.drawing_overlay.hide()
                # self.set_darwin_player_visibility(False)
            else:
                if self.current_perspective == Perspective.Annotation:
                    self.drawing_overlay.show()
                    # self.set_darwin_player_visibility(True)

        super(MainWindow, self).changeEvent(event)

    def on_application_lost_focus(self, arg):
        if arg is None:
            self.application_in_focus = False
        else:
            self.application_in_focus = True

        self.check_overlay_visibility()
        # if arg is None or len(self.open_dialogs) != 0:
        #     self.set_overlay_visibility(False)
        # else:
        #     if self.current_perspective in[Perspective.SVGAnnotation, Perspective.Segmentation]:
        #         self.set_overlay_visibility(True)
        #         self.set_overlay_visibility(True)
        #         self.onOpenCVFrameVisibilityChanged.emit(True)
        #     else:
        #         self.set_overlay_visibility(False)
            # self.set_darwin_player_visibility(True)

    def on_set_letterbox(self):
        if self.project is not None:
            dialog = LetterBoxWidget(self, self)
            dialog.set_movie(self.project.movie_descriptor)
            dialog.show()
            dialog.view.fitInView(dialog.view.sceneRect(), Qt.KeepAspectRatio)

    def analysis_triggered(self, analysis:IAnalysisJob):
        analysis.max_width = self.settings.PROCESSING_WIDTH

        targets = []
        for sel in self.project.selected:
            if sel.get_type() in analysis.source_types:
                targets.append(sel)

        dialog = AnalysisDialog(self, analysis, targets)
        dialog.onAnalyse.connect(self.on_start_analysis)
        dialog.show()

    def on_start_analysis(self, from_dialog):
        analysis = from_dialog['analysis']
        targets = from_dialog['targets']
        parameters = from_dialog['parameters']
        class_objs = from_dialog['classification_objs']
        fps = self.player.get_fps()
        self.worker_manager.push(self.project, analysis, targets, parameters, fps, class_objs)

        # args = analysis.prepare(self.project, targets, parameters, fps, class_objs)
        #
        # if analysis.multiple_result:
        #     for arg in args:
        #         worker = Worker(analysis.process, self, self.analysis_result, arg,
        #                         msg_finished=analysis.name+ " Finished", target_id=None, i_analysis_job=analysis)
        #         self.start_worker(worker, analysis.get_name())
        # else:
        #     worker = Worker(analysis.process, self, self.analysis_result, args, msg_finished=analysis.name+ " Finished", target_id=None, i_analysis_job=analysis)
        #     self.start_worker(worker, analysis.get_name())

    def analysis_result(self, result):
        pass
        # analysis = result[1]
        # result = result[0]
        #
        # try:
        #     if isinstance(result, list):
        #         for r in result:
        #             analysis.modify_project(self.project, r, main_window = self)
        #             self.project.add_analysis(r, dispatch = False)
        #             r.unload_container()
        #     else:
        #         analysis.modify_project(self.project, result, main_window=self)
        #         self.project.add_analysis(result)
        #         result.unload_container()
        # except Exception as e:
        #     print("Exception in MainWindow.analysis_result", str(e))
        # self.project.dispatch_changed(item=self.project)
        #
        # # Let the Analysis Worker know to start the next analysis
        # self.onAnalysisIntegrated.emit()

    def on_classification_object_changed(self, cl_obj):
        self.project.set_active_classification_object(cl_obj)
        job = ClassificationObjectChangedJob(self.project, self.project.hdf5_manager, cl_obj, hdf5_cache=self.hdf5_cache)
        self.run_job_concurrent(job)

    def on_save_custom_perspective(self):
        setting = QSettings("UniversityOfZurich", "VIAN")
        setting.setValue("geometry", self.saveGeometry())
        setting.setValue("windowState", self.saveState())

    def on_load_custom_perspective(self):
        setting = QSettings("UniversityOfZurich", "VIAN")
        self.restoreGeometry(setting.value("geometry"))
        self.restoreState(setting.value("windowState"))

    def start_worker(self, worker, name = "New Task"):
        job = worker.concurrent_job
        if job is None:
            job = worker.i_analysis_job
        self.concurrent_task_viewer.add_task(worker.task_id, name, worker, job)
        self.thread_pool.start(worker)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def toggle_statusbar(self):
        if self.statusBar().isVisible():
            self.statusBar().hide()
        else:
            self.statusBar().show()

    def on_frame_source_changed(self, visibility):
        if visibility:
            if (self.current_perspective == Perspective.Segmentation or
                    self.current_perspective == Perspective.Annotation):
                self.check_overlay_visibility()

        else:
            if self.current_perspective == Perspective.Segmentation:
                self.check_overlay_visibility()

    def update_player_size(self):
        self.player.update()

    def open_documentation(self):
        webbrowser.open("https://www.vian.app/static/manual/index.html")

    def on_about(self):
        about = ""
        about += "Author:".ljust(12) + ", ".join(version.__author__)+ "\n"
        about += "Copyright:".ljust(12) + str(version.__copyright__) + "\n"
        about += "Version:".ljust(12) + str(version.__version__) + "\n"
        about += "Credits:".ljust(12) + ",\n".join(version.__credits__)+ "\n"
        QMessageBox.about(self, "About", about)

    def increase_playrate(self):
        self.player.set_rate(np.clip(self.player.get_rate() + 0.1, 0.1, 10))
        self.player_controls.update_rate()

    def decrease_playrate(self):
        self.player.set_rate(np.clip(self.player.get_rate() - 0.1, 0.1, 10))
        self.player_controls.update_rate()

    def on_create_experiment(self):
        print("Hello Experiment")
        if self.project is not None:
            self.project.create_experiment()

    def on_set_movie_path(self):
        if self.project is not None:
            path = parse_file_path(QFileDialog.getOpenFileName(self)[0])
            if os.path.isfile(path):
                self.project.movie_descriptor.set_movie_path(path)
                self.player.open_movie(path)
                self.dispatch_on_changed()

    def on_reload_movie(self):
        if self.project is not None:
            self.player.on_loaded(self.project)

    def on_export_screenshots(self):
        dialog = DialogScreenshotExporter(self, self.project)
        dialog.show()

    def on_facial_reconition(self):
        return

        if self.facial_identification_dock is None:
            self.facial_identification_dock.raise_()

    def on_export_colorimetry(self):
        if self.project is None:
            return
        p = QFileDialog.getSaveFileName(filter="*.csv", directory=self.project.export_dir)[0]
        try:
            self.project.export(ColorimetryExporter(), p)
        except Exception as e:
            log_error(e)

    def on_export_summary(self):
        if self.project is None:
            return
        p = QFileDialog.getSaveFileName(filter="*.html", caption="Select Save Path", directory=self.project.export_dir)[0]
        try:
            from vian.core.visualization.bokeh_timeline import generate_plot
            generate_plot(self.project, file_name=p)
            QMessageBox.information(self, "Summary Exported", "The Summary has been exported to {f}".format(f=p))
        except Exception as e:
            log_error(e)
    def on_export_vianwebapp(self):
        self.project.store_project(bake=True)

    def on_export_sequence_protocol(self):
        p = Path(QFileDialog.getSaveFileName(filter="*.csv *.pdf", caption="Select Save Path", directory=self.project.export_dir)[0])
        if ".csv" in p.suffixes:
            self.project.export(SequenceProtocolExporter(export_format="csv"), p)
        else:
            self.project.export(SequenceProtocolExporter(export_format="pdf"), p)

    def on_browser_visualization(self):
        webbrowser.open("http://127.0.0.1:{p}/screenshot_vis/".format(p=VIAN_PORT))

    def on_project_summary(self):
        self.summary_dock.set_url("http://127.0.0.1:{p}/summary/".format(p=VIAN_PORT))
        self.summary_dock.setWindowTitle("Project Summary")

        # Just show it
        self.create_summary_dock()

    def check_update(self):
        version, id = get_vian_version()
        has_update = version_check(version, self.version)
        if has_update:
            QMessageBox.information(self, "New Version available", "A new VIAN version is available.\n"
                                                                   "Go to https://www.vian.app/vian to "
                                                                   "update to download the newest version.\n"
                                                                   "Your Version: " + self.version + "\n"
                                                                   "Newest Version: " + str(version))
        else:
            QMessageBox.information(self, "All set", "You have the newest version of VIAN!\n"
                                                     "Your Version: " + self.version)

    # endregion

    #region Project Management
    def action_new_project(self):
        self.on_new_project()

    def on_new_project(self, movie_path = "", add_to_current_corpus = False):
        # self.set_darwin_player_visibility(False)
        self.update()

        if self.project is not None and self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()


        dialog = NewProjectDialog(self, self.settings, movie_path,
                                  add_to_current_corpus=add_to_current_corpus)
        dialog.show()

    def new_project(self, project, template_path = None, vocabularies = None, copy_movie = "None", finish_callback = None, corpus_path=None):
        if self.project is not None:
            self.close_project()
        self.project = project

        self.project.inhibit_dispatch = True
        self.project.create_file_structure()
        self.project.connect_hdf5()

        self.settings.add_to_recent_files(self.project)
        self.update_recent_menu()

        # Importing all Vocabularies
        if vocabularies is not None:
            for i, v in enumerate(vocabularies):
                log_debug("Importing: " + str(i) + " " + v + "\r")
                self.project.import_vocabulary(v)

        if copy_movie == "Copy":
            new_path = self.project.folder + os.path.basename(self.project.movie_descriptor.movie_path)
            log_debug("Copy: ", new_path, self.project.movie_descriptor.movie_path)
            shutil.copy(self.project.movie_descriptor.movie_path, new_path)
            self.project.movie_descriptor.set_movie_path(new_path)

        elif copy_movie == "Move":
            new_path = self.project.folder + os.path.basename(self.project.movie_descriptor.movie_path)
            shutil.move(self.project.movie_descriptor.movie_path, new_path)
            self.project.movie_descriptor.set_movie_path(new_path)

        if corpus_path is not None:
            if self.corpus_widget.corpus is None or self.corpus_widget.corpus.file != corpus_path:
                corpus = self.corpus_widget.load_corpus(corpus_path)
            else:
                corpus = self.corpus_widget.corpus
            corpus.add_project(self.project)
            self.project.apply_template(template=corpus.template.get_template(segm=True,
                                                                              voc=True,
                                                                              experiment=True,
                                                                              pipeline=True))
            print("Script",self.project.active_pipeline_script)
        elif template_path is not None:
            self.project.apply_template(template_path)

        self.project.store_project()
        self.project.inhibit_dispatch = False

        self.project.onProjectLoaded.connect(self.dispatch_on_loaded)
        self.project.onProjectChanged.connect(self.dispatch_on_changed)
        self.project.onSelectionChanged.connect(self.dispatch_on_selected)
        self.onProjectOpened.emit(self.project)

        #  Creating a Default Experiment and Classification Object in case the multi-experiment mode is turned off
        if len(self.project.experiments) == 0:
            exp = self.project.create_experiment("Default")
        if len(self.project.experiments[0].classification_objects) == 0:
            self.project.experiments[0].create_class_object("Global")

        if not is_vian_light():
            dialog = LetterBoxWidget(self, self, self.dispatch_on_loaded)
            dialog.set_movie(self.project.movie_descriptor)
            dialog.show()
            dialog.view.fitInView(dialog.view.sceneRect(), Qt.KeepAspectRatio)
        else:
            self.dispatch_on_loaded()

    def on_load_project(self):
        if self.project is not None and self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()

        self.check_overlay_visibility()
        path = QFileDialog.getOpenFileName(filter="*" + VIAN_PROJECT_EXTENSION, directory=self.settings.DIR_PROJECTS)
        path = path[0]
        self.close_project()
        try:
            self.load_project(path)
        except Exception as e:
            log_error(e)
            QMessageBox.warning(self, "Failed to Load", "File is corrupt and could not be loaded")

    def close_project(self):
        self.worker_manager.on_closed()

        if self.project is not None:

            if self.project.undo_manager.has_modifications():
                answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
                if answer == QMessageBox.Yes:
                    self.on_save_project(sync=True)

            self.flask_server.on_closed()
            self.player.stop()
            self.abortAllConcurrentThreads.emit()

            if self.colormetry_running:
                self.toggle_colormetry()
            self.project.cleanup()
            if self.corpus_widget is not None:
                self.corpus_widget.set_in_template_mode(False)

        self.player_controls.setState(False)
        self.project = None
        self.dispatch_on_closed()

    def load_project(self, path):
        if self.project is not None:
            self.close_project()

        if path == "" or path is None:
            self.print_message("Not Loaded, Path was Empty")
            return

        new = VIANProject()
        log_info("Loading Project Path", path)
        new.inhibit_dispatch = True
        new.load_project(path, main_window=self, library=self.vocabulary_library)

        self.project = new
        self.settings.add_to_recent_files(self.project)
        self.update_recent_menu()

        self.project.onProjectLoaded.connect(self.dispatch_on_loaded)
        self.project.onProjectChanged.connect(self.dispatch_on_changed)
        self.project.onSelectionChanged.connect(self.dispatch_on_selected)

        # Creating a Default Experiment and Classification Object in case the multi-experiment mode is turned off
        if len(self.project.experiments) == 0:
            exp = self.project.create_experiment("Default")
        if len(self.project.experiments[0].classification_objects) == 0:
            self.project.experiments[0].create_class_object("Global")


        self.onProjectOpened.emit(self.project)
        new.inhibit_dispatch = False
        try:
            self.dispatch_on_loaded()
        except FileNotFoundError:
            self.close_project()

    def on_save_project(self, open_dialog=False, sync = False):
        if self.project is None:
            return

        if self.corpus_widget.in_template_mode:
            return

        self.onSave.emit()

        if open_dialog is True or self.project.path == "" or self.project.name == "":

            path = QFileDialog.getSaveFileName(caption="Select Project File to save", filter="*" + VIAN_PROJECT_EXTENSION)

            path = path[0].replace(VIAN_PROJECT_EXTENSION, "")
            path = path.replace("\\", "/")
            split = path.split("/")
            path = ""
            for s in split[0:len(split)-1]:
                path += s + "/"
            name = split[len(split)-1]
            self.project.path = path + name
            self.project.name = name
            self.project.movie_descriptor.set_movie_path(self.player.movie_path)

            path = self.project.path
            args = [self.project, path]
        else:
            path = self.project.path
            args = [self.project, self.project.path]

        if sync:
            store_project_concurrent(args, self.dummy_func)
        else:
            worker = Worker(store_project_concurrent, self, None, args, msg_finished="Project Saved")
            self.start_worker(worker, "Saving Project")

        log_info("Saving to:", path)
        self.settings.add_to_recent_files(self.project)
        self.project.undo_manager.no_changes = True

        return

    def on_save_project_as(self):
        self.on_save_project(True)
    #endregion

    #region Tools
    def on_auto_segmentation(self):
        dialog = DialogAutoSegmentation(self, self.project)
        dialog.show()

    def on_auto_screenshot(self):
        dialog = DialogAutoScreenshot(self, self.project)
        dialog.show()

    # endregion

    #region MISC
    def update_autosave_timer(self, do_start = True):
        self.autosave_timer.stop()
        if self.settings.AUTOSAVE:
            ms =  self.settings.AUTOSAVE_TIME * 60 * 1000
            log_info("Autosave Changed:", ms, "ms")
            self.autosave_timer.setInterval(ms)
            if do_start:
                self.autosave_timer.start()

    def open_drawing_editor(self, drawing, pos):
        if self.drawing_editor is not None:
            self.close_drawing_editor()

        self.drawing_editor = DrawingEditorWidget(drawing, self)
        self.drawing_editor.move(pos)
        self.drawing_editor.show()

    def close_drawing_editor(self):
        if self.drawing_editor is not None:

            self.drawing_editor.close()
            self.drawing_editor = None

    def check_overlay_visibility(self):
        if self.application_in_focus is False:
            self.set_overlay_visibility(False)
        elif not self.player_dock_widget.isVisible():
            self.set_overlay_visibility(False)
        elif len(self.open_dialogs) > 0:
            self.set_overlay_visibility(False)
        elif self.settings.OPENCV_PER_FRAME == 0:
            self.set_overlay_visibility(False)
        else:
            self.set_overlay_visibility(True)

    def set_overlay_visibility(self, visibility = None):
        if visibility:
            self.drawing_overlay.show()
        else:
            self.drawing_overlay.hide()

        self.update_overlay()
        self.drawing_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, not visibility)

    def create_analysis_list(self):
        self.analysis_list = []
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj):
                if issubclass(obj, IAnalysisJob):
                    if not obj.__name__ == IAnalysisJob.__name__:
                        self.analysis_list.append(obj)

    def signal_timestep_update(self):
        if self.time_counter < self.clock_synchronize_step:
            self.time += self.time_update_interval * self.player.get_rate()
            self.time_counter += 1
        else:
            self.time = self.player.get_media_time()
            self.time_counter = 0

        t = self.time
        if t > 0:
            if self.project is not None and t > self.project.movie_descriptor.duration - self.settings.EARLY_STOP:
                self.player.pause()
            self.dispatch_on_timestep_update(t)

    #endregion

    #region Import / Export
    def export_template(self):
        dialog = ExportTemplateDialog(self)
        dialog.show()

    def import_elan_project(self, path=None, create_new = True):
        """
        Imports an existing ELAN Project's segmentations either in the current project or into a new one
        :param path: Path to the ELAN Project (optional)
        :param create_new: If a new Project should be created (optional)
        :return: Nothing
        """
        importer = ELANProjectImporter(self, remote_movie=True, import_screenshots=True)
        try:
            if path is None or not os.path.isfile(path):
                path = QFileDialog.getOpenFileName(self, filter="*.eaf")[0]

            movie_path, segmentation = importer.elan_project_importer(path)

            # Create A New Project if necessary
            if create_new:
                if os.path.isfile(movie_path):
                    cap = cv2.VideoCapture(movie_path)
                    ret, frame = cap.read()
                    if not ret:
                        movie_path = ""
                else:
                    movie_path = ""

                dialog = NewProjectDialog(self, self.settings, movie_path, elan_segmentation=segmentation)
                dialog.show()
            else:
                if self.project is not None:
                    importer.apply_import(self.project, segmentation)
                    self.dispatch_on_changed()
        except Exception as e:
            log_error(e)

    def import_csv_vocabulary(self):
        dialog = CSVVocabularyImportDialog(self, self.project)
        dialog.show()

    def import_segmentation(self, path=None):
        pass

    def import_webapp(self):
        if self.project is None:
            self.close_project()

        project_file = QFileDialog.getOpenFileName(self, caption="Select WebApp File", filter="*.json *.webapp_json")[0]

        if not os.path.isfile(project_file):
            return

        if self.project is None:
            self.close_project()

        directory = QFileDialog.getExistingDirectory(self,
                                                     caption="Select directory where the project folder is placed",
                                                    directory=self.settings.DIR_PROJECTS)

        if not os.path.isdir(directory):
            QMessageBox.warning(self, "No valid Directory", "No valid directory has been selected")
            return

        movie_path = QFileDialog.getOpenFileName(self, caption="Select Movie File",
                                                 directory=self.settings.DIR_PROJECTS)[0]

        self.project = VIANProject(movie_path=movie_path)
        self.project.import_(WebAppProjectImporter(self.project.movie_descriptor.movie_path,
                                                   directory=directory),
                             project_file)

        self.project.store_project(self.project.path)
        p = self.project.path
        self.close_project()

        self.load_project(p)


    def import_srt(self):
        if self.project is None:
            return
        srt_file = QFileDialog.getOpenFileName(self, caption="Select SRT File", filter="*.srt")[0]
        self.project.import_(SRTImporter(), srt_file)

    def import_eyetracking(self):
        dialog = DialogImportEyetracking(self)
        dialog.show()
        pass

    def export_segmentation(self):
        dialog = ExportSegmentationDialog(self)
        dialog.show()

    def import_vocabulary(self, paths=None):
        if paths is None:
            paths = QFileDialog.getOpenFileNames(directory=os.path.abspath(get_vian_data("vocabularies/")))[0]
        try:
            self.project.inhibit_dispatch = True
            for p in paths:
                self.project.import_vocabulary(p)
            self.project.inhibit_dispatch = False
            self.project.dispatch_changed()
        except Exception as e:
            self.print_message("Vocabulary Import Failed", "Red")
            self.print_message(str(e), "Red")

    def import_template(self, path = None):
        if path is None:
            path = QFileDialog.getOpenFileName(self, caption="Select VIANT File", filter="*.viant")[0]
        if self.project is not None:
            self.project.apply_template(path)


    def export_vocabulary(self):
        return
        #TODO
        dialog = VocabularyExportDialog(self)
        dialog.show()

    def import_screenshots(self, paths=None):
        dialog = DialogScreenshotImport(self, paths)
        dialog.show()

    def on_zip_project(self):
        try:
            zip_project(self.project.export_dir + "/" + self.project.name, self.project.folder)
        except Exception as e:
            self.print_message("Zipping Project Failed", "Red")
            self.print_message(str(e), "Red")

    def on_export_csv(self):
        file = QFileDialog.getSaveFileName(filter="*.csv")[0]
        try:
            self.project.export(SequenceProtocolExporter(), file)
        except Exception as e:
            log_error(e)

    def on_export_excel(self):
        file = QFileDialog.getSaveFileName(filter="*.xlsx")[0]
        try:
            self.project.export(SequenceProtocolExporter(export_format=SequenceProtocolExporter.FORMAT_EXCEL), file)
        except Exception as e:
            raise

    def on_export_movie_segments(self):
        if self.project is not None:
            to_export = []
            for s in self.project.selected:
                if isinstance(s, Segment):
                    name = build_segment_nomenclature(s)
                    to_export.append((s.get_start(), s.get_end(), name))

            if len(to_export) > 0:
                directory = QFileDialog.getExistingDirectory(caption="Select Directory to export Segments into", directory=self.project.export_dir)
                if os.path.isdir(directory):
                    self.audio_handler.export_segments(to_export, directory=directory, callback=print)
                else:
                    return
            else:
                dialog = QMessageBox.information(self, "Export Segments", "You first have to select some segments to export.")
                dialog.show()
        pass

    def import_experiment(self):
        if self.project is None:
            QMessageBox.warning(self, "No Project loaded", "You first have to create a "
                                                           "new project or load an existing to do this.")
            return
        file = QFileDialog.getOpenFileName()[0]
        self.project.import_(ExperimentTemplateImporter(), file)

    #endregion

    def set_ui_enabled(self, state):
        self.actionSave.setDisabled(not state)
        self.actionCompare_Project_with.setDisabled(not state)
        self.actionSaveAs.setDisabled(not state)
        self.actionBackup.setDisabled(not state)
        self.actionClose_Project.setDisabled(not state)
        self.menuExport.setDisabled(not state)
        self.plugin_menu.setDisabled(False)
        self.menuWindows.setDisabled(False)
        self.actionImportELANSegmentation.setDisabled(not state)
        self.actionImportVocabulary.setDisabled(not state)
        self.actionImportCSVVocabulary.setDisabled(not state)
        self.screenshot_toolbar.setDisabled(not state)
        self.annotation_toolbar.setDisabled(not state)

        for i in range(2, len(self.menus_list)): # The First two should also be active if no project is opened
            m = self.menus_list[i]
            for e in m.actions():
                e.setDisabled(not state)
        self.actionPreferences.setEnabled(True)

    def get_version_as_string(self):

        result = "VIAN - Visual Movie SVGAnnotation\n"
        result += "Version: ".ljust(15) + str(version.__version__) + "\n"
        result += "\n\n"
        result += "Author: ".ljust(15) + str(version.__author__) + "\n"
        result += "Copyright: ".ljust(15) + str(version.__copyright__) + "\n"
        result += "Credits: ".ljust(15) + str(version.__credits__[0]) + "\n"
        for i in range(1, len(version.__credits__)):
            result += "".ljust(15) + str(version.__credits__[i]) + "\n"
        result += "License: ".ljust(15) + str(version.__license__) + "\n"
        result += "Maintainer: ".ljust(15) + str(version.__maintainer__) + "\n"
        result += "Email: ".ljust(15) + str(version.__email__) + "\n"
        result += "Status: ".ljust(15) + str(version.__status__) + "\n"

        return result

    def show_info_popup(self, widget:QWidget, text, pos = Qt.TopRightCorner):
        """
        Shows a frameless popup with a given text and position to help the user understand the GUI

        :param widget:
        :param text:
        :param pos:
        :return:
        """
        loc = widget.parent().mapToGlobal(widget.pos())
        if pos == Qt.TopRightCorner:
            loc += QPoint(widget.width(), 0)
        elif pos == Qt.BottomRightCorner:
            loc += QPoint(widget.width(), widget.height())
        elif pos == Qt.BottomLeftCorner:
            loc += QPoint(0, widget.height())

        w = InfoPopup(self, text, loc)
        w.show()

    @pyqtSlot(bool)
    def on_multi_experiment_changed(self, state):
        """ If multi experiment is activated, a selector is shown, else the primary experiment is shown per default """
        self.actionCreateExperiment.setVisible(state)
        self.onMultiExperimentChanged.emit(state)
        # self.recreate_tree()

    #region IProjectChangedNotify

    def dispatch_on_loaded(self):
        # self.set_darwin_player_visibility(True)
        self.autosave_timer.start()
        self.set_ui_enabled(True)
        self.hdf5_cache.cleanup()

        self.vian_event_handler.set_project(self.project)
        self.project.onAnalysisAdded.connect(self.corpus_client_toolbar.on_analyses_changed)

        screenshot_position = []
        screenshot_annotation_dicts = []

        self.has_open_project = True

        job = ERCUpdateJob()
        worker = MinimalThreadWorker(job.run_concurrent, self.project, True)
        self.thread_pool.start(worker, QThread.HighPriority)

        # Check if the file exists locally
        success = True
        if not os.path.isfile(self.project.movie_descriptor.movie_path):
            exists = False
            if self.project.movie_descriptor.movie_path == "":
                exists = False
            if not exists:
                QMessageBox.information(self, "Could not find movie",
                                        "Could not find movie: " + str(self.project.movie_descriptor.movie_path) +
                                        "\nPlease set it manually after clicking \"OK\".")
                path = QtWidgets.QFileDialog.getOpenFileName(self)[0]
                if os.path.isfile(path):
                    self.project.movie_descriptor.set_movie_path(path)
                else:
                    success = False

        if not success:
            self.close_project()
            return

        self.onMovieOpened.emit(self.project)
        for o in self.i_project_notify_reciever:
            o.on_loaded(self.project)
        self.pipeline_widget.pipeline.on_loaded(self.project)

        self.frame_update_worker.set_movie_path(self.project.movie_descriptor.get_movie_path())
        self.frame_update_worker.set_project(self.project)

        self.screenshots_manager.set_loading(True)
        job = LoadScreenshotsJob(self.project)
        self.run_job_concurrent(job)

        self.setWindowTitle("VIAN Project:" + str(self.project.path))
        self.dispatch_on_timestep_update(-1)

        self.search_window.on_loaded(self.project)
        ready, colorimetry = self.project.get_colormetry()
        run_colormetry = False
        if not ready:
            run_colormetry = False
            # if self.settings.AUTO_START_COLORMETRY:
            #     run_colormetry = True
            # else:
            #     self.open_dialogs.append("Dummy")
            #     self.check_overlay_visibility()
            #     answer = QMessageBox.question(self, "Colormetry",
            #                                   "Do you want to start the Colormetry Analysis now?"
            #                                   "\n\n"
            #                                   "Hint: The Colormetry will be needed for several Tools in VIAN,\n"
            #                                   "but will need quite some resources of your computer.")
            #     if answer == QMessageBox.Yes:
            #         run_colormetry = True
            #     self.open_dialogs.remove("Dummy")
            #     self.check_overlay_visibility()

            if run_colormetry:
                self.toggle_colormetry()
            else:
                self.timeline.timeline.set_colormetry_progress(0.0)
        else:
            self.on_colormetry_finished(None)

        log_info("\n#### --- Loaded Project --- ####")
        log_info("Folder:".rjust(15), self.project.folder)
        log_info("Path:".rjust(15),self.project.path)
        log_info("Movie Path:".rjust(15),self.project.movie_descriptor.movie_path)
        if self.project.colormetry_analysis is not None:
            log_info("Colorimetry:".rjust(15), self.project.colormetry_analysis.has_finished)
        log_info("\n")


    def dispatch_on_changed(self, receiver = None, item = None):
        if self.project is None or not self.allow_dispatch_on_change:
            return
        if receiver is not None:
            for r in receiver:
                r.on_changed(self.project, item)
        else:
            for o in self.i_project_notify_reciever:
                o.on_changed(self.project, item)


    @pyqtSlot(object, object)
    def dispatch_on_selected(self, sender, selected):
        if self.project is None:
            return
        self.elan_status.set_selection(selected)

        if not isinstance(selected, list):
            selected = []

        for o in self.i_project_notify_reciever:
            # ttime = time.time()
            o.on_selected(sender, selected)
            # print(sender, o.__class__.__name__, time.time() - ttime)


    @pyqtSlot(int)
    def dispatch_on_timestep_update(self, time):
        if self.project is None:
            return

        frame = self.player.get_frame_pos_by_time(time)
        self.onTimeStep.emit(time)
        QCoreApplication.removePostedEvents(self.frame_update_worker)
        self.onUpdateFrame.emit(time, frame)

        if self.project.get_main_segmentation() is not None:
            current_segment = self.project.get_main_segmentation().get_segment_of_time(time)
            if current_segment is not None and self.last_segment_index != current_segment.ID - 1:
                self.last_segment_index = current_segment.ID - 1
                self.onSegmentStep.emit(self.last_segment_index)

        if time == -1:
            for l in self.project.annotation_layers:
                for a in l.annotations:
                    a.widget.hide()
                    a.widget.is_active = False
        else:
            for l in self.project.annotation_layers:
                if l.is_visible:
                    for a in l.annotations:
                        if a.get_start() <= time <= a.get_end():
                            if a.widget is not None:
                                a.is_visible = True
                                a.widget.show()
                                a.widget.is_active = True
                        else:
                            if a.widget is not None:
                                a.is_visible = False
                                a.widget.hide()
            if len(self.project.annotation_layers) > 0:
                self.drawing_overlay.update()


    def dispatch_on_closed(self):
        self.onProjectClosed.emit()
        self.autosave_timer.stop()
        for o in self.i_project_notify_reciever:
            o.on_closed()

        self.search_window.on_close()
        self.pipeline_widget.pipeline.on_closed()
        self.set_ui_enabled(False)


    #endregion
    pass


class DialogFirstStart(QtWidgets.QDialog):
    def __init__(self, main_window):
        super(DialogFirstStart, self).__init__(main_window)
        path = os.path.abspath("qt_ui/DialogFirstStart.ui")
        uic.loadUi(path, self)

        self.main_window = main_window
        self.settings = main_window.settings
        self.may_proceed = False

        self.btn_OK.clicked.connect(self.on_ok)
        self.lineEdit_UserName.editingFinished.connect(self.on_name_changed)

        self.show()

    def on_name_changed(self):
        name = self.lineEdit_UserName.text()
        self.settings.USER_NAME = name

    def check_if_finished(self):
        finished = False
        if self.lineEdit_UserName.text() != "":
            self.lineEdit_UserName.setStyleSheet("QLineEdit{color:green;}")
            if self.lineEdit_FullName.text() != "":
                self.lineEdit_FullName.setStyleSheet("QLineEdit{color:green;}")
                if self.lineEdit_EMail.text() != "":
                    self.lineEdit_EMail.setStyleSheet("QLineEdit{color:green;}")
                    return True
                else:
                    self.lineEdit_EMail.setStyleSheet("QLineEdit{color:red;}")
                    return False
            else:
                self.lineEdit_FullName.setStyleSheet("QLineEdit{color:red;}")
                return False
        else:
            self.lineEdit_UserName.setStyleSheet("QLineEdit{color:red;}")
            return False

    def on_ok(self):
        if self.check_if_finished():
            c = Contributor(full_name = self.lineEdit_FullName.text(),
                            user_name = self.lineEdit_UserName.text(),
                            email=self.lineEdit_EMail.text())
            self.settings.set_contributor(c)
            self.settings.store(self.main_window.dock_widgets)
            self.close()
        else:
            QMessageBox.warning(self.main_window, "Please Fill out the Form",
                                "Some information seems to be missing, please fill out the Form.")


class InfoPopup(QMainWindow):
    def __init__(self, parent, text, pos):
        super(InfoPopup, self).__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setStyleSheet("QWidget { background-color: #303030; border: 4px solid #a92020; color:#ffffff; font-size: 12pt; }")
        self.move(pos)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.setWindowOpacity(0.8)
        self.setCentralWidget(self.label)










