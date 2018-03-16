from PyQt5.QtWidgets import *
from PyQt5 import uic

from core.gui.ewidgetbase import EDockWidget, CreateSegmentationPopup, CreateAnnotationLayerPopup, CreateScreenshotGroupPopup
from core.data.interfaces import IProjectChangeNotify
from core.data.containers import *
from core.data.enums import MovieSource, TargetContainerType

TGT_ENTRIES = [ 'All',
                "All Segments",
                "All Annotations" ,
                "All Screenshots",
                "All Segments of ",
                "All Annotations of ",
                "All Screenshots of ",
                "All Segments of <Create Segmentation>",
                "All Annotations of <Create Annotation Layer",
                "All Screenshots of <Create Screenshots Group>"]

class ExperimentEditorDock(EDockWidget):
    def __init__(self, main_window, editor):
        super(ExperimentEditorDock, self).__init__(main_window, limit_size=False)
        self.setWidget(editor)
        self.setWindowTitle("Experiment Overview")


class ExperimentEditor(QWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(ExperimentEditor, self).__init__(main_window)
        path = os.path.abspath("qt_ui/ExperimentEditor.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.current_experiment = None
        self.current_experiment = Experiment()
        self.selected_class_object = None

        self.voc_items = []
        self.analysis_items = []
        self.inhibit_ui_signals = False

        self.cache_obj = None
        self.cache_param = None

        # This contains all current option of the ComboBox Target Container
        self.target_container_options = []

        self.cB_ClassSegment.stateChanged.connect(self.source_changed)
        self.cB_ClassAnnotation.stateChanged.connect(self.source_changed)
        self.cB_ClassScreenshots.stateChanged.connect(self.source_changed)

        # self.cB_ClassSegmentation.stateChanged.connect(self.source_changed)
        # self.cB_ClassAnnotationLayer.stateChanged.connect(self.source_changed)

        self.lineEdit_ExperimentName.textChanged.connect(self.name_changed)
        self.lineEdit_ObjectName.returnPressed.connect(self.add_class_object)

        # self.treeWidget_Objects = QTreeWidget()
        self.treeWidget_Objects.itemSelectionChanged.connect(self.on_class_selection_changed)
        self.listView_Vocabularies.itemChanged.connect(self.update_vocabulary_list_in_object)
        self.listWidget_Analyses.itemChanged.connect(self.update_analysis_list_in_experiment)
        self.btn_AddObject.clicked.connect(self.add_class_object)
        self.btn_RemoveObject.clicked.connect(self.remove_class_object)
        self.comboBox_TargetContainers.currentIndexChanged.connect(self.on_target_container_changed)

    def update_ui(self):
        if self.current_experiment is None or self.main_window.project is None:
            self.set_enabled(False)
        else:
            self.set_enabled(True)

            self.cB_ClassSegment.setChecked(SEGMENT in self.current_experiment.classification_sources)
            # self.cB_ClassSegmentation.setChecked(SEGMENTATION in self.current_experiment.classification_sources)
            self.cB_ClassAnnotation.setChecked(ANNOTATION in self.current_experiment.classification_sources)
            self.cB_ClassScreenshots.setChecked(SCREENSHOT in self.current_experiment.classification_sources)
            # self.cB_ClassAnnotationLayer.setChecked(ANNOTATION_LAYER in self.current_experiment.classification_sources)

            self.lineEdit_ExperimentName.setText(self.current_experiment.name)
            self.update_classification_object_tree()
            self.update_vocabulary_view()
            self.update_analysis_list()
            self.update_target_container_combobox()

    def update_vocabulary_view(self):
        self.listView_Vocabularies.clear()
        self.voc_items = []
        if self.selected_class_object is not None:
            # self.listView_Vocabularies = QListWidget()
            for voc in self.main_window.project.vocabularies:
                if voc.derived_vocabulary is False:
                    itm = VocabularyListItem(self.listView_Vocabularies, voc)
                    self.listView_Vocabularies.addItem(itm)
                    if voc in self.selected_class_object.obj.get_base_vocabularies():
                        itm.setCheckState(Qt.Checked)
                    self.voc_items.append(itm)

    def update_classification_object_tree(self):
        self.treeWidget_Objects.clear()
        for root in self.current_experiment.classification_objects:
            plain = []
            root.get_children_plain(plain)

            item_index_list = []
            for i, obj in enumerate(plain):
                if i == 0:
                    itm = ClassificationObjectItem(self.treeWidget_Objects, obj)
                    self.treeWidget_Objects.addTopLevelItem(itm)
                else:
                    # Find the Parent Item in the list
                    for temp in item_index_list:
                        if temp[0] == obj.parent:
                            rt = temp[1]
                            break
                    # Add it as Child of the Parent Item
                    if rt is not None:
                        itm = ClassificationObjectItem(rt, obj)

                item_index_list.append([obj, itm])
        self.treeWidget_Objects.expandAll()

    def update_target_container_combobox(self):
        self.comboBox_TargetContainers.currentIndexChanged.disconnect(self.on_target_container_changed)

        self.comboBox_TargetContainers.clear()
        self.target_container_options.clear()
        self.comboBox_TargetContainers.addItem(TGT_ENTRIES[0])
        self.target_container_options.append(("All", None))

        if SEGMENT in self.current_experiment.classification_sources:
            self.comboBox_TargetContainers.addItem(TGT_ENTRIES[1])
            self.target_container_options.append((TGT_ENTRIES[1], None))

            for segm in self.current_experiment.project.segmentation:
                self.comboBox_TargetContainers.addItem(TGT_ENTRIES[4] + segm.get_name())
                self.target_container_options.append((TGT_ENTRIES[4] + segm.get_name(), segm))

            self.comboBox_TargetContainers.addItem(TGT_ENTRIES[7])
            self.target_container_options.append((TGT_ENTRIES[7], None))

        if ANNOTATION in self.current_experiment.classification_sources:
            self.comboBox_TargetContainers.addItem(TGT_ENTRIES[2])
            self.target_container_options.append((TGT_ENTRIES[1], None))

            for ann in self.current_experiment.project.annotation_layers:
                self.comboBox_TargetContainers.addItem(TGT_ENTRIES[5] + ann.get_name())
                self.target_container_options.append((TGT_ENTRIES[5] + ann.get_name(), ann))

            self.comboBox_TargetContainers.addItem(TGT_ENTRIES[8])
            self.target_container_options.append((TGT_ENTRIES[8], None))

        if SCREENSHOT in self.current_experiment.classification_sources:
            self.comboBox_TargetContainers.addItem(TGT_ENTRIES[3])
            self.target_container_options.append((TGT_ENTRIES[3], None))

            for grp in self.current_experiment.project.screenshot_groups:
                self.comboBox_TargetContainers.addItem(TGT_ENTRIES[6] + grp.get_name())
                self.target_container_options.append((TGT_ENTRIES[6] + grp.get_name(), grp))

            self.comboBox_TargetContainers.addItem(TGT_ENTRIES[9])
            self.target_container_options.append((TGT_ENTRIES[9], None))

        self.comboBox_TargetContainers.currentIndexChanged.connect(self.on_target_container_changed)

    def on_target_container_changed(self):
        if self.selected_class_object is not None:
            idx = self.comboBox_TargetContainers.currentIndex()
            curr_tpl = self.target_container_options[idx]
            obj = self.selected_class_object.obj

            if curr_tpl[0] == "All Segments of <Create Segmentation>":
                popup = CreateSegmentationPopup(self.main_window, self.main_window.project,
                                                self.selected_class_object.obj.name, self.on_new_created_object)
                self.cache_obj = obj
                self.cache_param = TargetContainerType.EXPLICIT_SEGMENTS
            elif curr_tpl[0] == "All Annotations of <Create Annotation Layer":
                popup = CreateAnnotationLayerPopup(self.main_window, self.main_window.project,
                                                   self.selected_class_object.obj.name, self.on_new_created_object)
                self.cache_obj = obj
                self.cache_param = TargetContainerType.EXPLICIT_ANNOTATIONS

            elif curr_tpl[0] == "All Screenshots of <Create Screenshots Group>":
                popup = CreateScreenshotGroupPopup(self.main_window, self.main_window.project,
                                                   self.selected_class_object.obj.name, self.on_new_created_object)
                self.cache_obj = obj
                self.cache_param = TargetContainerType.EXPLICIT_SCREENSHOTS

            elif "All Segments of" in curr_tpl[0] and curr_tpl[1] is not None:
                obj.set_target_container(curr_tpl[1], TargetContainerType.EXPLICIT_SEGMENTS)
            elif "All Annotations of" in curr_tpl[0] and curr_tpl[1] is not None:
                obj.set_target_container(curr_tpl[1], TargetContainerType.EXPLICIT_ANNOTATIONS)
            elif "All Screenshots of" in curr_tpl[0] and curr_tpl[1] is not None:
                obj.set_target_container(curr_tpl[1], TargetContainerType.EXPLICIT_SCREENSHOTS)

            elif "All Segments" in curr_tpl[0]:
                obj.set_target_container(None, TargetContainerType.ALL_SEGMENTS)
            elif "All Annotations" in curr_tpl[0]:
                obj.set_target_container(None, TargetContainerType.ALL_ANNOTATIONS)
            elif "All Screenshots" in curr_tpl[0]:
                obj.set_target_container(None, TargetContainerType.ALL_SCREENSHOTS)

            else:
                obj.set_target_container(None)

            self.update_classification_object_tree()

    def on_new_created_object(self, returnvalue):
        self.cache_obj.set_target_container(returnvalue, self.cache_param)

    def on_class_selection_changed(self):
        self.inhibit_ui_signals = True
        if len(self.treeWidget_Objects.selectedItems()) > 0:
            self.selected_class_object = self.treeWidget_Objects.selectedItems()[0]
            self.lineEdit_ObjectNameDetails.setText(self.selected_class_object.obj.name)
            self.update_vocabulary_view()
        else:
            self.selected_class_object = None
        self.inhibit_ui_signals = False

    def add_class_object(self):
        name = self.lineEdit_ObjectName.text()
        if name == "":
            return

        if self.selected_class_object is not None:
            self.current_experiment.create_class_object(name, self.selected_class_object.obj)
        else:
            self.current_experiment.create_class_object(name, self.current_experiment)

        self.lineEdit_ObjectName.clear()
        self.update_classification_object_tree()

    def remove_class_object(self):
        if self.selected_class_object is not None:
            if isinstance(self.selected_class_object.obj.parent, ClassificationObjects):
                self.selected_class_object.obj.parent.remove_child(self.selected_class_object.obj)
            else:
                self.current_experiment.remove_class_object(self.selected_class_object.obj)
        self.update_classification_object_tree()

    def source_changed(self):
        if self.inhibit_ui_signals:
            return
        sources = []
        if self.cB_ClassSegment.isChecked():
            sources.append(SEGMENT)
        if self.cB_ClassAnnotation.isChecked():
            sources.append(ANNOTATION)
        if self.cB_ClassScreenshots.isChecked():
            sources.append(SCREENSHOT)
        # if self.cB_ClassSegmentation.isChecked():
        #     sources.append(SEGMENTATION)
        # if self.cB_ClassAnnotationLayer.isChecked():
        #     sources.append(ANNOTATION_LAYER)

        self.current_experiment.classification_sources = sources
        self.update_target_container_combobox()

    def name_changed(self):
        if self.inhibit_ui_signals:
            return
        self.current_experiment.set_name(self.lineEdit_ExperimentName.text())

    def set_enabled(self, state):
        for c in self.children():
            if isinstance(c, QWidget):
                c.setEnabled(state)

    def update_vocabulary_list_in_object(self):
        if self.inhibit_ui_signals:
            return
        for itm in self.voc_items:
            if itm.checkState() == Qt.Checked:
                if itm.voc not in self.selected_class_object.obj.get_base_vocabularies():
                    self.selected_class_object.obj.add_vocabulary(itm.voc)
            else:
                for v in self.selected_class_object.obj.classification_vocabularies:
                    if v.base_vocabulary == itm.voc:
                        self.selected_class_object.obj.remove_vocabulary(v)

    def update_analysis_list(self):
        self.listWidget_Analyses.clear()
        self.analysis_items = []
        for analysis in self.main_window.analysis_list:
            itm = AnalysisItem(self.listWidget_Analyses, analysis)
            self.listWidget_Analyses.addItem(itm)
            self.analysis_items.append(itm)
            if self.current_experiment is not None:
                if analysis.__name__ in self.current_experiment.analyses_templates:
                    itm.setCheckState(Qt.Checked)
                if self.main_window.project.has_analysis(analysis.__name__):
                    itm.setForeground(QColor(0, 204, 0))
                else:
                    itm.setForeground(QColor(204, 0, 0))

    def update_analysis_list_in_experiment(self):
        for itm in self.analysis_items:
            if itm.checkState() == Qt.Checked:
                if itm.analysis_class.__name__ not in self.current_experiment.analyses_templates:
                    self.current_experiment.analyses_templates.append(itm.analysis_class.__name__)
            else:
                if itm.analysis_class.__name__ in self.current_experiment.analyses_templates:
                    self.current_experiment.analyses_templates.remove(itm.analysis_class.__name__)

    def on_selected(self, sender, selected):
        self.inhibit_ui_signals = True
        if len(selected) > 0:
            if selected[0].get_type() == EXPERIMENT:
                self.set_enabled(True)
                self.current_experiment = selected[0]
            else:
                self.set_enabled(False)
            self.update_ui()
        else:
            self.set_enabled(False)
        self.inhibit_ui_signals = False

    def on_loaded(self, project):
        if len(project.experiments) > 0:
            self.current_experiment = project.experiments[0]
        else:
            self.current_experiment = None

        self.update_ui()

    def on_closed(self):
        self.update_ui()

    def on_changed(self, project, item):
        if item is None:
            return

        if isinstance(item, IProjectContainer) and item.get_type() == EXPERIMENT or item.get_type() == CLASSIFICATION_OBJECT:
            self.update_ui()


class ClassificationObjectItem(QTreeWidgetItem):
    def __init__(self, parent, obj):
        super(ClassificationObjectItem, self).__init__(parent)
        if len(obj.target_container) > 0:
            self.setText(0, obj.name + " " + str([t.get_name() for t in obj.target_container]))
        else:
            self.setText(0, obj.name + " [All]")
        self.obj = obj


class VocabularyListItem(QListWidgetItem):
    def __init__(self, parent, voc):
        super(VocabularyListItem, self).__init__(parent, Qt.ItemIsUserCheckable)
        self.voc = voc
        self.setText(voc.name)
        self.setCheckState(Qt.Unchecked)


class AnalysisItem(QListWidgetItem):
    def __init__(self, parent, analysis_class):
        super(AnalysisItem, self).__init__(parent, Qt.ItemIsUserCheckable)
        self.analysis_class = analysis_class
        self.setText(self.analysis_class().name)
        self.setCheckState(Qt.Unchecked)