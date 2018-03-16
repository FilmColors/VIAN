# from PyQt4 import QtCore, QtGui, uic

# from annotation_viewer import AnnotationViewer
import webbrowser
import cProfile
import os
import glob
import cv2
from core.concurrent.worker import Worker
import time
import inspect
import sys

import importlib
from functools import partial

from core.concurrent.worker_functions import *
from core.concurrent.worker import MinimalThreadWorker
from core.data.enums import *
from core.data.importers import *
from core.data.masterfile import MasterFile
from core.data.project_streaming import ProjectStreamerShelve, NumpyDataManager
from core.data.settings import UserSettings
from core.data.vian_updater import VianUpdater
from core.data.exporters import *
from core.data.tools import *
from core.concurrent.auto_segmentation import *
from core.gui.Dialogs.SegmentationImporterDialog import SegmentationImporterDialog
from core.gui.Dialogs.elan_opened_movie import ELANMovieOpenDialog
from core.gui.Dialogs.export_segmentation_dialog import ExportSegmentationDialog
from core.gui.Dialogs.export_template_dialog import ExportTemplateDialog
from core.gui.Dialogs.new_project_dialog import NewProjectDialog
from core.gui.Dialogs.preferences_dialog import DialogPreferences
from core.gui.Dialogs.csv_vocabulary_importer_dialog import CSVVocabularyImportDialog
from core.gui.Dialogs.screenshot_importer_dialog import DialogScreenshotImport
from core.gui.Dialogs.welcome_dialog import WelcomeDialog
from core.gui.analyses_widget import AnalysisDialog
from core.gui.concurrent_tasks import ConcurrentTaskDock
from core.gui.drawing_widget import DrawingOverlay, DrawingEditorWidget, AnnotationToolbar
from core.gui.history import HistoryView
from core.gui.inspector import Inspector
from core.gui.keyeventhandler import EKeyEventHandler
from core.gui.outliner import Outliner
from core.gui.perspectives import PerspectiveManager, Perspective
from core.gui.player_controls import PlayerControls
from core.gui.player_vlc import Player_VLC, PlayerDockWidget
from core.gui.experiment_editor import ExperimentEditor, ExperimentEditorDock
from core.gui.colormetry_widget import *
from core.analysis.colorimetry.colormetry2 import ColormetryJob2
# from core.gui.shots_window import ScreenshotsManagerWidget, ScreenshotsToolbar, ScreenshotsManagerDockWidget
from core.gui.screenshot_manager import ScreenshotsManagerWidget, ScreenshotsToolbar, ScreenshotsManagerDockWidget
from core.gui.status_bar import StatusBar, OutputLine, StatusProgressBar, StatusVideoSource
from core.gui.timeline import TimelineContainer
from core.gui.vocabulary import VocabularyManager, VocabularyExportDialog, ClassificationWindow
from core.gui.analysis_results import AnalysisResultsDock, AnalysisResultsWidget
from core.gui.quick_annotation import QuickAnnotationWidget, QuickAnnotationDock
from core.node_editor.node_editor import NodeEditorDock
from core.node_editor.script_results import NodeEditorResults
from core.remote.corpus.client import CorpusClient
from core.remote.corpus.corpus import *
from core.remote.elan.server.server import QTServer
from extensions.extension_list import ExtensionList
from core.concurrent.timestep_update import TimestepUpdateWorkerSingle


from core.analysis.colorimetry.colorimetry import ColometricsAnalysis
from core.analysis.movie_mosaic.movie_mosaic import MovieMosaicAnalysis
from core.analysis.barcode.barcode_analysis import BarcodeAnalysisJob
from core.analysis.filmcolors_pipeline.filmcolors_pipeline import FilmColorsPipelineAnalysis
__author__ = "Gaudenz Halter"
__copyright__ = "Copyright 2017, Gaudenz Halter"
__credits__ = ["Gaudenz Halter", "FIWI, University of Zurich", "VMML, University of Zurich"]
__license__ = "GPL"
__version__ = "0.5.2"
__maintainer__ = "Gaudenz Halter"
__email__ = "gaudenz.halter@uzh.ch"
__status__ = "Development, (BETA)"

PROFILE = False


