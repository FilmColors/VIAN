# from PyQt4 import QtCore, QtGui, uic

# from annotation_viewer import AnnotationViewer
import webbrowser
import cProfile
import os
import glob
import cv2
from core.concurrent.worker import Worker


import importlib
from functools import partial

from core.concurrent.worker_functions import *
from core.data.enums import *
from core.data.importers import ELANProjectImporter
from core.data.masterfile import MasterFile
from core.data.project_streaming import ProjectStreamerShelve, NumpyDataManager
from core.data.settings import UserSettings
from core.data.vian_updater import VianUpdater
from core.data.exporters import zip_project
# from core.gui.Dialogs.SegmentationImporterDialog import SegmentationImporterDialog
from core.gui.Dialogs.elan_opened_movie import ELANMovieOpenDialog
from core.gui.Dialogs.export_segmentation_dialog import ExportSegmentationDialog
from core.gui.Dialogs.export_template_dialog import ExportTemplateDialog
from core.gui.Dialogs.new_project_dialog import NewProjectDialog
from core.gui.Dialogs.preferences_dialog import DialogPreferences
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
from core.gui.player_vlc import Player_VLC
# from core.gui.shots_window import ScreenshotsManagerWidget, ScreenshotsToolbar, ScreenshotsManagerDockWidget
from core.gui.screenshot_manager import ScreenshotsManagerWidget, ScreenshotsToolbar, ScreenshotsManagerDockWidget
from core.gui.status_bar import StatusBar, OutputLine, StatusProgressBar, StatusVideoSource
from core.gui.timeline import TimelineContainer
from core.gui.vocabulary import VocabularyManager, VocabularyExportDialog, VocabularyMatrix
from core.node_editor.node_editor import NodeEditorDock
from core.node_editor.script_results import NodeEditorResults
from core.remote.corpus.client import CorpusClient
from core.remote.corpus.corpus import *
from core.remote.elan.server.server import QTServer
from extensions.extension_list import ExtensionList
from core.concurrent.timestep_update import TimestepUpdateWorkerSingle


