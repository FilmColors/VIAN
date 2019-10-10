import os
import glob
import sys
import importlib

from core.gui.ewidgetbase import EDockWidget, EToolBar
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QPixmap, QIcon, QMouseEvent
from core.data.interfaces import IProjectChangeNotify

from functools import partial
from core.gui.python_script_editor import PythonScriptEditor
from core.data.creation_events import VIANEventHandler, ALL_REGISTERED_PIPELINES, get_path_of_pipeline_script, get_name_of_script_by_path
from core.data.log import log_error, log_info, log_warning
from core.container.project import VIANProject
from core.container.analysis import PipelineScript
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
        self.editor = PythonScriptEditor(self.inner.centralWidget())
        self.pipeline = PipelineWidget(self, event_manager, self.main_window, self.editor)
        self.splitter = QSplitter(Qt.Horizontal)
        self.inner.setCentralWidget(self.splitter)
        self.inner.centralWidget().setLayout(QHBoxLayout())

        self.splitter.addWidget(self.pipeline)

        self.splitter.addWidget(self.editor)
        self.editor.onReload.connect(self.pipeline.on_reload_scripts)

        self.pipeline.onPipelineActivated.connect(self.on_active_pipeline_changed)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)

    def on_active_pipeline_changed(self, pipeline:PipelineScript):
        # script_path = get_path_of_pipeline_script(pipeline)
        # if script_path is not None and os.path.isfile(script_path):
        self.editor.load(pipeline.path)

    def on_pipeline_loaded(self, pipeline):
        if pipeline is not None:
            self.pipeline.check_missing()

    @pyqtSlot(bool)
    def set_is_loading(self, state):
        self.pipeline.set_is_loading(state)


