from core.gui.ewidgetbase import EDockWidget, EToolBar
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPixmap, QIcon
from core.data.interfaces import IProjectChangeNotify
import os
from core.gui.python_script_editor import PythonScriptEditor
from core.data.creation_events import VIANEventHandler, ALL_REGISTERED_PIPELINES, get_path_of_pipeline_script, get_name_of_script_by_path
from core.data.log import log_error, log_info, log_warning
from core.container.project import VIANProject
from core.data.computation import import_module_from_path, create_icon


class PipelineToolbar(EToolBar):
    onToComputeChanged = pyqtSignal(bool, bool, bool)
    runAll = pyqtSignal()

    def __init__(self, main_window):
        super(PipelineToolbar, self).__init__(main_window, "Windows Toolbar")
        self.setWindowTitle("Windows Toolbar")

        self.a_auto_screenshot = self.addAction(create_icon("qt_ui/icons/icon_pipeline_screenshot_off.png"), "Auto Pipeline Screenshots")
        self.a_auto_screenshot.setCheckable(True)
        self.a_auto_screenshot.setEnabled(False)
        self.a_auto_screenshot.triggered.connect(self.on_screenshot_checked_changed)

        self.a_auto_segment = self.addAction(create_icon("qt_ui/icons/icon_pipeline_segment_off.png"), "Auto Pipeline Segments")
        self.a_auto_segment.setCheckable(True)
        self.a_auto_segment.setEnabled(False)
        self.a_auto_segment.triggered.connect(self.on_segment_checked_changed)

        self.a_run_all = self.addAction(create_icon("qt_ui/icons/icon_pipeline_run_all.png"), "Run Complete Pipeline")
        self.a_run_all.triggered.connect(self.run_all)

        self.a_pipeline_settings = self.addAction(create_icon("qt_ui/icons/icon_pipeline_settings.png"), "Pipeline Configuration")
        self.a_pipeline_settings.triggered.connect(self.main_window.create_pipeline_widget)

        # self.lbl_status = QLabel("0 \n/ 0", self)
        # self.lbl_status.setWordWrap(True)
        # self.addWidget(self.lbl_status)

    def on_screenshot_checked_changed(self):
        if self.a_auto_screenshot.isChecked():
            self.a_auto_screenshot.setIcon(create_icon("qt_ui/icons/icon_pipeline_screenshot_on.png"))
        else:
            self.a_auto_screenshot.setIcon(create_icon("qt_ui/icons/icon_pipeline_screenshot_off.png"))
        self.on_update_to_compute()

    def on_segment_checked_changed(self):
        if self.a_auto_segment.isChecked():
            self.a_auto_segment.setIcon(create_icon("qt_ui/icons/icon_pipeline_segment_on.png"))
        else:
            self.a_auto_segment.setIcon(create_icon("qt_ui/icons/icon_pipeline_segment_off.png"))
        self.on_update_to_compute()

    def set_to_compute(self, comp_segments, comp_screenshots, comp_annotations):
        if comp_segments:
            self.a_auto_segment.setChecked(True)
            self.a_auto_segment.setIcon(create_icon("qt_ui/icons/icon_pipeline_segment_on.png"))
        else:
            self.a_auto_segment.setIcon(create_icon("qt_ui/icons/icon_pipeline_segment_off.png"))

        if comp_screenshots:
            self.a_auto_screenshot.setChecked(True)
            self.a_auto_screenshot.setIcon(create_icon("qt_ui/icons/icon_pipeline_screenshot_on.png"))
        else:
            self.a_auto_screenshot.setIcon(create_icon("qt_ui/icons/icon_pipeline_screenshot_off.png"))

    def on_update_to_compute(self):
        comp_screenshots = self.a_auto_screenshot.isChecked()
        comp_segments = self.a_auto_segment.isChecked()
        comp_annotations = False

        if self.main_window.project is not None:
            self.main_window.project.compute_pipeline_settings = dict(segments=comp_segments,
                                                          screenshots=comp_screenshots,
                                                          annotations=comp_annotations)

        self.onToComputeChanged.emit(comp_segments, comp_screenshots, comp_annotations)

    @pyqtSlot(object)
    def on_current_pipeline_changed(self, pipeline):
        if pipeline is None:
            self.a_auto_segment.setEnabled(False)
            self.a_auto_screenshot.setEnabled(False)
        else:
            self.a_auto_screenshot.setEnabled(True)
            self.a_auto_segment.setEnabled(True)

    def run_all(self):
        self.runAll.emit()

class PipelineDock(EDockWidget):
    def __init__(self, parent, event_manager):
        super(PipelineDock, self).__init__(parent, False)
        self.setWindowTitle("Pipeline Manager")
        self.pipeline = PipelineWidget(self, event_manager, self.main_window)
        self.splitter = QSplitter(Qt.Horizontal)
        self.inner.setCentralWidget(self.splitter)
        self.inner.centralWidget().setLayout(QHBoxLayout())

        self.splitter.addWidget(self.pipeline)
        self.editor = PythonScriptEditor(self.inner.centralWidget())
        self.splitter.addWidget(self.editor)
        self.editor.onReload.connect(self.pipeline.on_reload_scripts)

        self.pipeline.onPipelineActivated.connect(self.on_active_pipeline_changed)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)

    def on_active_pipeline_changed(self, name):
        script_path = get_path_of_pipeline_script(name)
        if script_path is not None and os.path.isfile(script_path):
            self.editor.load(script_path)


