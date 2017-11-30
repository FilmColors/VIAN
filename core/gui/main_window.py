from functools import partial

# from PyQt4 import QtCore, QtGui, uic
from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QFileDialog, qApp, QLabel, QMessageBox, QWidget

# from annotation_viewer import AnnotationViewer
from core.concurrent.worker import Worker, ProjectModifier
from core.concurrent.worker_functions import *
from core.data.exporters import SegmentationExporter
from core.data.importers import ELANProjectImporter
from core.data.masterfile import MasterFile
from core.data.settings import UserSettings
from core.data.enums import *
from core.data.project_streaming import ProjectStreamer
from core.gui.Dialogs.SegmentationImporterDialog import SegmentationImporterDialog
from core.gui.Dialogs.elan_opened_movie import ELANMovieOpenDialog
from core.gui.Dialogs.new_project_dialog import NewProjectDialog
from core.gui.Dialogs.preferences_dialog import DialogPreferences
from core.gui.Dialogs.welcome_dialog import WelcomeDialog
from core.gui.Dialogs.progressbar_popup import DialogProgress
from core.gui.analyses_widget import AnalysesWidget
from core.gui.concurrent_tasks import ConcurrentTaskDock
from core.gui.history import HistoryView
from core.gui.inspector import Inspector
from core.gui.keyeventhandler import EKeyEventHandler
from core.gui.outliner import Outliner
from core.gui.perspectives import PerspectiveManager, Perspective
from core.gui.timeline import TimelineContainer
from core.gui.Dialogs.export_template_dialog import ExportTemplateDialog
from core.node_editor.node_editor import NodeEditorDock
from core.node_editor.script_results import NodeEditorResults
from core.remote.corpus.client import CorpusClient
from core.remote.corpus.corpus import *
from core.remote.elan.server.server import QTServer
from drawing_widget import DrawingOverlay, DrawingEditorWidget, AnnotationToolbar
from extensions.colormetrics.hilbert_colors import HilbertHistogramProc
from extensions.extension_list import ExtensionList
from player_controls import PlayerControls
from player_vlc import Player_VLC
from shots_window import ScreenshotsManagerWidget, ScreenshotsToolbar, ScreenshotsManagerDockWidget
from status_bar import StatusBar, OutputLine, StatusProgressBar
from core.gui.vocabulary import VocabularyManager
from core.data.vian_updater import VianUpdater

__author__ = "Gaudenz Halter"
__copyright__ = "Copyright 2017, Gaudenz Halter"
__credits__ = ["Gaudenz Halter", "FIWI, University of Zurich", "VMML, University of Zurich"]
__license__ = "GPL"
__version__ = "0.1.1"
__maintainer__ = "Gaudenz Halter"
__email__ = "gaudenz.halter@uzh.ch"
__status__ = "Production"