class MainWindow(QtWidgets.QMainWindow):
    onTimeStep = pyqtSignal(int)
    onUpdateFrame = pyqtSignal(int, int)
    onSegmentStep = pyqtSignal(object)
    currentSegmentChanged = pyqtSignal(int)
    abortAllConcurrentThreads = pyqtSignal()
    onOpenCVFrameVisibilityChanged = pyqtSignal(bool)

    def __init__(self, loading_screen:QSplashScreen):
        super(MainWindow, self).__init__()
        path = os.path.abspath("qt_ui/MainWindow.ui")
        uic.loadUi(path, self)

        loading_screen.setStyleSheet("QWidget{font-family: \"Helvetica\"; font-size: 10pt;}")
        loading_screen.showMessage("Loading, Please Wait... Initializing Main Window", Qt.AlignHCenter|Qt.AlignBottom, QColor(200,200,200,100))
        
        if PROFILE:
            self.profiler = cProfile.Profile()
            self.profiler.enable()

        self.setAcceptDrops(True)
        self.has_open_project = False
        self.version = __version__

        self.extension_list = ExtensionList(self)
        self.is_darwin = False
        if sys.platform == "darwin":  # for MacOS
            self.is_darwin = True
            self.setAttribute(Qt.WA_MacFrameworkScaled)
            self.setAttribute(Qt.WA_MacOpaqueSizeGrip)
            # self.setAttribute(Qt.WA_MacNoClickThrough)

            # self.setAttribute(Qt.WA_MacNormalSize)

        self.plugin_menu = self.extension_list.get_plugin_menu(self.menuWindows)
        self.menuBar().addMenu(self.plugin_menu)
        self.menuAnalysis.addMenu(self.extension_list.get_analysis_menu(self.menuAnalysis, self))

        self.settings = UserSettings()
        self.settings.load()

        self.master_file = MasterFile(self.settings)
        self.master_file.load()
        self.icons = IconContainer()

        loading_screen.showMessage("Checking ELAN Connection", Qt.AlignHCenter|Qt.AlignBottom,
                                   QColor(200,200,200,100))


        self.updater = VianUpdater(self, self.version)

        self.key_event_handler = EKeyEventHandler(self)

        # Central Widgets
        self.video_player = None
        self.screenshots_manager = None

        self.allow_dispatch_on_change = True

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(8)

        loading_screen.showMessage("Create Data Stream Database", Qt.AlignHCenter|Qt.AlignBottom,
                                   QColor(200,200,200,100))

        self.numpy_data_manager = NumpyDataManager(self)
        self.project_streamer = ProjectStreamerShelve(self)

        self.video_capture = None

        self.current_perspective = Perspective.Annotation.name

        # DockWidgets
        self.player_controls = None
        self.elan_status = None
        self.source_status = None
        # self.shots_window = None
        self.phonon_player = None
        self.annotation_toolbar = None
        # self.annotation_viewer = None
        self.drawing_overlay = None
        self.timeline = None
        self.output_line = None
        self.perspective_manager = None
        # self.screenshots_editor = None
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
        self.experiment_editor = None
        self.experiment_editor_dock = None
        self.quick_annotation_dock = None
        self.colorimetry_live = None

        # This is the Widget created when Double Clicking on a Annotation
        # This is store here, because is has to be removed on click, and because the background of the DrawingWidget
        # is Transparent
        self.drawing_editor = None
        self.concurrent_task_viewer = None

        self.dock_widgets = []

        # self.player = Player_VLC(self)
        self.player = Player_VLC(self)
        self.player_dock_widget = None

        self.server = QTServer(self.player)
        self.server.player = self.player
        if self.settings.USE_ELAN:
            self.server.start()

        self.project = VIANProject(self, "", "Default Project")

        loading_screen.showMessage("Creating GUI", Qt.AlignHCenter|Qt.AlignBottom,
                                   QColor(200,200,200,100))

        self.frame_update_worker = TimestepUpdateWorkerSingle()
        self.frame_update_thread = QThread(self)
        self.frame_update_worker.moveToThread(self.frame_update_thread)
        self.onUpdateFrame.connect(self.frame_update_worker.perform)


        # self.frame_update_thread.started.connect(self.frame_update_worker.run)
        self.frame_update_worker.signals.onMessage.connect(self.print_time)
        self.frame_update_thread.start()

        self.create_widget_elan_status()
        self.create_widget_video_player()
        # self.create_analyses_widget()
        self.drawing_overlay = DrawingOverlay(self, self.player.videoframe, self.project)
        self.create_annotation_toolbar()
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

        self.create_analysis_results_widget()
        self.create_experiment_editor()
        self.create_quick_annotation_dock()

        self.create_colorimetry_live()

        self.splitDockWidget(self.player_controls, self.perspective_manager, Qt.Horizontal)
        self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)

        self.tabifyDockWidget(self.inspector, self.history_view)
        self.tabifyDockWidget(self.screenshots_manager_dock, self.vocabulary_matrix)


        self.tabifyDockWidget(self.inspector, self.concurrent_task_viewer)

        self.annotation_toolbar.raise_()
        self.inspector.raise_()
        self.screenshots_manager_dock.raise_()
        # self.annotation_tb2 = AnnotationToolbar2(self,self.drawing_overlay)
        # self.addToolBar(self.annotation_tb2)

        # self.tabifyDockWidget(self.screenshots_editor, self.annotation_viewer)
        # self.tabifyDockWidget(self.screenshots_editor, self.inspector)
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.East)
        self.history_view.hide()
        self.concurrent_task_viewer.hide()

        # self.drawing_overlay.setParent(self)



        # Binding the Action Menu
        # self.connect(self.actionScreenshot, QtCore.SIGNAL("triggered()"), self.screenshot)
        # self.connect(self.actionControls, QtCore.SIGNAL("triggered()"), self.create_widget_player_controls)
        # self.connect(self.actionElanConnection, QtCore.SIGNAL("triggered()"), self.create_widget_elan_status)
        # self.connect(self.actionShots, QtCore.SIGNAL("triggered()"), self.create_widget_shots_window)

        ## Action Slots ##
        # Tab File

        loading_screen.showMessage("Initializing Callbacks", Qt.AlignHCenter|Qt.AlignBottom,
                                   QColor(250, 250, 250, 100))
        self.actionNew.triggered.connect(self.action_new_project)
        self.actionLoad.triggered.connect(self.on_load_project)
        self.actionSave.triggered.connect(self.on_save_project)
        self.actionSaveAs.triggered.connect(self.on_save_project_as)
        self.actionBackup.triggered.connect(self.on_backup)

        self.actionImportELANSegmentation.triggered.connect(self.import_segmentation)
        self.action_importELAN_Project.triggered.connect(self.import_elan_project)
        self.actionImportVocabulary.triggered.connect(partial(self.import_vocabulary, None))
        self.actionImportFilmColorsPipeline.triggered.connect(self.import_pipeline)
        self.actionImportFilmColorsFilemaker.triggered.connect(self.import_filemaker)
        self.actionImportCSVVocabulary.triggered.connect(self.import_csv_vocabulary)
        self.actionImportScreenshots.triggered.connect(self.import_screenshots)
        self.actionImportVIANExperiment.triggered.connect(self.import_experiment)

        self.action_ExportSegmentation.triggered.connect(self.export_segmentation)
        self.actionExportTemplate.triggered.connect(self.export_template)
        self.actionExportVocabulary.triggered.connect(self.export_vocabulary)
        self.actionExportExperiment.triggered.connect(self.export_experiment)
        self.actionClose_Project.triggered.connect(self.close_project)
        self.actionZip_Project.triggered.connect(self.on_zip_project)
        self.actionExit.triggered.connect(self.on_exit)

        self.actionUndo.triggered.connect(self.on_undo)
        self.actionRedo.triggered.connect(self.on_redo)
        self.actionDelete.triggered.connect(self.on_delete)

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
        self.actionExperiment_Editor.triggered.connect(self.create_experiment_editor)

        self.actionExperimentSetupPersp.triggered.connect(partial(self.switch_perspective, Perspective.ExperimentSetup.name))
        self.actionPlayerPersp.triggered.connect(partial(self.switch_perspective, Perspective.VideoPlayer.name))
        self.actionAnnotationPersp.triggered.connect(partial(self.switch_perspective, Perspective.Annotation.name))
        self.actionScreenshotsPersp.triggered.connect(partial(self.switch_perspective, Perspective.ScreenshotsManager.name))
        self.actionNodeEditorPerspective.triggered.connect(partial(self.switch_perspective, Perspective.Analyses.name))
        self.actionSegmentationPersp.triggered.connect(partial(self.switch_perspective, Perspective.Segmentation.name))
        self.actionResultsPersp.triggered.connect(partial(self.switch_perspective, Perspective.Results.name))
        self.actionVocabularyPersp.triggered.connect(partial(self.switch_perspective, Perspective.Classification.name))
        self.actionQuick_Annotation.triggered.connect(partial(self.switch_perspective, Perspective.QuickAnnotation.name))

        self.actionHistory.triggered.connect(self.create_history_view)
        self.actionTaksMonitor.triggered.connect(self.create_concurrent_task_viewer)
        self.actionAdd_Annotation_Layer.triggered.connect(self.on_new_annotation_layer)
        self.actionAdd_Segmentation.triggered.connect(self.on_new_segmentation)
        self.actionCreateExperiment.triggered.connect(self.on_new_experiment)

        self.actionScreenshot.triggered.connect(self.on_screenshot)
        self.actionAdd_Key.triggered.connect(self.on_key_annotation)
        self.actionAdd_Segment.triggered.connect(self.on_new_segment)
        self.actionAbout.triggered.connect(self.on_about)
        self.actionWelcome.triggered.connect(self.show_welcome)
        self.actionIncreasePlayRate.triggered.connect(self.increase_playrate)
        self.actionDecreasePlayRate.triggered.connect(self.decrease_playrate)

        #TOOLS
        self.actionAuto_Segmentation.triggered.connect(self.on_auto_segmentation)

        self.actionColormetry.triggered.connect(self.start_colormetry)
        self.actionMovie_Mosaic.triggered.connect(partial(self.analysis_triggered, MovieMosaicAnalysis()))
        self.actionMovie_Barcode.triggered.connect(partial(self.analysis_triggered, BarcodeAnalysisJob()))

        self.actionSave_Perspective.triggered.connect(self.on_save_custom_perspective)
        self.actionLoad_Perspective.triggered.connect(self.on_load_custom_perspective)
        self.actionDocumentation.triggered.connect(self.open_documentation)

        self.actionUpdate.triggered.connect(self.update_vian)
        self.actionPlay_Pause.triggered.connect(self.player.play_pause)
        self.actionFrame_Forward.triggered.connect(partial(self.player.frame_step, False))
        self.actionFrame_Backward.triggered.connect(partial(self.player.frame_step, True))

        self.actionClearRecent.triggered.connect(self.clear_recent)

        qApp.focusWindowChanged.connect(self.on_application_lost_focus)
        self.i_project_notify_reciever = [self.player,
                                    self.drawing_overlay,
                                    # self.annotation_viewer,
                                    self.screenshots_manager,
                                    self.outliner,
                                    self.timeline.timeline,
                                    self.inspector,
                                    self.history_view,
                                    self.node_editor_dock.node_editor,
                                    self.vocabulary_manager,
                                    self.vocabulary_matrix,
                                    self.numpy_data_manager,
                                    self.project_streamer,
                                    self.analysis_results_widget,
                                    self.experiment_editor
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

        # self.actionElanConnection.triggered.connect(self.create_widget_elan_status)
        # self.actionShots.triggered.connect(self.create_widget_shots_window)





        # Autosave
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.on_save_project, False)
        self.update_autosave_timer(do_start=False)

        self.time_update_interval = 100
        self.update_timer = QtCore.QTimer()
        self.update_timer.setTimerType(Qt.PreciseTimer)
        self.update_timer.setInterval(self.time_update_interval)
        self.update_timer.timeout.connect(self.signal_timestep_update)

        self.time = 0
        self.time_counter = 0
        self.clock_synchronize_step = 5
        self.last_segment_index = 0

        self.player.movieOpened.connect(self.on_movie_opened, QtCore.Qt.QueuedConnection)
        self.player.started.connect(self.start_update_timer, QtCore.Qt.QueuedConnection)
        self.player.stopped.connect(self.update_timer.stop, QtCore.Qt.QueuedConnection)
        self.player.timeChanged.connect(self.dispatch_on_timestep_update, QtCore.Qt.AutoConnection)

        self.player.started.connect(partial(self.frame_update_worker.set_opencv_frame, False))
        self.player.stopped.connect(partial(self.frame_update_worker.set_opencv_frame, True))
        # self.player.started.connect(partial(self.frame_update_worker.set_colormetry_update, True))
        # self.player.stopped.connect(partial(self.frame_update_worker.set_opencv_frame, False))

        self.player.started.connect(partial(self.drawing_overlay.on_opencv_frame_visibilty_changed, False))
        self.player.started.connect(partial(self.drawing_overlay.on_opencv_frame_visibilty_changed, True))

        self.drawing_overlay.onSourceChanged.connect(self.source_status.on_source_changed)
        self.onOpenCVFrameVisibilityChanged.connect(self.on_frame_source_changed)
        self.dispatch_on_changed()

        self.frame_update_worker.signals.onColormetryUpdate.connect(self.colorimetry_live.update_timestep)

        self.screenshot_blocked = False

        # self.menuAnalysis.addMenu("Extensions")

        self.analysis_list = []

        self.is_selecting_analyzes = False


        loading_screen.showMessage("Finalizing", Qt.AlignHCenter|Qt.AlignBottom,
                                   QColor(200,200,200,100))
        self.update_recent_menu()


        # self.load_project("projects/ratatouille/Ratatouille.eext")

        # SEGMENT EVALUATOR
        # self.current_segment_evaluator = CurrentSegmentEvaluater()
        # self.player.started.connect(self.current_segment_evaluator.play)
        # self.player.stopped.connect(self.current_segment_evaluator.pause)
        # self.onTimeStep.connect(self.current_segment_evaluator.set_time)
        # self.current_segment_evaluator.signals.segmentChanged.connect(self.currentSegmentChanged.emit)
        # self.thread_pool.start(self.current_segment_evaluator)
        self.switch_perspective(Perspective.Segmentation.name)

        self.player_controls.setState(False)

        self.create_analysis_list()
        self.source_status.on_source_changed(self.settings.OPENCV_PER_FRAME)
        # self.onOpenCVFrameVisibilityChanged.emit(self.settings.OPENCV_PER_FRAME != 0)
        self.update_vian(False)

        self.project.undo_manager.clear()
        self.close_project()


        self.show()
        loading_screen.hide()
        self.setWindowState(Qt.WindowMaximized)

        # This can be used for a oneshot forced command.
        force_file_path = os.path.abspath("install/force.txt")
        if os.path.isfile(force_file_path):
            try:
                os.remove(force_file_path)
                self.settings.GRID_SIZE = 1
                self.settings.store()
                self.show_welcome()
            except Exception as e:
                print(e)

        if self.settings.SHOW_WELCOME:
            self.show_welcome()

        if self.settings.USER_NAME == "":
            self.show_first_start()




    def print_time(self, segment):
        print(segment)

    def test_function(self):
        self.abortAllConcurrentThreads.emit()

    def start_colormetry(self):
        job = ColormetryJob2(30, self)
        args = job.prepare(self.project)
        worker = MinimalThreadWorker(job.run_concurrent, args, True)
        worker.signals.callback.connect(self.on_colormetry_push_back)
        worker.signals.finished.connect(job.colormetry_analysis.set_finished)
        self.abortAllConcurrentThreads.connect(job.abort)
        self.thread_pool.start(worker)

    def on_colormetry_push_back(self, data):
        if self.project is not None:
            self.project.colormetry_analysis.append_data(data[0])
            self.timeline.timeline.set_colormetry_progress(data[1])
    #region WidgetCreation

    def show_welcome(self):
        open_web_browser(os.path.abspath("_docs/build/html/whats_new/latest.html"))
        self.settings.SHOW_WELCOME = False
        self.settings.store()

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
            if self.player_controls.isVisible():
                self.player_controls.hide()
            else:
                self.player_controls.show()
                self.player_controls.raise_()
                self.player_controls.activateWindow()

    def create_widget_elan_status(self):
        if self.elan_status is None:
            self.source_status = StatusVideoSource(self)
            self.elan_status = StatusBar(self, self.server)
            self.output_line = OutputLine(self)
            self.progress_bar = StatusProgressBar(self)

            self.statusBar().addWidget(self.source_status)
            self.statusBar().addPermanentWidget(self.progress_bar)
            self.statusBar().addWidget(self.output_line)

            self.statusBar().addPermanentWidget(self.elan_status)
            self.statusBar().setFixedHeight(45)

    def create_experiment_editor(self):
        if self.experiment_editor_dock is None:
            self.experiment_editor = ExperimentEditor(self)
            self.experiment_editor_dock = ExperimentEditorDock(self, self.experiment_editor)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.experiment_editor_dock)
        else:
            self.experiment_editor_dock.activateWindow()

    def create_widget_video_player(self):
        if self.player_dock_widget is None:
            self.player_dock_widget = PlayerDockWidget(self)
            self.player_dock_widget.set_player(self.player)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.player_dock_widget, Qt.Horizontal)

        else:
            self.player_dock_widget.set_player(self.player)
            self.player_dock_widget.show()
        if self.drawing_overlay is not None:
            self.set_overlay_visibility(True)