from core.analysis.colorimetry.colorimetry import ColometricsAnalysis
from core.analysis.movie_mosaic.movie_mosaic import MovieMosaicAnalysis
__author__ = "Gaudenz Halter"
__copyright__ = "Copyright 2017, Gaudenz Halter"
__credits__ = ["Gaudenz Halter", "FIWI, University of Zurich", "VMML, University of Zurich"]
__license__ = "GPL"
__version__ = "0.4.1"
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

    def __init__(self,vlc_instance, vlc_player):
        super(MainWindow, self).__init__()
        path = os.path.abspath("qt_ui/MainWindow.ui")
        uic.loadUi(path, self)

        if PROFILE:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
        loading_screen = LoadingScreen()
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


        self.menuWindows.addMenu(self.extension_list.get_plugin_menu(self.menuWindows))
        self.menuAnalysis.addMenu(self.extension_list.get_analysis_menu(self.menuAnalysis, self))

        self.settings = UserSettings()
        self.settings.load()

        self.master_file = MasterFile(self.settings)
        self.master_file.load()
        self.icons = IconContainer()

        self.corpus_client = CorpusClient(self.settings.USER_NAME)
        self.corpus_client.send_connect(self.settings.USER_NAME)
        if self.settings.USE_CORPUS:
            self.corpus_client.start()


        self.vlc_instance = vlc_instance
        self.vlc_player = vlc_player

        self.updater = VianUpdater(self, self.version)

        self.key_event_handler = EKeyEventHandler(self)

        # Central Widgets
        self.video_player = None
        self.screenshots_manager = None

        self.allow_dispatch_on_change = True

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(8)

        self.numpy_data_manager = NumpyDataManager(self)
        self.project_streamer = ProjectStreamerShelve(self)
        self.video_capture = None


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

        # This is the Widget created when Double Clicking on a Annotation
        # This is store here, because is has to be removed on click, and because the background of the DrawingWidget
        # is Transparent
        self.drawing_editor = None
        self.concurrent_task_viewer = None

        self.dock_widgets = []

        # self.player = Player_VLC(self)
        self.player = Player_VLC(self)

        self.server = QTServer(self.player)
        self.server.player = self.player
        if self.settings.USE_ELAN:
            self.server.start()

        self.project = ElanExtensionProject(self, "","Default Project")

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
        self.actionNew.triggered.connect(self.action_new_project)
        self.actionLoad.triggered.connect(self.on_load_project)
        self.actionSave.triggered.connect(self.on_save_project)
        self.actionSaveAs.triggered.connect(self.on_save_project_as)

        self.actionImportELANSegmentation.triggered.connect(self.import_segmentation)
        self.action_importELAN_Project.triggered.connect(self.import_elan_project)
        self.actionImportVocabulary.triggered.connect(self.import_vocabulary)

        self.action_ExportSegmentation.triggered.connect(self.export_segmentation)
        self.actionExportTemplate.triggered.connect(self.export_template)
        self.actionExportVocabulary.triggered.connect(self.export_vocabulary)
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

        self.actionPlayerPersp.triggered.connect(partial(self.switch_perspective, Perspective.VideoPlayer.name))
        self.actionAnnotationPersp.triggered.connect(partial(self.switch_perspective, Perspective.Annotation.name))
        self.actionScreenshotsPersp.triggered.connect(partial(self.switch_perspective, Perspective.ScreenshotsManager.name))
        self.actionAnalysisPerspective.triggered.connect(partial(self.switch_perspective, Perspective.Analyses.name))
        self.actionSegmentationPersp.triggered.connect(partial(self.switch_perspective, Perspective.Segmentation.name))

        self.actionHistory.triggered.connect(self.create_history_view)
        self.actionTaksMonitor.triggered.connect(self.create_concurrent_task_viewer)
        self.actionAdd_Annotation_Layer.triggered.connect(self.on_new_annotation_layer)
        self.actionAdd_Segmentation.triggered.connect(self.on_new_segmentation)

        self.actionScreenshot.triggered.connect(self.on_screenshot)
        self.actionAdd_Key.triggered.connect(self.on_key_annotation)
        self.actionAdd_Segment.triggered.connect(self.on_new_segment)
        self.actionAbout.triggered.connect(self.on_about)
        self.actionWelcome.triggered.connect(self.show_welcome)
        self.actionIncreasePlayRate.triggered.connect(self.increase_playrate)
        self.actionDecreasePlayRate.triggered.connect(self.decrease_playrate)

        self.actionColorimetry.triggered.connect(partial(self.analysis_triggered, ColometricsAnalysis()))
        self.actionMovie_Mosaic.triggered.connect(partial(self.analysis_triggered, MovieMosaicAnalysis()))

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
                                          ]


        # self.actionElanConnection.triggered.connect(self.create_widget_elan_status)
        # self.actionShots.triggered.connect(self.create_widget_shots_window)





        # Autosave
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.on_save_project, False)
        self.update_autosave_timer()

        self.time_update_interval = 100
        self.update_timer = QtCore.QTimer()
        self.update_timer.setTimerType(Qt.PreciseTimer)
        self.update_timer.setInterval(self.time_update_interval)
        self.update_timer.timeout.connect(self.signal_timestep_update)

        self.time = 0
        self.time_counter = 0
        self.clock_synchronize_step = 5
        self.last_segment_index = 0

        self.current_perspective = Perspective.Annotation.name

        self.player.movieOpened.connect(self.on_movie_opened, QtCore.Qt.QueuedConnection)
        self.player.started.connect(self.start_update_timer, QtCore.Qt.QueuedConnection)
        self.player.stopped.connect(self.update_timer.stop, QtCore.Qt.QueuedConnection)
        self.player.timeChanged.connect(self.dispatch_on_timestep_update, QtCore.Qt.AutoConnection)

        self.player.started.connect(partial(self.frame_update_worker.set_opencv_frame, False))
        self.player.stopped.connect(partial(self.frame_update_worker.set_opencv_frame, True))

        self.drawing_overlay.onSourceChanged.connect(self.source_status.on_source_changed)
        self.dispatch_on_changed()

        self.screenshot_blocked = False

        # self.menuAnalysis.addMenu("Extensions")

        self.analyzes_list =[
            # HilbertHistogramProc(0)
        ]

        self.is_selecting_analyzes = False

        loading_screen.hide()

        self.update_recent_menu()
        self.switch_perspective(Perspective.Segmentation.name)

        # self.load_project("projects/ratatouille/Ratatouille.eext")

        # SEGMENT EVALUATOR
        # self.current_segment_evaluator = CurrentSegmentEvaluater()
        # self.player.started.connect(self.current_segment_evaluator.play)
        # self.player.stopped.connect(self.current_segment_evaluator.pause)
        # self.onTimeStep.connect(self.current_segment_evaluator.set_time)
        # self.current_segment_evaluator.signals.segmentChanged.connect(self.currentSegmentChanged.emit)
        # self.thread_pool.start(self.current_segment_evaluator)

        self.show()

        self.setWindowState(Qt.WindowMaximized)

        if self.settings.SHOW_WELCOME:
           self.show_welcome()

        if self.settings.USER_NAME == "":
            self.show_first_start()

        self.player_controls.setState(False)
        self.timeline.timeline.setState(False)

    def print_time(self, segment):
        print(segment)

    def test_function(self):
        print(self.player.get_fps())

    #region WidgetCreation

    def export_template(self):
        dialog = ExportTemplateDialog(self)
        dialog.show()

    def show_welcome(self):
        welcome_dialog = WelcomeDialog(self, self)
        welcome_dialog.raise_()

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

    def create_widget_video_player(self):
        if self.video_player is None:
            # #DARWIN
            # if self.is_darwin:  # for MacOS
            #     self.player_container.show()
            #     self.setCentralWidget(self.player_placeholder)
            # else:
            self.setCentralWidget(self.player)
        else:
            self.video_player.activateWindow()