class PipelineWidget(QWidget):
    onPipelineActivated = pyqtSignal(object)
    onPipelineFinalize = pyqtSignal()
    onToComputeChanged = pyqtSignal(bool, bool, bool)
    onRunAnalysis = pyqtSignal(object)

    def __init__(self, parent, event_manager: VIANEventHandler, main_window, editor):
        super(PipelineWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/PipelineWidget.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.project = None #type: VIANProject
        self.editor = editor

        self.btn_onSegment.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}" + "QPushButton:checked{background-color: rgb(10, 100, 10);}")
        self.btn_onScreenshot.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}" + "QPushButton:checked{background-color: rgb(10, 100, 10);}")
        self.btn_onAnnotation.setStyleSheet("QPushButton{background-color: rgb(100, 10, 10);}" + "QPushButton:checked{background-color: rgb(10, 100, 10);}")

        self.btn_onSegment.clicked.connect(self.on_update_to_compute)
        self.btn_onScreenshot.clicked.connect(self.on_update_to_compute)
        self.btn_onAnnotation.clicked.connect(self.on_update_to_compute)
        self.btn_Finalize.clicked.connect(self.on_pipeline_finalize)

        self.btn_usePipeline.clicked.connect(self.on_use_pipeline)
        self.pushButtonCheckMissing.clicked.connect(self.check_missing)
        self.pushButtonRunAll.clicked.connect(self.run_all)

        self.listWidget_Pipelines = PipelineListWidget(self, self)
        self.widgetInner.layout().addWidget(self.listWidget_Pipelines)
        self.comboBoxExperiment.currentTextChanged.connect(self.on_experiment_selected)
        self.current_item = None
        self.all_items = dict()

        self.all_experiments = dict()

        self.pipeline_library = dict()

        self.event_manager = event_manager
        self.on_reload_scripts()

    def update_library(self):
        log_info("Updating Pipeline Library")

        # Fetch all registered pipelines and create a PipelineScript for each
        self.pipeline_library = dict()
        to_remove = []
        if self.project is not None:
            for script in self.project.pipeline_scripts:
                script.import_pipeline()
                try:
                    script.uuid = ALL_REGISTERED_PIPELINES[script.name][0].uuid
                except AttributeError as e:
                    to_remove.append(script)
                    print(e)
                    continue

        for p in to_remove:
            self.project.remove_pipeline_script(p)

        project_pipelines = dict()
        for p in self.project.pipeline_scripts:
            project_pipelines[p.name] = p


        for k, (cl, path) in ALL_REGISTERED_PIPELINES.items():
            if k in project_pipelines:
                self.pipeline_library[k] = project_pipelines[k]
            else:
                if os.path.isfile(path):
                    with open(path, "r") as f:
                        content = f.read()
                    self.pipeline_library[k] = self.project.add_pipeline_script(
                        PipelineScript(name=cl.name, script=content, author=cl.author)
                    )
                    self.pipeline_library[k].save_script()

    def on_reload_scripts(self):
        # self.fetch_pipeline_scripts()
        last_selection = None
        if self.current_item is not None:
            last_selection = self.current_item.text()
            self.current_item = None

        self.listWidget_Pipelines.clear()
        self.all_items.clear()

        if self.project is None:
            return

        self.update_library()

        for name, pipeline in self.pipeline_library.items():
            itm = QListWidgetItem(name)
            self.listWidget_Pipelines.addItem(itm)
            if last_selection is not None and name == last_selection:
                self.listWidget_Pipelines.setCurrentItem(itm)
            self.all_items[name] = itm

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

    def on_use_pipeline(self, pipeline_name = None):
        """ Makes the currently selected pipeline as the active"""
        if pipeline_name is None or not isinstance(pipeline_name, str):
            if self.current_item is not None:
                self.current_item.setForeground(QColor(69,69,69))

            if self.listWidget_Pipelines.currentItem() is None:
                return
            pipeline_name = self.listWidget_Pipelines.currentItem().text()
        else:
            try:
                itm = self.all_items[pipeline_name]
                self.listWidget_Pipelines.setCurrentItem(itm)
            except Exception as e:
                raise e
                pass

        self.current_item = self.listWidget_Pipelines.currentItem()
        pipeline = self.pipeline_library[pipeline_name]
        log_info("Activated Pipeline", pipeline)

        if self.current_item is not None:
            self.current_item.setForeground(QColor(69, 200, 69))

        if self.project is not None and pipeline_name in ALL_REGISTERED_PIPELINES:
            pipeline = self.project.add_pipeline_script(pipeline)

        if self.comboBoxExperiment.currentText() != "Select Experiment (Optional)":
           pipeline.experiment = self.all_experiments[self.comboBoxExperiment.currentText()]
        self.on_reload_scripts()
        self.onPipelineActivated.emit(pipeline)

    def on_pipeline_finalize(self):
        self.onPipelineFinalize.emit()

    def remove_script(self):
        if self.project is None:
            return

        for t in self.listWidget_Pipelines.selectedItems():
            if t.text() in self.pipeline_library:
                itm = self.pipeline_library[t.text()]
                self.project.remove_pipeline_script(itm)
                try:
                    os.remove(itm.path)
                except OSError as e:
                    print(e)
        self.on_reload_scripts()

    def edit_script(self):
        try:
            t = self.pipeline_library[self.listWidget_Pipelines.selectedItems()[0].text()]

            self.editor.load(t.path)
        except Exception as e:
            print(e)

    def check_missing(self):
        if self.main_window.vian_event_handler.current_pipeline is None:
            return
        missing_info = self.project.get_missing_analyses(self.main_window.vian_event_handler.current_pipeline.requirements)
        for k in missing_info.keys():
            print(k, missing_info[k][1], missing_info[k][2])
        if missing_info['segment_analyses'][1] > 0:
            self.progressBarSegments.setValue(missing_info['segment_analyses'][2] / missing_info['segment_analyses'][1] * 100)
        else:
            self.progressBarSegments.setValue(100)
        if missing_info['screenshot_analyses'][1] > 0:
            self.progressBarScreenshots.setValue(
                missing_info['screenshot_analyses'][2] / missing_info['screenshot_analyses'][1] * 100)
        else:
            self.progressBarScreenshots.setValue(100)
        if missing_info['annotation_analyses'][1] > 0:
            self.progressBarAnnotations.setValue(
                missing_info['annotation_analyses'][2] / missing_info['annotation_analyses'][1] * 100)
        else:
            self.progressBarAnnotations.setValue(100)

    def on_pipeline_selected(self):
        if len(self.listWidget_Pipelines.selectedItems()) == 0:
            self.comboBoxExperiment.setEnabled(False)
            return
        else:
            self.comboBoxExperiment.setEnabled(True)
        name = self.listWidget_Pipelines.currentItem().text()
        if self.pipeline_library[name].experiment is None:
            self.comboBoxExperiment.setCurrentText("Select Experiment (Optional)")
        else:
            self.comboBoxExperiment.setCurrentText(self.pipeline_library[name].experiment.name)

    def on_experiments_changed(self):
        if self.project is None:
            return
        self.comboBoxExperiment.clear()
        self.all_experiments = dict()

        self.comboBoxExperiment.addItem("Select Experiment (Optional)")
        for e in self.project.experiments:
            self.comboBoxExperiment.addItem(e.name)
            self.all_experiments[e.name] = e

    def on_experiment_selected(self):
        if len(self.listWidget_Pipelines.selectedItems()) > 0 and \
                self.comboBoxExperiment.currentText() != "Select Experiment (Optional)":
            self.pipeline_library[self.listWidget_Pipelines.selectedItems()[0].text()].experiment \
                = self.all_experiments[self.comboBoxExperiment.currentText()]

    @pyqtSlot()
    def run_all(self):
        return
        # if self.project is not None:
        #     missing_info = self.project.get_missing_analyses(self.main_window.vian_event_handler.current_pipeline.requirements)
        #     missing = dict()
        #     log_info("## Missing Analyses in Pipeline ##")
        #     for k in missing_info.keys():
        #         missing.update(missing_info[k][0])
        #         log_info("## -- ", k, missing_info[k][2], missing_info[k][1], missing_info[k][0])
        #
        #     experiment = self.project.get_experiment_by_name(self.main_window.vian_event_handler.current_pipeline.experiment)
        #
        #     if experiment is None:
        #         log_error("Experiment not found for RunAll")
        #         return
        #
        #     for priority in sorted(missing.keys()):
        #         for analysis_name in missing[priority].keys():
        #             analysis = self.main_window.eval_class(analysis_name)
        #             for clobj_name, containers in missing[priority][analysis_name].items():
        #                 clobj = experiment.get_classification_object_by_name(clobj_name)
        #
        #                 if clobj is None:
        #                     log_warning("Classification Object not found")
        #                     continue
        #                 d = dict(
        #                     analysis=analysis(),
        #                     targets=containers,
        #                     parameters=None,
        #                     classification_objs=clobj
        #                 )
        #                 log_info("Pipeline Analysis: ", priority, analysis_name, clobj_name)
        #                 self.onRunAnalysis.emit(d)

    @pyqtSlot(object)
    def on_loaded(self, project:VIANProject):
        self.setEnabled(True)
        self.project = project
        project.onExperimentAdded.connect(self.on_experiments_changed)
        project.onExperimentRemoved.connect(self.on_experiments_changed)
        self.on_experiments_changed()
        self.on_reload_scripts()
        return

        # self.project = project
        #
        # for p in project.pipeline_scripts:
        #     log_info("Pipeline in Project:", p)
        #     try:
        #         import_module_from_path(p)
        #     except Exception as e:
        #         log_error("Exception during loading of Script:", e)
        # self.on_reload_scripts()
        # module_name = get_name_of_script_by_path(project.active_pipeline_script)
        # if module_name is not None and module_name in self.all_items:
        #     self.listWidget_Pipelines.setCurrentItem(self.all_items[module_name])
        #
        # self.btn_onSegment.setChecked(project.compute_pipeline_settings['segments'])
        # self.btn_onScreenshot.setChecked(project.compute_pipeline_settings['screenshots'])
        # self.btn_onAnnotation.setChecked(project.compute_pipeline_settings['annotations'])
        #
        # if module_name is not None:
        #     self.on_use_pipeline(pipeline_name=module_name)
        #
        # self.on_update_to_compute()
        # project.onAnalysisRemoved.connect(partial(self.check_missing))
        # project.onAnalysisAdded.connect(partial(self.check_missing))

    def on_closed(self):
        self.setEnabled(False)
        self.project = None
        self.on_reload_scripts()
        self.on_experiments_changed()

    def set_is_loading(self, state):
        if state:
            self.stackedWidget.setCurrentIndex(2)
            self.pushButtonCheckMissing.setEnabled(False)
            self.pushButtonRunAll.setEnabled(False)
            self.setEnabled(False)
        else:
            self.stackedWidget.setCurrentIndex(1)
            self.pushButtonCheckMissing.setEnabled(True)
            self.pushButtonRunAll.setEnabled(True)
            self.setEnabled(True)


class PipelineListWidget(QListWidget):
    def __init__(self, parent, pipeline_widget):
        super(PipelineListWidget, self).__init__(parent)
        self.pipeline_widget = pipeline_widget

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        super(PipelineListWidget, self).mouseDoubleClickEvent(e)
        self.pipeline_widget.edit_script()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        super(PipelineListWidget, self).mousePressEvent(e)
        self.pipeline_widget.on_pipeline_selected()
        if e.button() == Qt.RightButton:
            menu = QMenu(self)
            a_edit = menu.addAction("Edit Script")
            a_edit.triggered.connect(self.pipeline_widget.edit_script)
            a_delete = menu.addAction("Delete Script")
            a_delete.triggered.connect(self.pipeline_widget.remove_script)
            menu.popup(self.mapToGlobal(e.pos()))