#OLD CODE

    def create_annotation_toolbar(self):
        if self.annotation_toolbar is None:
            self.annotation_toolbar = AnnotationToolbar(self, self.drawing_overlay)
            self.addToolBar(self.annotation_toolbar)
            # self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.annotation_toolbar)
        else:
            self.annotation_toolbar.show()

    def create_screenshot_manager(self):
        if self.screenshots_manager is None:
            self.screenshots_manager = ScreenshotsManagerWidget(self, key_event_handler = self.key_event_handler, parent=None)
        else:
            self.screenshots_manager.activateWindow()

#OLD CODE

    def create_inspector(self):
        if self.inspector is None:
            self.inspector = Inspector(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
        else:
            if self.inspector.isVisible():
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
            if self.concurrent_task_viewer.isVisible():
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
            if self.history_view.isVisible():
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
            if self.outliner.isVisible():
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
            if self.timeline.isVisible():
                self.timeline.hide()
            else:
                self.timeline.show()
                self.timeline.raise_()
                self.timeline.activateWindow()

    def create_screenshot_manager_dock_widget(self):
        if self.screenshots_manager_dock is None:
            self.screenshots_manager_dock = ScreenshotsManagerDockWidget(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.screenshots_manager_dock, QtCore.Qt.Horizontal)
            # self.on_movie_updated()
            self.screenshots_manager_dock.set_manager(self.screenshots_manager)
        else:
            if self.screenshots_manager_dock.isVisible():
                self.screenshots_manager_dock.hide()
            else:
                self.screenshots_manager_dock.show()
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
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.vocabulary_manager, QtCore.Qt.Vertical)
        else:
            self.vocabulary_manager.show()
            self.vocabulary_manager.activateWindow()

    def create_vocabulary_matrix(self):
        if self.vocabulary_matrix is None:
            self.vocabulary_matrix = ClassificationWindow(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.vocabulary_matrix, QtCore.Qt.Vertical)
        else:
            self.vocabulary_matrix.show()
            self.vocabulary_matrix.raise_()
            self.vocabulary_matrix.activateWindow()

    def create_analysis_results_widget(self):
        if self.analysis_results_widget is None:
            self.analysis_results_widget_dock = AnalysisResultsDock(self)
            self.analysis_results_widget = AnalysisResultsWidget(self.analysis_results_widget_dock, self)
            self.analysis_results_widget_dock.set_analysis_widget(self.analysis_results_widget)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.analysis_results_widget_dock, Qt.Vertical)
        else:
            if self.analysis_results_widget.isVisible():
                self.analysis_results_widget.hide()
            else:
                self.analysis_results_widget.show()
                self.analysis_results_widget.raise_()
                self.analysis_results_widget.activateWindow()

    def create_quick_annotation_dock(self):
        if self.quick_annotation_dock is None:
            self.quick_annotation_dock = QuickAnnotationDock(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.quick_annotation_dock, Qt.Vertical)
        else:
            if self.quick_annotation_dock.isVisible():
                self.quick_annotation_dock.hide()
            else:
                self.quick_annotation_dock.show()

    def create_colorimetry_live(self):
        if self.colorimetry_live is None:
            self.colorimetry_live = ColorimetryLiveWidget(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.colorimetry_live, Qt.Vertical)
        else:
            if self.colorimetry_live.isVisible():
                self.colorimetry_live.hide()
            else:
                self.colorimetry_live.show()

    #endregion

    #region QEvent Overrides
    def moveEvent(self, *args, **kwargs):
        QtWidgets.QMainWindow.moveEvent(self, *args, **kwargs)
        self.update()

    def closeEvent(self, *args, **kwargs):
        self.on_exit()

    def resizeEvent(self, *args, **kwargs):
        QtWidgets.QMainWindow.resizeEvent(self, *args, **kwargs)
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.screenshots_manager.ctrl_is_pressed = True
            self.timeline.timeline.is_scaling = True
        elif event.key() == Qt.Key_Shift:
            pass
            # self.timeline.timeline.is_multi_selecting = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.screenshots_manager.ctrl_is_pressed = False
            self.timeline.timeline.is_scaling = False
        elif event.key() == Qt.Key_Shift:
            pass
            # self.timeline.timeline.is_multi_selecting = False

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            file_extension = str(event.mimeData().urls()[0].toLocalFile()).split(".").pop()
            if file_extension in ["eaf", "png", "jpg"]:
                event.acceptProposedAction()

    def dropEvent(self, event):
        print("Hello")
        if event.mimeData().hasUrls():
            file_extension = str(event.mimeData().urls()[0]).split(".").pop()
            files = event.mimeData().urls()
            if "eaf" in file_extension:
                print("Importing ELAN Project")
                self.import_elan_project(str(event.mimeData().urls()[0]))
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
         #self.update_overlay()
        # if self.is_darwin:
        #     self.player.mac_frame.update()

        # if self.is_darwin:
        #     self.player_container.synchronize()
        #     self.drawing_overlay.raise_()
    #endregion

    #region MainWindow Event Handlers

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

    def clear_recent(self):
        self.settings.recent_files_name = []
        self.settings.recent_files_path = []
        self.update_recent_menu()

    def update_recent_menu(self):
        self.menuRecently_Opened.clear()
        try:
            for i, recent in enumerate(self.settings.recent_files_name):
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
                        print(getattr(module, class_name))
                        return getattr(module, class_name)
            except Exception as e:
                print(e)

    def update_vian(self, show_newest = True):
        try:
            result = self.updater.get_server_version()
        except:
            return

        if result:
            answer = QMessageBox.question(self, "Update Available", "A new Update is available, and will be updated now.\nVIAN will close after the Update. Please do not Update before you have saved the current Project. \n\n Do you want to Update now?")
            if answer == QMessageBox.Yes:
                self.updater.update()
            else:
                self.print_message("Update Aborted", "Orange")
        else:
            if show_newest:
                QMessageBox.information(self, "VIAN Up to Date", "VIAN is already on the newest version: " + self.version)
            else:
                self.print_message("VIAN is up to date with version: " + str(__version__), "Green")

    def open_preferences(self):
        dialog = DialogPreferences(self)
        dialog.show()

    def on_movie_opened(self):
        if self.player.movie_path != self.project.get_movie().movie_path:
            dialog = ELANMovieOpenDialog(self, self.master_file, self.player.movie_path)
            dialog.show()
        self.player_controls.on_play()

    def on_exit(self):
        if self.project is not None and self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project(sync=True)
            elif answer == QMessageBox.No:
                pass
            else:
                return

        self.dispatch_on_closed()
        self.settings.store()

        self.frame_update_thread.quit()

        if PROFILE:
            self.profiler.disable()
            self.profiler.dump_stats("Profile.prof")

        QCoreApplication.quit()

    def on_undo(self):
        self.project.undo_manager.undo()

    def on_redo(self):
        self.project.undo_manager.redo()

    def on_delete(self):
        to_delete = self.project.selected
        try:
            for d in to_delete:
                d.delete()
        except Exception as e:
            print(e)

    def update_overlay(self):
        if self.drawing_overlay is not None and self.drawing_overlay.isVisible():
            self.drawing_overlay.update()

    def on_new_segment(self):
        self.timeline.timeline.create_segment(None)

    def on_screenshot(self):
        # imgs = self.drawing_overlay.render_annotation()
        # qimage = imgs[0]
        # frame = imgs[1]
        #
        # annotation = convertQImageToMat(qimage)
        # blend = blend_transparent(frame, annotation)
        #


        time = self.player.get_media_time()
        # frame, pos = self.get_frame(time)
        
        frame_pos = self.player.get_frame_pos_by_time(time)
        # result = create_screenshot([self.drawing_overlay, frame, time, pos], None)
        # self.on_screenshot_finished(result)

        annotation_dicts = []
        for l in self.project.annotation_layers:
            if l.is_visible:
                for a in l.annotations:
                    a_dict = a.serialize()
                    annotation_dicts.append(a_dict)

        job = CreateScreenshotJob([frame_pos, self.project.movie_descriptor.movie_path, annotation_dicts, time])
        self.run_job_concurrent(job)

    def on_new_experiment(self):
        self.project.create_experiment()

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
        print("*********ERROR**IN**WORKER***********")
        print(error)
        print("*************************************")

    def worker_progress(self, tpl):
        # self.progress_bar.set_progress(float)
        total = self.concurrent_task_viewer.update_progress(tpl[0],tpl[1])
        self.progress_bar.set_progress(float(total)/100)

    def worker_abort(self, int):
        self.concurrent_task_viewer.remove_task(int)
        self.print_message("Task:" + str(int) + " aborted.", "orange")
        self.progress_bar.on_finished()

    def run_job_concurrent(self, job):
        job.prepare(self.project)
        worker = Worker(job.run_concurrent, self, self.on_job_concurrent_result, job.args, msg_finished="Screenshots Loaded", concurrent_job=job)
        self.abortAllConcurrentThreads.connect(job.abort)
        self.start_worker(worker, "Job")

    def on_job_concurrent_result(self, result):
        res = result[0]
        job = result[1]
        self.allow_dispatch_on_change = False

        if not job.aborted:
            job.modify_project(project=self.project,result=res)

        self.allow_dispatch_on_change = True
        self.dispatch_on_changed()
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
        pos = s.get_position()
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
            path = QFileDialog.getExistingDirectory(self, directory = self.settings.DIR_PROJECT)[0] + "/"
        elif answer == QMessageBox.Yes:
            path = self.settings.DIR_BACKUPS
        else:
            return

        if path is None or path == "":
            self.print_message("The Path: " + str(path) + " does not exist, please choose it manually.", "Orange")
            return

        filename = time.strftime("%Y_%m_%d_%H_%M_%S", time.gmtime(time.time()))+"_"+self.project.name + "_backup"
        try:
            print(path + filename)
            zip_project(path + filename, self.project.folder)
            self.print_message("Backup sucessfully stored to: " + path + filename + ".zip", "Green")
        except Exception as e:
            self.print_message("Backup Failed", "Red")
            self.print_message(str(e), "Red")

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
        self.centralWidget().setParent(None)
        self.statusBar().show()

        self.default_dock_locations()

        central = QWidget(self)
        central.setFixedWidth(0)

        if self.is_darwin:
            self.screenshot_toolbar.show()
            self.annotation_toolbar.show()

        if perspective == Perspective.VideoPlayer.name:
            self.current_perspective = Perspective.VideoPlayer
            self.hide_all_widgets()
            self.player_dock_widget.show()

        elif perspective == Perspective.Segmentation.name:
            self.current_perspective = Perspective.Segmentation
            self.hide_all_widgets()

            self.timeline.show()
            self.player_controls.show()
            self.screenshots_manager_dock.show()
            self.player_dock_widget.show()
            self.colorimetry_live.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.tabifyDockWidget(self.screenshots_manager_dock, self.colorimetry_live)

            self.screenshots_manager_dock.raise_()
            self.elan_status.stage_selector.set_stage(0, False)

        elif perspective == Perspective.Annotation.name:
            self.current_perspective = Perspective.Annotation

            self.hide_all_widgets()

            self.outliner.show()
            self.timeline.show()
            self.inspector.show()
            self.player_dock_widget.show()

            self.annotation_toolbar.show()

            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector)
            self.splitDockWidget(self.inspector, self.outliner, Qt.Vertical)
            self.elan_status.stage_selector.set_stage(1, False)
            self.screenshots_manager_dock.raise_()


        elif perspective == Perspective.ScreenshotsManager.name:
            self.current_perspective = Perspective.ScreenshotsManager
            self.screenshots_manager.update_manager()

            self.hide_all_widgets()

            self.screenshots_manager_dock.show()
            self.inspector.show()
            self.outliner.show()

            self.screenshot_toolbar.show()

            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.splitDockWidget(self.inspector, self.outliner, Qt.Vertical)

        elif perspective == Perspective.Analyses.name:
            self.current_perspective = Perspective.Analyses

            self.hide_all_widgets()

            self.inspector.show()
            self.outliner.show()
            self.node_editor_results.show()
            self.node_editor_dock.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)

        elif perspective == Perspective.Results.name:
            self.current_perspective = Perspective.Results

            self.hide_all_widgets()

            self.inspector.show()
            self.outliner.show()

            self.analysis_results_widget_dock.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.analysis_results_widget_dock, Qt.Horizontal)
            self.elan_status.stage_selector.set_stage(4, False)
            self.splitDockWidget(self.outliner, self.inspector, Qt.Vertical)

        elif perspective == Perspective.Classification.name:
            self.current_perspective = Perspective.Classification

            self.hide_all_widgets()

            self.timeline.show()
            self.screenshots_manager_dock.show()
            self.vocabulary_matrix.show()
            self.player_dock_widget.show()
            self.drawing_overlay.show()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.screenshots_manager_dock, Qt.Vertical)
            self.addDockWidget(Qt.RightDockWidgetArea, self.vocabulary_matrix)
            self.addDockWidget(Qt.RightDockWidgetArea, self.timeline, Qt.Vertical)

            self.elan_status.stage_selector.set_stage(3, False)
            # self.statusBar().hide()

        elif perspective == Perspective.ExperimentSetup.name:
            self.hide_all_widgets()

            self.outliner.show()
            self.vocabulary_manager.show()
            self.inspector.show()
            self.experiment_editor_dock.show()

            self.elan_status.stage_selector.set_stage(2, False)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner, Qt.Vertical)
            self.addDockWidget(Qt.RightDockWidgetArea, self.experiment_editor_dock)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)

        elif perspective == Perspective.QuickAnnotation.name:
            self.hide_all_widgets()
            self.player_dock_widget.show()
            self.quick_annotation_dock.show()

            self.addDockWidget(Qt.LeftDockWidgetArea,self.player_dock_widget)
            self.addDockWidget(Qt.BottomDockWidgetArea, self.quick_annotation_dock)


        self.setCentralWidget(central)

        self.centralWidget().show()
        # self.centralWidget().setBaseSize(size_central)

        if self.player_dock_widget.isVisible():
            self.set_overlay_visibility(True)
        else:
            self.set_overlay_visibility(False)

        self.set_default_dock_sizes(self.current_perspective)

    def hide_all_widgets(self):
        if self.annotation_toolbar.isVisible():
            self.annotation_toolbar.hide()
        if self.screenshot_toolbar.isVisible():
            self.screenshot_toolbar.hide()

        # self.create_widget_video_player()
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
        self.player_controls.hide()
        self.screenshots_manager_dock.hide()
        self.player_dock_widget.hide()
        self.experiment_editor_dock.hide()
        self.quick_annotation_dock.hide()
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
            print("OK")

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
        if self.current_perspective == Perspective.Annotation.name:
            if arg is None:
                # self.set_darwin_player_visibility(False)
                self.drawing_overlay.hide()
            else:
                # self.set_darwin_player_visibility(True)
                self.drawing_overlay.show()

    def analysis_triggered(self, analysis):

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
        fps = self.player.get_fps()

        args = analysis.prepare(self.project, targets, parameters, fps)

        if analysis.multiple_result:
            for arg in args:
                worker = Worker(analysis.process, self, self.analysis_result, arg,
                                msg_finished=analysis.name+ " Finished", target_id=None, i_analysis_job=analysis)
                self.start_worker(worker, analysis.get_name())
        else:
            worker = Worker(analysis.process, self, self.analysis_result, args, msg_finished=analysis.name+ " Finished", target_id=None, i_analysis_job=analysis)
            self.start_worker(worker, analysis.get_name())

    def analysis_result(self, result):
        analysis = result[1]
        result = result[0]

        analysis.modify_project(self.project, result)
        self.project.add_analysis(result)

        # Unload the analysis from Memory
        result.unload_container()

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
                self.set_overlay_visibility(True)

        else:
            if self.current_perspective == Perspective.Segmentation:
                self.set_overlay_visibility(False)

    def update_player_size(self):
        self.player.update()

    def open_documentation(self):
        webbrowser.open("file://" + os.path.abspath("_docs/build/html/index.html"))

    def on_about(self):
        about = ""
        about += "Author:".ljust(12) + __author__ + "\n"
        about += "Copyright:".ljust(12) + __copyright__ + "\n"
        about += "Version:".ljust(12) + __version__ + "\n"
        about += "Credits:".ljust(12) + str(__credits__) + "\n"
        QMessageBox.about(self, "About", about)

    def increase_playrate(self):
        self.player.set_rate(self.player.get_rate() + 0.1)
        self.player_controls.update_rate()

    def decrease_playrate(self):
        self.player.set_rate(self.player.get_rate() - 0.1)
        self.player_controls.update_rate()
    # endregion

    #region Project Management
    def action_new_project(self):
        self.on_new_project()

    def on_new_project(self, movie_path = ""):
        # self.set_darwin_player_visibility(False)
        self.update()

        if self.project is not None and self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()

        vocabularies = []
        built_in = glob.glob("user/vocabularies/*.txt")
        vocabularies = built_in

        dialog = NewProjectDialog(self, self.settings, movie_path, vocabularies)
        dialog.show()

    def new_project(self, project, template_path = None, vocabularies = None):
        if self.project is not None:
            self.close_project()

        self.project = project
        self.settings.add_to_recent_files(self.project)
        self.update_recent_menu()

        self.project.inhibit_dispatch = True
        if template_path is not None:
            self.project.apply_template(template_path, ExperimentImporter())

        self.project.create_file_structure()
        # Importing all Vocabularies
        if vocabularies is not None:
            for i, v in enumerate(vocabularies):
                print("Importing: " + str(i) + " " + v + "\r")
                self.project.import_vocabulary(v)

        # self.player.open_movie(project.movie_descriptor.movie_path)
        self.master_file.add_project(project)
        self.project.store_project(self.settings, self.master_file)

        self.project.inhibit_dispatch = False
        self.dispatch_on_loaded()

    def on_load_project(self):
        if self.project is not None and self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()

        self.set_overlay_visibility(False)
        path = QFileDialog.getOpenFileName(filter="*" + self.settings.PROJECT_FILE_EXTENSION, directory=self.settings.DIR_PROJECT)

        if self.current_perspective == (Perspective.Segmentation.name or Perspective.Annotation.name):
            self.set_overlay_visibility(True)
        path = path[0]
        self.close_project()
        self.load_project(path)

    def close_project(self):
        if self.project is not None:
            if self.project.undo_manager.has_modifications():
                answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
                if answer == QMessageBox.Yes:
                    self.on_save_project()

            self.player.stop()
            self.abortAllConcurrentThreads.emit()
            self.project.cleanup()

        self.player_controls.setState(False)
        self.project = None
        self.dispatch_on_closed()

    def load_project(self, path):

        if path == "" or path is None:
            self.print_message("Not Loaded, Path was Empty")
            return

        new = VIANProject(self)
        print("Loading Project Path", path)
        new.inhibit_dispatch = True
        new.load_project(self.settings ,path)

        self.project = new
        self.settings.add_to_recent_files(self.project)
        self.update_recent_menu()

        new.inhibit_dispatch = False
        #self.project_streamer.set_project(new)
        self.dispatch_on_loaded()

    def on_save_project(self, open_dialog=False, sync = False):
        if open_dialog is True or self.project.path is "" or self.project.name is "":

            path = QFileDialog.getSaveFileName(filter="*" + self.settings.PROJECT_FILE_EXTENSION)

            path = path[0].replace(self.settings.PROJECT_FILE_EXTENSION, "")
            path = path.replace("\\", "/")
            split = path.split("/")
            path = ""
            for s in split[0:len(split)-1]:
                path += s + "/"
            name = split[len(split)-1]
            self.project.path = path + name
            self.project.name = name
            self.project.movie_descriptor.movie_path = self.player.movie_path

            path = self.project.path
            args = [self.project, path, self.settings, self.master_file]
        else:
            args = [self.project, self.project.path, self.settings, self.master_file]

        if sync:
            store_project_concurrent(args, self.dummy_func)
        else:
            worker = Worker(store_project_concurrent, self, None, args, msg_finished="Project Saved")
            self.start_worker(worker, "Saving Project")

        self.project.undo_manager.no_changes = True

        return

    def on_save_project_as(self):
        self.on_save_project(True)
    #endregion

    #region Tools
    def on_auto_segmentation(self):
        dialog = DialogAutoSegmentation(self, self.project)
        dialog.show()
        # auto_segmentation(self.project,mode = AUTO_SEGM_CHIST, n_segment=10)

    # endregion

    #region MISC
    def update_autosave_timer(self, do_start = True):
        self.autosave_timer.stop()
        if self.settings.AUTOSAVE:
            ms =  self.settings.AUTOSAVE_TIME * 60 * 1000
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

    def set_overlay_visibility(self, visibility):
        if visibility:
            self.drawing_overlay.show()
        else:
            self.drawing_overlay.hide()
        self.drawing_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, not visibility)
        self.update_overlay()

    def create_analysis_list(self):
        self.analysis_list = []
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj):
                if issubclass(obj, IAnalysisJob):
                    if not obj.__name__ == IAnalysisJob.__name__:
                        self.analysis_list.append(obj)

    def signal_timestep_update(self):
        if self.time_counter < self.clock_synchronize_step:
            self.time += self.time_update_interval + 5
            self.time_counter += 1
        else:
            self.time = self.player.get_media_time()
            self.time_counter = 0
        t = self.time
        if t > 0:
            self.dispatch_on_timestep_update(t)

    #endregion

    #region Import / Export

    def import_experiment(self):
        paths = QFileDialog.getOpenFileNames(filter="*" + FILE_EXT_EXPERIMENT)[0]
        importer = ExperimentImporter()
        for p in paths:
            if os.path.isfile(p):
                try:
                    importer.import_experiment(p, self.project)
                except Exception as e:
                    print("Error in import_experiment()", str(e))

    def export_experiment(self):
        to_export = []
        for sel in self.project.selected:
            if sel.get_type() == EXPERIMENT:
                to_export.append(sel)

        dir = QFileDialog.getExistingDirectory(self, directory=self.project.export_dir)

        if not os.path.isdir(dir):
            self.print_message(str(dir) + " is not a valid Directory", "Red")

        exporter = ExperimentExporter()
        for exp in to_export:
            try:
                exporter.export(dir + "/" + exp.get_name().replace(" ", "_") + FILE_EXT_EXPERIMENT, experiment=exp)
            except Exception as e:
                raise(e)
                print("Error in export_experiment()", str(e))

        QMessageBox.information(self, "Export Finished", "The Experiments have been exported to " + str(dir))

    def export_template(self):
        dialog = ExportTemplateDialog(self)
        dialog.show()

    def import_elan_project(self, path=None):
        try:
            if path is None:
                path = QFileDialog.getOpenFileName(self, filter="*.eaf")[0]
            # path = path.replace("file:///", "")
            # path = path.replace("file:", "")

            path = parse_file_path(path)

            importer = ELANProjectImporter(self, remote_movie=True, import_screenshots=True)
            self.project = importer.import_project(path)
            self.on_save_project(False)

            self.project.main_window = self
            self.project.dispatch_loaded()
            self.print_message("Import Successfull", "Green")
        except Exception as e:
            self.print_message("Import Failed", "Red")
            self.print_message(
                "This is a serious Bug, please report this message, together with your project to Gaudenz Halter",
                "Red")
            self.print_message(str(e), "Red")

    def import_pipeline(self):
        path = QFileDialog.getOpenFileName(directory=self.project.export_dir)[0]
        if not os.path.isfile(path):
            self.print_message("Could not Open File", "Red")
            return
        importer = FilmColorsPipelineImporter()
        importer.import_pipeline(path, self.project)

    def import_filemaker(self):
        path = QFileDialog.getOpenFileName(directory=self.project.export_dir)[0]
        if not os.path.isfile(path):
            self.print_message("Could not Open File", "Red")
            return
        importer = FileMakerVocImporter()
        importer.import_filemaker(path, self.project)

    def import_csv_vocabulary(self):
        dialog = CSVVocabularyImportDialog(self, self.project)
        dialog.show()

    def import_segmentation(self, path=None):
        dialog = SegmentationImporterDialog(self, self.project, self)
        dialog.show()
        # QMessageBox.warning(self, "Deprecated",
        #                     "The Segmentation Importer is deprecated and therefore removed from VIAN.\n "
        #                     "For ELAN Projects use the \"ELAN Project Importer\". \n "
        #                     "A new Version for importing arbitary Segmentations is planned but not yet included.")
        # SegmentationImporterDialog(self, self.project, self)

    def export_segmentation(self):
        # path = QFileDialog.getSaveFileName(directory=self.project.path, filter=".txt")[0]
        dialog = ExportSegmentationDialog(self)
        dialog.show()

    def import_vocabulary(self, paths=None):
        if paths is None:
            paths = QFileDialog.getOpenFileNames(directory=os.path.abspath("user/vocabularies/"))[0]

        # path = QFileDialog.getOpenFileName(directory=self.project.export_dir)[0]
        try:
            self.project.inhibit_dispatch = True
            for p in paths:
                self.project.import_vocabulary(p)
            self.project.inhibit_dispatch = False
            self.project.dispatch_changed()
        except Exception as e:
            raise e
            self.print_message("Vocabulary Import Failed", "Red")
            self.print_message(str(e), "Red")

    def export_vocabulary(self):
        dialog = VocabularyExportDialog(self)
        dialog.show()

    def import_screenshots(self, paths=None):
        # paths = QFileDialog.getOpenFileNames()[0]
        # args = [self.project.movie_descriptor.movie_path, paths]
        # importer = ScreenshotImporter(args)
        # self.run_job_concurrent(importer)
        dialog = DialogScreenshotImport(self, paths)
        dialog.show()

    def on_zip_project(self):
        try:
            zip_project(self.project.export_dir + "/" + self.project.name, self.project.folder)
        except Exception as e:
            self.print_message("Zipping Project Failed", "Red")
            self.print_message(str(e), "Red")

    #endregion

    def set_ui_enabled(self, state):
        self.actionSave.setDisabled(not state)
        self.actionSaveAs.setDisabled(not state)
        self.actionBackup.setDisabled(not state)
        self.actionClose_Project.setDisabled(not state)
        self.menuExport.setDisabled(not state)
        self.plugin_menu.setDisabled(False)
        self.menuWindows.setDisabled(False)
        self.actionImportELANSegmentation.setDisabled(not state)
        self.actionImportVocabulary.setDisabled(not state)
        self.actionImportCSVVocabulary.setDisabled(not state)
        self.actionImportFilmColorsPipeline.setDisabled(not state)
        self.actionImportFilmColorsFilemaker.setDisabled(not state)

        for i in range(2, len(self.menus_list)): # The First two should also be active if no project is opened
            m = self.menus_list[i]
            for e in m.actions():
                e.setDisabled(not state)

    def get_version_as_string(self):

        result = "VIAN - Visual Movie Annotation\n"
        result += "Version: ".ljust(15) + __version__ + "\n"
        result += "\n\n"
        result += "Author: ".ljust(15) + __author__ + "\n"
        result += "Copyright: ".ljust(15) + __copyright__ + "\n"
        result += "Credits: ".ljust(15) + str(__credits__[0]) + "\n"
        for i in range(1, len(__credits__)):
            result += "".ljust(15) + str(__credits__[i]) + "\n"
        result += "License: ".ljust(15) + __license__ + "\n"
        result += "Maintainer: ".ljust(15) + __maintainer__ + "\n"
        result += "Email: ".ljust(15) + __email__ + "\n"
        result += "Status: ".ljust(15) + __status__ + "\n"

        return result

    #region IProjectChangedNotify

    def dispatch_on_loaded(self):
        # self.set_darwin_player_visibility(True)
        self.autosave_timer.start()
        self.set_ui_enabled(True)

        screenshot_position = []
        screenshot_annotation_dicts = []

        self.has_open_project = True

        for o in self.i_project_notify_reciever:
            o.on_loaded(self.project)

        self.project.unload_all()

        for s in self.project.screenshots:
            screenshot_position.append(s.frame_pos)
            a_dicts = []
            if s.annotation_item_ids is not None:
                for a_id in s.annotation_item_ids:
                    annotation_dict = self.project.get_by_id(a_id)
                    if annotation_dict is not None:
                        a_dicts.append(annotation_dict.serialize())

            screenshot_annotation_dicts.append(a_dicts)

        self.frame_update_worker.set_movie_path(self.project.movie_descriptor.movie_path)
        self.frame_update_worker.set_project(self.project)

        self.screenshots_manager.set_loading(True)
        job = LoadScreenshotsJob([self.project.movie_descriptor.movie_path, screenshot_position, screenshot_annotation_dicts])
        self.run_job_concurrent(job)

        self.setWindowTitle("VIAN Project:" + str(self.project.path))
        self.dispatch_on_timestep_update(-1)

        ready, coloremtry = self.project.get_colormetry()
        if not ready:
            run_colormetry = False
            if self.settings.AUTO_START_COLORMETRY:
                run_colormetry = True
            else:
                answer = QMessageBox.question(self, "Colormetry",
                                              "Do you want to start the Colormetry Analysis now?"
                                              "\n\n"
                                              "Hint: The Colormetry will be needed for several Tools in VIAN,\n"
                                              "but will need quite some resources of your computer.")
                if answer == QMessageBox.Yes:
                    run_colormetry = True
        else:
            run_colormetry = ready

        if run_colormetry:
            ready, col = self.project.get_colormetry()
            if not ready:
                self.start_colormetry()
            else:
                print("SetColormetry")
                self.timeline.timeline.set_colormetry_progress(1.0)
        print("LOADED:", self.project.name)

    def dispatch_on_changed(self, receiver = None, item = None):
        if self.project is None or not self.allow_dispatch_on_change:
            return

        if receiver is not None:
            for r in receiver:
                r.on_changed(self.project, item)
        else:
            for o in self.i_project_notify_reciever:
                o.on_changed(self.project, item)
        # self.player.on_changed(self.project)
        # self.drawing_overlay.on_changed(self.project)
        # self.annotation_viewer.on_changed(self.project)
        # self.screenshots_manager.on_changed(self.project)
        # self.timeline.timeline.on_changed(self.project)
        # self.outliner.on_changed(self.project)

    def dispatch_on_selected(self, sender, selected):
        if self.project is None:
            return

        self.elan_status.set_selection(selected)
        for o in self.i_project_notify_reciever:
                o.on_selected(sender, selected)

    def dispatch_on_timestep_update(self, time):
        # self.timeline.timeline.on_timestep_update(time)
        if self.project is None:
            return

        frame = self.player.get_frame_pos_by_time(time)
        self.onTimeStep.emit(time)
        QCoreApplication.removePostedEvents(self.frame_update_worker)
        self.onUpdateFrame.emit(time, frame)


        # self.frame_update_worker.setMSPosition(time, frame)
        # self.frame_update_thread.start()

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



                    # self.drawing_overlay.on_timestep_update(time)


            #endregion
            # DEPRECATED
            # for l in self.project.annotation_layers:
            #     if l.is_visible:
            #
            #     if l.get_start() <= time <= l.get_end():
            #         if l.is_visible == False:
            #             l.is_visible = True
            #             for a in l.annotations:
            #                 if a.widget is not None:
            #                     a.widget.show()
            #                     a.widget.is_active = True
            #     else:
            #         if l.is_visible is True:
            #             l.is_visible = False
            #             for a in l.annotations:
            #                 if a.widget is not None:
            #                     a.widget.hide()
            #                     a.widget.is_active = False



                                        # self.drawing_overlay.on_timestep_update(time)


                                        # endregion

    def dispatch_on_closed(self):
        self.autosave_timer.stop()
        self.set_ui_enabled(False)

        for o in self.i_project_notify_reciever:
            o.on_closed()

    #endregion
    pass


class IconContainer():
    def __init__(self):
        path = os.path.abspath("qt_ui/icons/")
        self.movie_icon = QIcon(QPixmap(path + "icon_movie.png"))


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
        if self.settings.USER_NAME != "":
            self.may_proceed = True

    def on_ok(self):
        self.check_if_finished()
        self.settings.store()
        if self.may_proceed:
            self.close()
        else:
            QMessageBox.warning(self.main_window, "Please Fill out the Form", "Some information seems to be missing, please fill out the Form.")