#OLD CODE

    def create_annotation_toolbar(self):
        if self.annotation_toolbar is None:
            self.annotation_toolbar = AnnotationToolbar(self, self.drawing_overlay)
            self.addToolBar(self.annotation_toolbar)
            # self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.annotation_toolbar)
        else:
            self.annotation_toolbar.show()
            self.annotation_toolbar.raise_()
            self.annotation_toolbar.activateWindow()

    # def create_analyses_widget(self):
    #     if self.analyses_widget is None:
    #         self.analyses_widget = AnalysesWidget(self)
    #         self.analyses_widget.hide()
    #
    #     else:
    #         self.analyses_widget.activateWindow()

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
            self.inspector.show()
            self.inspector.raise_()
            self.inspector.activateWindow()

    def create_concurrent_task_viewer(self):
        if self.concurrent_task_viewer is None:
            self.concurrent_task_viewer = ConcurrentTaskDock(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.concurrent_task_viewer)
        else:
            self.concurrent_task_viewer.show()
            self.concurrent_task_viewer.raise_()
            self.concurrent_task_viewer.activateWindow()

    def create_history_view(self):
        if self.history_view is None:
            self.history_view = HistoryView(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.history_view)
        else:
            self.history_view.show()

    def create_screenshots_toolbar(self):
        if self.screenshot_toolbar is None:
            self.screenshot_toolbar = ScreenshotsToolbar(self, self.screenshots_manager)
            self.addToolBar(self.screenshot_toolbar)
            #self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.screenshot_toolbar)
        else:
            self.screenshot_toolbar.show()
            self.screenshot_toolbar.raise_()
            self.screenshot_toolbar.activateWindow()

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
            self.outliner.show()
            self.outliner.raise_()
            self.outliner.activateWindow()

    def create_timeline(self):
        if self.timeline is None:
            self.timeline = TimelineContainer(self)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.timeline, QtCore.Qt.Vertical)
            # self.on_movie_updated()
        else:
            self.timeline.activateWindow()

    def create_screenshot_manager_dock_widget(self):
        if self.screenshots_manager_dock is None:
            self.screenshots_manager_dock = ScreenshotsManagerDockWidget(self)
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.screenshots_manager_dock, QtCore.Qt.Horizontal)
            # self.on_movie_updated()
            self.screenshots_manager_dock.set_manager(self.screenshots_manager)
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
            self.vocabulary_matrix = VocabularyMatrix(self)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.vocabulary_matrix, QtCore.Qt.Vertical)
        else:
            self.vocabulary_matrix.show()
            self.vocabulary_matrix.raise_()
            self.vocabulary_matrix.activateWindow()
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
        self.screenshots_manager.ctrl_is_pressed = True
        self.timeline.timeline.is_scaling = True


    def keyReleaseEvent(self, event):
        self.screenshots_manager.ctrl_is_pressed = False
        self.timeline.timeline.is_scaling = False


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

    def update_vian(self):
        result = self.updater.get_server_version()
        if result:
            answer = QMessageBox.question(self, "Update Available", "A new Update is available, and will be updated now.\nVIAN will close after the Update. Please do not Update before you have saved the current Project. \n\n Do you want to Update now?")
            if answer == QMessageBox.Yes:
                self.updater.update()
            else:
                self.print_message("Update Aborted", "Orange")
        else:
            QMessageBox.information(self, "VIAN Up to Date", "VIAN is already on the newest version: " + self.version)

    def open_preferences(self):
        dialog = DialogPreferences(self)
        dialog.show()

    def on_movie_opened(self):
        if self.player.movie_path != self.project.get_movie().movie_path:
            dialog = ELANMovieOpenDialog(self, self.master_file, self.player.movie_path)
            dialog.show()
        self.player_controls.on_play()

    def action_new_project(self):
        self.on_new_project()

    def on_new_project(self, movie_path = ""):
        # self.set_darwin_player_visibility(False)
        self.update()

        if self.project.undo_manager.has_modifications():
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
            self.project.apply_template(template_path)

        self.project.create_file_structure()
        # Importing all Vocabularies
        for i, v in enumerate(vocabularies):
            print("Importing: " + str(i) + " " + v + "\r")
            self.project.import_vocabulary(v)

        # self.player.open_movie(project.movie_descriptor.movie_path)
        self.master_file.add_project(project)
        self.project.store_project(self.settings, self.master_file)

        self.project.inhibit_dispatch = False
        self.dispatch_on_loaded()

    def on_load_project(self):
        if self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()

        self.set_overlay_visibility(False)
        path = QFileDialog.getOpenFileName(filter="*" + self.settings.PROJECT_FILE_EXTENSION, directory=self.settings.DIR_PROJECT)
        self.set_overlay_visibility(True)
        path = path[0]
        self.close_project()
        self.load_project(path)

    def close_project(self):
        if self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()

        self.player.stop()
        self.abortAllConcurrentThreads.emit()
        self.project.cleanup()
        self.project = ElanExtensionProject(self, name="No Project")
        print(len(self.project.screenshots))

        #self.project_streamer.release_project()


        #self.project_streamer.set_project(self.project)
        self.player_controls.setState(False)
        self.timeline.timeline.setState(False)

        self.dispatch_on_changed()

    def load_project(self, path):

        if path == "" or path is None:
            self.print_message("Not Loaded, Path was Empty")
            return



        new = ElanExtensionProject(self)
        print("Loading Project Path", path)
        new.inhibit_dispatch = True
        new.load_project(self.settings ,path)



        self.project = new
        self.settings.add_to_recent_files(self.project)
        self.update_recent_menu()

        new.inhibit_dispatch = False
        #self.project_streamer.set_project(new)
        self.dispatch_on_loaded()

    def on_save_project(self, open_dialog=False):
        if not self.has_open_project:
            self.print_message("No Project Open", "red")
            return

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

        worker = Worker(store_project_concurrent, self, None, args, msg_finished="Project Saved")
        self.start_worker(worker, "Saving Project")

        self.corpus_client.send_update_project(ProjectData().from_EEXTProject(self.project))


        return

    def on_save_project_as(self):
        self.on_save_project(True)

    def on_exit(self):
        self.drawing_overlay.close()
        self.vlc_player.release()
        self.vlc_instance.release()
        self.corpus_client.send_disconnect(self.settings.USER_NAME)

        if PROFILE:
            self.profiler.disable()
            self.profiler.dump_stats("Profile.prof")

        self.settings.store()

        if self.project.undo_manager.has_modifications():
            answer = QMessageBox.question(self, "Save Project", "Do you want to save the current Project?")
            if answer == QMessageBox.Yes:
                self.on_save_project()

        self.frame_update_thread.quit()

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

    def run_job_concurrent(self, job):
        job.prepare()
        worker = Worker(job.run_concurrent, self, self.on_job_concurrent_result, job.args, msg_finished="Screenshots Loaded", concurrent_job=job)
        self.abortAllConcurrentThreads.connect(job.abort)
        self.start_worker(worker, "Job")

    def on_job_concurrent_result(self, result):
        res = result[0]
        job = result[1]
        self.allow_dispatch_on_change = False

        # progress = None
        # if job.show_modify_progress:
        #     progress = DialogProgress(self, "Modifying Project")
        #
        # worker = ProjectModifier(job.modify_project, res, self, self.project, progress)
        # self.thread_pool.start(worker)
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

    def import_segmentation(self):
        QMessageBox.warning(self, "Deprecated", "The Segmentation Importer is deprecated and therefore removed from VIAN.\n "
                                          "For ELAN Projects use the \"ELAN Project Importer\". \n "
                                          "A new Version for importing arbitary Segmentations is planned but not yet included.")
        # SegmentationImporterDialog(self, self.project, self)

    def import_elan_project(self):
        try:
            path = QFileDialog.getOpenFileName(self, filter="*.eaf")[0]
            #path = path.replace("file:///", "")
            #path = path.replace("file:", "")

            path = parse_file_path(path)

            importer = ELANProjectImporter(self, remote_movie=True, import_screenshots=True)
            self.project = importer.import_project(path)

            self.project.main_window = self
            self.project.dispatch_loaded()
            self.print_message("Import Successfull", "Green")
        except Exception as e:
            self.print_message("Import Failed", "Red")
            self.print_message("This is a serious Bug, please report this message, together with your project to Gaudenz Halter", "Red")
            self.print_message(str(e), "Red")

    def import_vocabulary(self):
        path = QFileDialog.getOpenFileName(directory=self.project.export_dir)[0]
        try:
            self.project.import_vocabulary(path)
        except Exception as e:
            self.print_message("Vocabulary Import Failed", "Red")
            self.print_message(str(e), "Red")

    def export_segmentation(self):
        # path = QFileDialog.getSaveFileName(directory=self.project.path, filter=".txt")[0]
        dialog = ExportSegmentationDialog(self)
        dialog.show()

    def export_vocabulary(self):
        dialog = VocabularyExportDialog(self)
        dialog.show()

    def on_zip_project(self):
        try:
            zip_project(self.project.export_dir + "/" + self.project.name, self.project.folder)
        except Exception as e:
            self.print_message("Zipping Project Failed", "Red")
            self.print_message(str(e), "Red")

    def print_message(self, msg, color = "green"):
        self.output_line.print_message(msg, color)

    def switch_perspective(self, perspective):
        # DARWIN
        # if self.is_darwin:
        #     central = self.player_placeholder
        # else:

        central = self.player

        self.centralWidget().setParent(None)
        if perspective == Perspective.VideoPlayer.name:
            self.current_perspective = Perspective.VideoPlayer
            central = self.player

            self.drawing_overlay.hide()
            self.outliner.hide()
            self.annotation_toolbar.hide()
            self.screenshot_toolbar.hide()
            self.timeline.hide()
            self.player_controls.hide()
            self.perspective_manager.hide()
            self.inspector.hide()
            self.history_view.hide()
            self.concurrent_task_viewer.hide()
            self.node_editor_dock.hide()
            self.node_editor_results.hide()
            self.screenshots_manager_dock.hide()
            self.vocabulary_manager.hide()
            self.vocabulary_matrix.hide()

        elif perspective == Perspective.Segmentation.name:
            self.current_perspective = Perspective.Segmentation
            central = self.player

            self.drawing_overlay.hide()
            self.outliner.hide()
            self.annotation_toolbar.hide()
            self.screenshot_toolbar.hide()
            self.timeline.show()
            self.player_controls.show()
            self.perspective_manager.hide()
            self.inspector.hide()
            self.history_view.hide()
            self.concurrent_task_viewer.hide()
            self.node_editor_dock.hide()
            self.node_editor_results.hide()
            self.screenshots_manager_dock.show()
            self.vocabulary_manager.hide()
            self.vocabulary_matrix.hide()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)

        elif perspective == Perspective.Annotation.name:
            self.current_perspective = Perspective.Annotation
            central = self.player

            self.drawing_overlay.show()
            self.outliner.show()
            self.annotation_toolbar.show()
            self.screenshot_toolbar.hide()
            self.timeline.show()
            self.history_view.hide()
            self.perspective_manager.hide()
            self.player_controls.hide()
            self.annotation_toolbar.raise_()
            self.inspector.show()
            self.screenshots_manager_dock.set_manager(self.screenshots_manager)
            self.screenshots_manager_dock.hide()
            self.node_editor_dock.hide()
            self.vocabulary_manager.hide()
            self.node_editor_results.hide()
            self.vocabulary_matrix.hide()

            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector)
            self.splitDockWidget(self.inspector, self.outliner, Qt.Vertical)
            # self.concurrent_task_viewer.show()
            # self.history_view.show()

        elif perspective == Perspective.ScreenshotsManager.name:
            self.current_perspective = Perspective.ScreenshotsManager
            self.screenshots_manager.update_manager()

            # central = self.screenshots_manager
            # central.center_images()
            central = QWidget(self)
            central.setFixedWidth(0)

            self.drawing_overlay.hide()
            self.annotation_toolbar.hide()
            self.screenshot_toolbar.show()
            self.timeline.hide()
            self.player_controls.hide()
            self.screenshot_toolbar.raise_()
            self.outliner.show()
            self.history_view.hide()
            self.screenshots_manager.center_images()
            self.screenshots_manager_dock.show()
            self.node_editor_dock.hide()
            self.node_editor_results.hide()
            self.vocabulary_manager.hide()
            self.vocabulary_matrix.hide()
            self.inspector.show()

            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.splitDockWidget(self.inspector, self.outliner, Qt.Vertical)

        elif perspective == Perspective.Analyses.name:
            self.current_perspective = Perspective.Analyses

            # if self.is_darwin:
            #     self.player_container.hide()

            # central = self.analyses_widget
            central = QWidget(self)
            central.setFixedWidth(0)

            self.drawing_overlay.hide()
            self.outliner.show()
            self.annotation_toolbar.hide()
            self.screenshot_toolbar.hide()
            self.timeline.hide()
            self.player_controls.hide()
            self.screenshot_toolbar.raise_()
            self.history_view.hide()
            self.node_editor_dock.show()
            self.screenshots_manager_dock.hide()
            self.node_editor_results.show()
            self.vocabulary_manager.hide()

            self.addDockWidget(Qt.LeftDockWidgetArea, self.outliner)
            self.addDockWidget(Qt.RightDockWidgetArea, self.inspector, Qt.Horizontal)
            self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)



        self.setCentralWidget(central)
        self.centralWidget().show()
        # self.centralWidget().setBaseSize(size_central)


        if perspective != Perspective.Annotation.name:
            self.set_overlay_visibility(False)

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

    def on_save_custom_perspective(self):
        setting = QSettings("UniversityOfZurich", "VIAN")
        setting.setValue("geometry", self.saveGeometry())
        setting.setValue("windowState", self.saveState())

    def on_load_custom_perspective(self):
        setting = QSettings("UniversityOfZurich", "VIAN")
        self.restoreGeometry(setting.value("geometry"))
        self.restoreState(setting.value("windowState"))

    def start_worker(self, worker, name = "New Task"):
        self.concurrent_task_viewer.add_task(worker.task_id, name)
        self.thread_pool.start(worker)

    def update_player_size(self):
        self.player.update()
    # endregion

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
    #region MISC
    def update_autosave_timer(self):
        self.autosave_timer.stop()
        if  self.settings.AUTOSAVE:
            ms =  self.settings.AUTOSAVE_TIME * 60 * 1000
            self.autosave_timer.setInterval(ms)
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


    # def set_darwin_player_visibility(self, visibility):
    #     if self.is_darwin:
    #             self.player_container.setVisible(visibility)
    #             self.player_container.synchronize()

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

    def testfunction(self, a = None):
        print("**********************")
        print("Test function called")
        print(a)
        print(self.project.create_file_structure())
        print("**********************")
    #endregion

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
        screenshot_position = []
        screenshot_annotation_dicts = []

        self.has_open_project = True

        for o in self.i_project_notify_reciever:
            o.on_loaded(self.project)

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

        job = LoadScreenshotsJob([self.project.movie_descriptor.movie_path, screenshot_position, screenshot_annotation_dicts])
        self.run_job_concurrent(job)

        self.setWindowTitle("VIAN Project:" + str(self.project.path))
        self.dispatch_on_timestep_update(-1)
        print("LOADED")

    def dispatch_on_changed(self, receiver = None, item = None):
        if not self.allow_dispatch_on_change:
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
        self.elan_status.set_selection(selected)
        for o in self.i_project_notify_reciever:
                o.on_selected(sender, selected)

    def dispatch_on_timestep_update(self, time):
        # self.timeline.timeline.on_timestep_update(time)
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


class LoadingScreen(QtWidgets.QMainWindow):
    def __init__(self):
        super(LoadingScreen, self).__init__(None)
        self.lbl = QLabel(self)
        self.setFixedWidth(800)
        self.setFixedHeight(400)
        self.lbl.setPixmap(QPixmap(os.path.abspath("/qt_ui/images/loading_screen.png")))
        self.setCentralWidget(self.lbl)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.show()


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