class MainWindow(QtWidgets.QMainWindow):
    onTimeStep = pyqtSignal(long)
    abortAllConcurrentThreads = pyqtSignal()

    def __init__(self,vlc_instance, vlc_player):
        super(MainWindow, self).__init__()
        path = os.path.abspath("qt_ui/MainWindow.ui")
        uic.loadUi(path, self)
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

        self.settings = UserSettings()
        self.settings.load()

        self.master_file = MasterFile(self.settings)
        self.master_file.load()
        self.icons = IconContainer()

        self.corpus_client = CorpusClient(self.settings.USER_NAME)
        self.corpus_client.send_connect(self.settings.USER_NAME)
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

        self.project_streamer = ProjectStreamer(self)


        # DockWidgets
        self.player_controls = None
        self.elan_status = None
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

        self.server.start()
        self.project = ElanExtensionProject(self, "","New Project")



        # In OSX the DockPanels are brocken with the libVLC binding,
        # To Avoid this problem, we create a new QMainWindow, holding the Player, floating above the
        # CentralWidget
        # if self.is_darwin:  # for MacOS
        #     self.player_placeholder = QWidget(self)
        #     self.player_container = MacPlayerContainer(self, self.player)


        self.create_widget_elan_status()
        self.create_widget_video_player()
        self.create_analyses_widget()
        self.drawing_overlay = DrawingOverlay(self, self.player.videoframe, self.project)
        self.create_annotation_toolbar()
        # self.create_annotation_viewer()
        # self.create_screenshot_editor()
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



        self.splitDockWidget(self.player_controls, self.perspective_manager, Qt.Horizontal)
        self.splitDockWidget(self.inspector, self.node_editor_results, Qt.Vertical)

        # self.tabifyDockWidget(self.annotation_toolbar, self.screenshot_toolbar)
        self.tabifyDockWidget(self.inspector, self.history_view)

        self.tabifyDockWidget(self.inspector, self.concurrent_task_viewer)
        # self.tabifyDockWidget(self.inspector, self.screenshots_manager_dock)
        self.annotation_toolbar.raise_()
        self.inspector.raise_()
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
        self.action_ExportSegmentation.triggered.connect(self.export_segmentation)
        self.actionExportTemplate.triggered.connect(self.export_template)
        self.actionClose_Project.triggered.connect(self.close_project)
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

        self.actionSave_Perspective.triggered.connect(self.on_save_custom_perspective)
        self.actionLoad_Perspective.triggered.connect(self.on_load_custom_perspective)


        self.actionUpdate.triggered.connect(self.update_vian)
        self.actionPlay_Pause.triggered.connect(self.player.play_pause)
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
                                 self.vocabulary_manager]


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


        self.current_perspective = Perspective.Annotation.name


        self.player.movieOpened.connect(self.on_movie_opened, QtCore.Qt.QueuedConnection)
        self.player.started.connect(self.start_update_timer, QtCore.Qt.QueuedConnection)
        self.player.stopped.connect(self.update_timer.stop, QtCore.Qt.QueuedConnection)
        self.player.timeChanged.connect(self.dispatch_on_timestep_update, QtCore.Qt.AutoConnection)

        self.dispatch_on_changed()

        self.screenshot_blocked = False

        self.analyzes_list =[
            HilbertHistogramProc(0)
        ]

        self.is_selecting_analyzes = False

        loading_screen.hide()
        self.switch_perspective(Perspective.Annotation.name)

        # self.load_project("projects/ratatouille/Ratatouille.eext")



        self.showMaximized()
        if self.settings.SHOW_WELCOME:
           self.show_welcome()

        if self.settings.USER_NAME == "" and self.settings.UPDATE_SOURCE == "":
            self.show_first_start()


    def test_function(self):
        self.scale_screenshots(0.1)

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
            self.elan_status = StatusBar(self, self.server)
            self.output_line = OutputLine(self)
            self.progress_bar = StatusProgressBar(self)

            self.statusBar().addPermanentWidget(self.progress_bar)
            self.statusBar().addPermanentWidget(self.output_line)
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

    def create_analyses_widget(self):
        if self.analyses_widget is None:
            self.analyses_widget = AnalysesWidget(self)
            self.analyses_widget.hide()

        else:
            self.analyses_widget.activateWindow()

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
    #endregion

    #region QEvent Overrides
    def moveEvent(self, *args, **kwargs):
        QtWidgets.QMainWindow.moveEvent(self, *args, **kwargs)
        self.update()

    def closeEvent(self, *args, **kwargs):
        self.drawing_overlay.close()
        self.vlc_player.release()
        self.vlc_instance.release()
        self.corpus_client.send_disconnect(self.settings.USER_NAME)
        QtWidgets.QMainWindow.close(self)

    def resizeEvent(self, *args, **kwargs):
        QtWidgets.QMainWindow.resizeEvent(self, *args, **kwargs)
        self.update()

    def keyPressEvent(self, event):
        self.key_event_handler.pressEvent(event)
        self.update()

    def keyReleaseEvent(self, event):
        self.key_event_handler.releaseEvent(event)
        self.update()

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
    def update_vian(self):
        result = self.updater.get_server_version()
        if result:
            answer = QMessageBox.question(self, "Update Available", "A new Update is available, and will be updated now.\n\nDo you want to Update now?")
            if answer == QMessageBox.Yes:
                self.updater.update()
            else:
                self.print_message("Update Aborted", "Orange")


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
        if self.project is not None:
            self.project.cleanup()

        dialog = NewProjectDialog(self, self.settings, movie_path)
        dialog.show()

    def new_project(self, project, template_path = None):
        self.project = project
        if template_path is not None:
            self.project.apply_template(template_path)

        self.player.open_movie(project.movie_descriptor.movie_path)
        self.master_file.add_project(project)
        self.project.store_project(self.settings, self.master_file)
        self.dispatch_on_loaded()

    def on_load_project(self):
        self.set_overlay_visibility(False)
        path = QFileDialog.getOpenFileName(filter="*" + self.settings.PROJECT_FILE_EXTENSION, directory=self.settings.DIR_PROJECT)
        self.set_overlay_visibility(True)
        path = path[0]
        self.load_project(path)

    def close_project(self):
        self.project.cleanup()
        self.project = ElanExtensionProject(self, name="No Project")
        self.player.stop()
        #self.project_streamer.release_project()
        self.abortAllConcurrentThreads.emit()

        #self.project_streamer.set_project(self.project)
        self.dispatch_on_changed()

    def load_project(self, path):

        if path == "" or path is None:
            self.print_message("Not Loaded, Path was Empty")
            return

        self.close_project()

        new = ElanExtensionProject(self)
        print "Loading Project Path", path
        new.load_project(self.settings ,path)

        self.project = new

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
        self.on_save_project(False)
        QCoreApplication.quit()

    def on_undo(self):
        self.project.undo_manager.undo()

    def on_redo(self):
        self.project.undo_manager.redo()

    def on_delete(self):
        to_delete = self.project.selected

        for d in to_delete:
            d.delete()

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
        print "*********ERROR**IN**WORKER***********"
        print error
        print "*************************************"

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
        SegmentationImporterDialog(self, self.project, self)

    def import_elan_project(self):
        try:
            path = QFileDialog.getOpenFileName(self, filter="*.eaf")[0]
            #path = path.replace("file:///", "")
            #path = path.replace("file:", "")
            print path
            path = parse_file_path(path)
            print path
            importer = ELANProjectImporter(remote_movie=True, import_screenshots=True)
            self.project = importer.import_project(path)

            self.project.main_window = self
            self.project.dispatch_loaded()
            self.print_message("Import Successfull", "Green")
        except:
            self.print_message("Import Failed", "Red")

    def export_segmentation(self):
        path = QFileDialog.getSaveFileName(directory=self.project.path, filter=".txt")[0]
        path = parse_file_path(path)
        exporter = SegmentationExporter(path)
        segmentations = []
        for s in self.project.segmentation:
            segmentations.append(s.serialize())
        exporter.export(segmentations)
        self.print_message("Segmentation Exported to: " + path, "Green")

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

        elif perspective == Perspective.Annotation.name:
            self.current_perspective = Perspective.Annotation
            central = self.player

            self.drawing_overlay.show()
            self.outliner.show()
            self.annotation_toolbar.show()
            self.screenshot_toolbar.show()
            self.timeline.show()
            self.history_view.hide()
            self.player_controls.show()
            self.annotation_toolbar.raise_()
            self.inspector.show()
            self.screenshots_manager_dock.set_manager(self.screenshots_manager)
            self.screenshots_manager_dock.show()
            self.node_editor_dock.hide()
            self.vocabulary_manager.hide()
            self.node_editor_results.hide()
            # self.concurrent_task_viewer.show()
            # self.history_view.show()

        elif perspective == Perspective.ScreenshotsManager.name:
            self.current_perspective = Perspective.ScreenshotsManager
            self.screenshots_manager.update_manager()

            central = self.screenshots_manager
            central.center_images()

            self.drawing_overlay.hide()
            self.annotation_toolbar.show()
            self.screenshot_toolbar.show()
            self.timeline.hide()
            self.player_controls.hide()
            self.screenshot_toolbar.raise_()
            self.outliner.hide()
            self.history_view.hide()
            self.screenshots_manager.center_images()
            self.screenshots_manager_dock.hide()
            self.node_editor_dock.hide()
            self.node_editor_results.hide()
            self.vocabulary_manager.hide()

        elif perspective == Perspective.Analyses.name:
            self.current_perspective = Perspective.Analyses

            # if self.is_darwin:
            #     self.player_container.hide()

            # central = self.analyses_widget
            central = QWidget(self)
            central.setFixedWidth(0)

            self.drawing_overlay.hide()
            self.outliner.show()
            self.annotation_toolbar.show()
            self.screenshot_toolbar.show()
            self.timeline.hide()
            self.player_controls.hide()
            self.screenshot_toolbar.raise_()
            self.history_view.hide()
            self.node_editor_dock.show()
            self.screenshots_manager_dock.hide()
            self.node_editor_results.show()
            self.vocabulary_manager.hide()


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

    def on_start_analysis(self, analysis, target_id, args):
        worker = Worker(analysis.process, self, self.analysis_result, args, msg_finished="Hilbert Histogram Calculated", target_id=target_id)
        self.start_worker(worker, analysis.get_name())

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

    def analysis_result(self, result):
        self.project.add_analysis(result)

    def update_player_size(self):
        self.player.update()
    # endregion

    def on_about(self):
        about = ""
        about += "Author:".ljust(12) + __author__ + "\n"
        about += "Copyright:".ljust(12) + __copyright__ + "\n"
        about += "Version:".ljust(12) + __version__ + "\n"
        about += "Credits:".ljust(12) + str(__credits__) + "\n"
        QMessageBox.about(self, "About", about)

    def increase_playrate(self):
        self.player.set_rate(self.player.get_rate() + 0.1)

    def decrease_playrate(self):
        self.player.set_rate(self.player.get_rate() - 0.1)
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
        print "**********************"
        print "Test function called"
        print a
        print "**********************"
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

        job = LoadScreenshotsJob([self.project.movie_descriptor.movie_path, screenshot_position, screenshot_annotation_dicts])
        self.run_job_concurrent(job)

        self.setWindowTitle("VIAN Project:" + str(self.project.path))
        self.dispatch_on_timestep_update(-1)
        print "LOADED"

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
        self.onTimeStep.emit(time)

        if time == -1:
            for l in self.project.annotation_layers:
                l.is_visible = False
                for a in l.annotations:
                    a.widget.hide()
                    a.widget.is_active = False


        else:
            for l in self.project.annotation_layers:
                if l.get_start() <= time <= l.get_end():
                    if l.is_visible == False:
                        l.is_visible = True
                        for a in l.annotations:
                            a.widget.show()
                            a.widget.is_active = True
                else:
                    if l.is_visible is True:
                            l.is_visible = False
                            for a in l.annotations:
                                if a.widget is not None:
                                    a.widget.hide()
                                    a.widget.is_active = False



            # self.drawing_overlay.on_timestep_update(time)


    #endregion

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

        self.btn_BrowseSource.clicked.connect(self.btn_browse_vian_source)
        self.btn_OK.clicked.connect(self.on_ok)
        self.lineEdit_UpdateDir.textChanged.connect(self.update_directory_changed)
        self.lineEdit_UserName.editingFinished.connect(self.on_name_changed)

        self.show()


    def on_name_changed(self):
        name = self.lineEdit_UserName.text()
        self.settings.USER_NAME = name
        self.check_if_finished()

    def btn_browse_vian_source(self):
        source = QFileDialog.getExistingDirectory()
        self.lineEdit_UpdateDir.setText(source)

    def update_directory_changed(self):
        self.settings.UPDATE_SOURCE = self.lineEdit_UpdateDir.text()
        try:
            result = False
            with open(self.settings.UPDATE_SOURCE + "/VIAN/__version__.txt", "rb") as f:
                for l in f:
                    if "__version__" in l:
                        result = True
                        break
        except Exception as e:
            result = False
            print e

        if not result:
            QMessageBox.warning( self.main_window, "Couldn't open Update Path", "Couldn't Open Update Path.\n\nMake sure the path points to: \n <Some_Adress>/team/Software/VIAN/<Your_OS>")

        self.check_if_finished()

    def check_if_finished(self):
        print self.settings.USER_NAME, self.settings.UPDATE_SOURCE
        if self.settings.USER_NAME != "" and self.settings.UPDATE_SOURCE != "":
            self.may_proceed = True

    def on_ok(self):
        if self.may_proceed:
            self.close()
        else:
            QMessageBox.warning(self.main_window, "Please Fill out the Form", "Some information seems to be missing, please fill out the Form.")