class PipelineWidget(QWidget):
    onPipelineActivated = pyqtSignal(str)
    onPipelineFinalize = pyqtSignal()
    onToComputeChanged = pyqtSignal(bool, bool, bool)
    onRunAnalysis = pyqtSignal(object)

    def __init__(self, parent, event_manager: VIANEventHandler, main_window):
        super(PipelineWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/PipelineWidget.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.project = None #type: VIANProject

        self.btn_onSegment.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}" + "QPushButton:checked{background-color: rgb(10, 100, 10);}")
        self.btn_onScreenshot.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}" + "QPushButton:checked{background-color: rgb(10, 100, 10);}")
        self.btn_onAnnotation.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}" + "QPushButton:checked{background-color: rgb(10, 100, 10);}")

        self.btn_onSegment.clicked.connect(self.on_update_to_compute)
        self.btn_onScreenshot.clicked.connect(self.on_update_to_compute)
        self.btn_onAnnotation.clicked.connect(self.on_update_to_compute)
        self.btn_Finalize.clicked.connect(self.on_pipeline_finalize)

        self.btn_usePipeline.clicked.connect(self.on_use_pipeline)
        self.current_item = None
        self.all_items = dict()

        self.event_manager = event_manager
        self.on_reload_scripts()

    def on_reload_scripts(self):
        last_selection = None
        if self.current_item is not None:
            last_selection = self.current_item.text()
            self.current_item = None

        self.listWidget_Pipelines.clear()
        self.all_items.clear()

        for pipeline in ALL_REGISTERED_PIPELINES.keys():
            itm = QListWidgetItem(pipeline)
            self.listWidget_Pipelines.addItem(itm)
            if last_selection is not None and pipeline == last_selection:
                self.listWidget_Pipelines.setCurrentItem(itm)
                self.on_use_pipeline()
            self.all_items[pipeline] = itm

    def set_to_compute(self, comp_segments, comp_screenshots, comp_annotations):
        self.btn_onSegment.setChecked(comp_segments)
        self.btn_onScreenshot.setChecked(comp_screenshots)
        self.btn_onAnnotation.setChecked(comp_annotations)

        self.on_update_to_compute()

    def on_update_to_compute(self):
        comp_segments = self.btn_onSegment.isChecked()
        comp_annotations = self.btn_onAnnotation.isChecked()
        comp_screenshots = self.btn_onScreenshot.isChecked()

        if self.project is not None:
            self.project.compute_pipeline_settings = dict(segments=comp_segments,
                                                          screenshots=comp_screenshots,
                                                          annotations=comp_annotations)

        self.onToComputeChanged.emit(comp_segments, comp_screenshots, comp_annotations)

    def on_use_pipeline(self):
        if self.current_item is not None:
            self.current_item.setForeground(QColor(69,69,69))

        if self.listWidget_Pipelines.currentItem() is None:
            return

        pipeline_name = self.listWidget_Pipelines.currentItem().text()

        self.current_item = self.listWidget_Pipelines.currentItem()
        if self.current_item is not None:
            self.current_item.setForeground(QColor(69, 200, 69))

        self.onPipelineActivated.emit(pipeline_name)
        if self.project is not None and pipeline_name in ALL_REGISTERED_PIPELINES:
            self.project.add_pipeline_script(get_path_of_pipeline_script(pipeline_name))
            self.project.active_pipeline_script = get_path_of_pipeline_script(pipeline_name)

    def on_pipeline_finalize(self):
        self.onPipelineFinalize.emit()

    @pyqtSlot()
    def run_all(self):
        if self.project is not None:
            missing_info = self.project.get_missing_analyses(self.main_window.vian_event_handler.current_pipeline.requirements)
            missing = dict()
            for k in missing_info.keys():
                missing.update(missing_info[k][0])
            print(missing)
            experiment = self.project.get_experiment_by_name(self.main_window.vian_event_handler.current_pipeline.template)
            if experiment is None:
                return

            for priority in sorted(missing.keys()):
                for analysis_name in missing[priority].keys():
                    analysis = self.main_window.eval_class(analysis_name)
                    for clobj_name, containers in missing[priority][analysis_name].items():
                        clobj = experiment.get_classification_object_by_name(clobj_name)

                        if clobj is None:
                            log_warning("Classification Object not found")
                            continue
                        d = dict(
                            analysis=analysis(),
                            targets=containers,
                            parameters=None,
                            classification_objs=clobj
                        )
                        log_info("Pipeline Analysis: ", priority, analysis_name, clobj_name)
                        self.onRunAnalysis.emit(d)

    @pyqtSlot(object)
    def on_loaded(self, project:VIANProject):
        self.project = project

        for p in project.pipeline_scripts:
            log_info("Pipeline in Project:", p)
            try:
                import_module_from_path(p)
            except Exception as e:
                raise e
                log_error("Exception during loading of Script:", e)
        self.on_reload_scripts()
        module_name = get_name_of_script_by_path(project.active_pipeline_script)

        if module_name is not None and module_name in self.all_items:
            self.listWidget_Pipelines.setCurrentItem(self.all_items[module_name])

        self.btn_onSegment.setChecked(project.compute_pipeline_settings['segments'])
        self.btn_onScreenshot.setChecked(project.compute_pipeline_settings['screenshots'])
        self.btn_onAnnotation.setChecked(project.compute_pipeline_settings['annotations'])

        self.on_use_pipeline()
        self.on_update_to_compute()
