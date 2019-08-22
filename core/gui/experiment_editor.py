import os
from functools import partial

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from core.gui.ewidgetbase import EDockWidget

from core.data.interfaces import IProjectChangeNotify
from core.container.project import SEGMENT, SCREENSHOT, ClassificationObject, \
    ANNOTATION, ANNOTATION_LAYER, SCREENSHOT_GROUP, Experiment, IProjectContainer, EXPERIMENT, CLASSIFICATION_OBJECT
from core.analysis.deep_learning.labels import VIAN_SEGMENTATION_DATASETS




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
    def __init__(self, main_window):
        super(ExperimentEditorDock, self).__init__(main_window, limit_size=False)
        self.experiment_editor = ExperimentEditor(main_window)
        self.setWidget(self.experiment_editor)
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
        self.target_items = []
        self.inhibit_ui_signals = False

        self.curr_parameter_widget = None

        for ds in VIAN_SEGMENTATION_DATASETS:
            self.comboBox_Dataset.addItem(ds[0])

        # This contains all current option of the ComboBox Target Container
        self.target_container_options = []
        self.classification_object_index = dict()

        self.lineEdit_ExperimentName.textChanged.connect(self.experiment_name_changed)
        self.lineEdit_ObjectName.returnPressed.connect(self.add_class_object)

        # self.treeWidget_Objects = QTreeWidget()
        self.treeWidget_Objects.itemSelectionChanged.connect(self.on_class_selection_changed)
        self.listView_Vocabularies.itemChanged.connect(self.update_vocabulary_list_in_object)
        self.listTargets.itemChanged.connect(self.update_target_list_in_object)
        self.btn_AddObject.clicked.connect(self.add_class_object)
        self.btn_RemoveObject.clicked.connect(self.remove_class_object)

        self.comboBox_Dataset.currentTextChanged.connect(self.on_dataset_changed)
        self.pushButton_SelectAllLabel.clicked.connect(partial(self.select_all_labels, True))
        self.pushButton_DeselectAllLabel.clicked.connect(partial(self.select_all_labels, False))
        self.listWidget_Labels.itemChanged.connect(self.update_dataset_in_object)
        self.current_dataset_label_checkboxes = []

        # Analysis
        self.selected_analysis = None
        self.comboBox_AnalysisClassificationObject.currentTextChanged.connect(self.on_analysis_classification_object_changed)
        self.comboBox_AnalysisClass.currentTextChanged.connect(self.on_analysis_combobox_changed)
        self.btn_AddAnalysis.clicked.connect(self.on_add_analysis)
        self.btn_RemoveAnalysis.clicked.connect(self.on_remove_analysis)
        self.btn_ApplyAnalysisChanges.clicked.connect(self.on_apply_analysis_changes)
        # self.listWidget_Analyses.itemChanged.connect(self.update_analysis_list_in_experiment)
        self.listWidget_Analyses.itemSelectionChanged.connect(self.on_selected_analysis_changed)
        self.lineEdit_AnalysisName.textChanged.connect(self.on_analysis_name_changed)

        self.analysis_index = dict()
        self.analyses_entries = []
        for a in self.main_window.analysis_list:
            self.comboBox_AnalysisClass.addItem(a.__name__)
            self.analysis_index[a.__name__] = a

        # Disable all controls that need a selected Classification Object:
        self.on_class_selection_changed()

    def update_ui(self):
        if self.current_experiment is None or self.main_window.project is None:
            self.set_enabled(False)
        else:
            self.set_enabled(True)

            self.lineEdit_ExperimentName.setText(self.current_experiment.name)
            self.update_classification_object_tree()
            self.update_vocabulary_view()
            self.update_analysis_list()
            self.update_target_container_combobox()

    def experiment_name_changed(self):
        if self.inhibit_ui_signals:
            return
        self.current_experiment.set_name(self.lineEdit_ExperimentName.text())

    #region Classification_objects
    def update_vocabulary_view(self):
        self.listView_Vocabularies.clear()
        self.voc_items = []
        if self.selected_class_object is not None:
            for voc in self.main_window.project.vocabularies:
                itm = VocabularyListItem(self.listView_Vocabularies, voc)
                self.listView_Vocabularies.addItem(itm)
                if voc in self.selected_class_object.obj.get_vocabularies():
                    itm.setCheckState(Qt.Checked)
                self.voc_items.append(itm)

    def update_classification_object_tree(self):
        self.treeWidget_Objects.clear()
        self.comboBox_AnalysisClassificationObject.currentTextChanged.disconnect(
            self.on_analysis_classification_object_changed)
        self.comboBox_AnalysisClassificationObject.clear()
        self.comboBox_AnalysisClassificationObject.addItem("None")
        self.classification_object_index = dict()

        for root in self.current_experiment.classification_objects:
            plain = []
            root.get_children_plain(plain)

            item_index_list = []
            for i, obj in enumerate(plain):
                self.comboBox_AnalysisClassificationObject.addItem(obj.name)
                self.classification_object_index[obj.name] = obj
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
        self.comboBox_AnalysisClassificationObject.currentTextChanged.connect(
            self.on_analysis_classification_object_changed)

    def update_target_container_combobox(self):
        self.listTargets.clear()
        self.target_items.clear()
        if self.selected_class_object is None:
            return

        for c in self.main_window.project.segmentation:
            itm = TargetItem(self.listTargets, c, "All Segments of " + c.get_name())
            if c in self.selected_class_object.obj.target_container:
                itm.setCheckState(Qt.Checked)
            self.listTargets.addItem(itm)
            self.target_items.append(itm)

        for c in self.main_window.project.annotation_layers:
            itm = TargetItem(self.listTargets, c, "All Annotations of " + c.get_name())
            if c in self.selected_class_object.obj.target_container:
                itm.setCheckState(Qt.Checked)
            self.listTargets.addItem(itm)
            self.target_items.append(itm)

        for c in self.main_window.project.screenshot_groups:
            itm = TargetItem(self.listTargets, c, "All Screenshots of " + c.get_name())
            if c in self.selected_class_object.obj.target_container:
                itm.setCheckState(Qt.Checked)
            self.listTargets.addItem(itm)
            self.target_items.append(itm)

    def on_new_created_object(self, returnvalue):
        self.cache_obj.set_target_container(returnvalue, self.cache_param)

    def on_class_selection_changed(self):
        self.inhibit_ui_signals = True
        if len(self.treeWidget_Objects.selectedItems()) > 0:
            self.listTargets.setEnabled(True)
            self.listView_Vocabularies.setEnabled(True)
            self.lineEdit_ObjectNameDetails.setEnabled(True)
            self.listWidget_Labels.setEnabled(True)
            self.pushButton_SelectAllLabel.setEnabled(True)
            self.pushButton_DeselectAllLabel.setEnabled(True)

            self.selected_class_object = self.treeWidget_Objects.selectedItems()[0]
            self.lineEdit_ObjectNameDetails.setText(self.selected_class_object.obj.name)
            self.update_vocabulary_view()
            self.update_target_container_combobox()
            self.update_semantic_ui()
        else:
            self.selected_class_object = None
            self.listTargets.setEnabled(False)
            self.listView_Vocabularies.setEnabled(False)
            self.lineEdit_ObjectNameDetails.setEnabled(False)
            self.listWidget_Labels.setEnabled(False)
            self.pushButton_SelectAllLabel.setEnabled(False)
            self.pushButton_DeselectAllLabel.setEnabled(False)

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
            if isinstance(self.selected_class_object.obj.parent, ClassificationObject):
                self.selected_class_object.obj.parent.remove_child(self.selected_class_object.obj)
            else:
                self.current_experiment.remove_classification_object(self.selected_class_object.obj)
        self.update_classification_object_tree()

    def update_vocabulary_list_in_object(self):
        if self.inhibit_ui_signals:
            return
        for itm in self.voc_items:
            if itm.checkState() == Qt.Checked:
                if itm.voc not in self.selected_class_object.obj.get_vocabularies():
                    self.selected_class_object.obj.add_vocabulary(itm.voc)
            else:
                if itm.voc in self.selected_class_object.obj.get_vocabularies():
                    self.selected_class_object.obj.remove_vocabulary(itm.voc)

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

    def update_target_list_in_object(self):
        if self.selected_class_object is not None:
            for itm in self.target_items:
                if itm.checkState() == Qt.Checked:
                    if itm.target_item not in self.selected_class_object.obj.target_container:
                        self.selected_class_object.obj.target_container.append(itm.target_item)
                else:
                    if itm.target_item in self.selected_class_object.obj.target_container:
                        self.selected_class_object.obj.target_container.remove(itm.target_item)

    #endregion

    #region Analysis Tab
    def on_add_analysis(self):
        if self.current_experiment is not None:
            self.current_experiment.add_analysis_to_pipeline("New Analysis_" +str(len(self.current_experiment.analyses)), self.main_window.analysis_list[0], None, None)
            self.update_analysis_list()

    def on_remove_analysis(self):
        if self.current_experiment is not None and self.selected_analysis is not None:
            self.current_experiment.remove_analysis_from_pipeline(self.selected_analysis)
            self.update_analysis_list()

    def on_apply_analysis_changes(self):
        if self.selected_analysis is not None and self.curr_parameter_widget is not None:
            self.selected_analysis['params'] = self.curr_parameter_widget.get_parameters()

    def on_analysis_classification_object_changed(self):
        if self.selected_analysis is not None:
            if self.comboBox_AnalysisClassificationObject.currentText == "None":
                self.selected_analysis['class_obj'] = "None"
            else:
                self.selected_analysis['class_obj'] = self.classification_object_index[self.comboBox_AnalysisClassificationObject.currentText()]

    def on_analysis_name_changed(self):
        if self.selected_analysis is not None:
            self.selected_analysis['name'] = self.lineEdit_AnalysisName.text()
            for s in self.analyses_entries:
                s.update_text()

    def on_selected_analysis_changed(self):
        self.lineEdit_AnalysisName.textChanged.disconnect(self.on_analysis_name_changed)
        if len(self.listWidget_Analyses.selectedItems()) > 0:
            itm = self.listWidget_Analyses.selectedItems()[0]
            self.selected_analysis = itm.analysis_entry
            a_class = itm.analysis_class

            # Add the new Parameter Widget
            if self.curr_parameter_widget is not None:
                self.curr_parameter_widget.deleteLater()
            self.curr_parameter_widget = a_class().get_parameter_widget()
            self.widgetParam.layout().addWidget(self.curr_parameter_widget)

            self.comboBox_AnalysisClass.setCurrentText(str(self.selected_analysis['class_name'].__name__))
            self.lineEdit_AnalysisName.setText(self.selected_analysis['name'])

            if self.selected_analysis['class_obj'] is not None:
                self.comboBox_AnalysisClassificationObject.setCurrentText(str(self.selected_analysis['class_obj'].name))
        else:
            self.selected_analysis = None

        self.lineEdit_AnalysisName.textChanged.connect(self.on_analysis_name_changed)

    def update_analysis_list(self):
        self.listWidget_Analyses.clear()
        self.analyses_entries = []
        if self.current_experiment is not None:
            for a in self.current_experiment.analyses:
                itm = AnalysisItem(self.listWidget_Analyses, a['class_name'], a)
                self.listWidget_Analyses.addItem(itm)
                self.analyses_entries.append(itm)

    def on_analysis_combobox_changed(self):
        if self.selected_analysis is not None:
            self.selected_analysis['class_name'] = self.analysis_index[self.comboBox_AnalysisClass.currentText()]

            if self.curr_parameter_widget is not None:
                self.curr_parameter_widget.deleteLater()
            self.curr_parameter_widget = self.selected_analysis['class_name']().get_parameter_widget()
            self.widgetParam.layout().addWidget(self.curr_parameter_widget)
    #endregion

    # region Semantic Segmentation
    def update_semantic_ui(self):
        self.listWidget_Labels.itemChanged.disconnect(self.update_dataset_in_object)
        self.comboBox_Dataset.currentTextChanged.disconnect(self.on_dataset_changed)
        self.current_dataset_label_checkboxes = []
        old_ds = self.selected_class_object.obj.semantic_segmentation_labels
        self.comboBox_Dataset.setCurrentText(old_ds[0])
        idx = self.comboBox_Dataset.currentIndex()
        if idx == 0:
            self.listWidget_Labels.setEnabled(False)
            self.selected_class_object.obj.set_dataset(None)
        else:
            self.listWidget_Labels.setEnabled(True)
            self.listWidget_Labels.clear()

            # Since the First IDX is "None" we need to subtract 1
            for lbl in VIAN_SEGMENTATION_DATASETS[idx - 1][1]:
                itm = LabelListItem(self.listWidget_Labels, lbl)
                self.listWidget_Labels.addItem(itm)
                self.current_dataset_label_checkboxes.append(itm)
                if old_ds[0] == VIAN_SEGMENTATION_DATASETS[idx - 1][0]:
                    if itm.label.value in self.selected_class_object.obj.semantic_segmentation_labels[1]:
                        itm.setCheckState(Qt.Checked)

        self.comboBox_Dataset.currentTextChanged.connect(self.on_dataset_changed)
        self.listWidget_Labels.itemChanged.connect(self.update_dataset_in_object)

    def select_all_labels(self, state):
        for s in self.current_dataset_label_checkboxes:
            if state:
                s.setCheckState(Qt.Checked)
            else:
                s.setCheckState(Qt.Unchecked)

    def on_dataset_changed(self):
        self.listWidget_Labels.itemChanged.disconnect(self.update_dataset_in_object)
        self.current_dataset_label_checkboxes = []
        if self.selected_class_object is None:
            return

        old_ds = self.selected_class_object.obj.semantic_segmentation_labels
        idx = self.comboBox_Dataset.currentIndex()
        if idx == 0:
            self.listWidget_Labels.setEnabled(False)
            self.selected_class_object.obj.set_dataset(None)
        else:
            self.listWidget_Labels.setEnabled(True)
            self.listWidget_Labels.clear()

            # Since the First IDX is "None" we need to subtract 1
            for lbl in VIAN_SEGMENTATION_DATASETS[idx - 1][1]:
                itm = LabelListItem(self.listWidget_Labels, lbl)
                self.listWidget_Labels.addItem(itm)
                self.current_dataset_label_checkboxes.append(itm)
                if old_ds[0] == VIAN_SEGMENTATION_DATASETS[idx - 1][0]:
                    if itm.label.value in self.selected_class_object.obj.semantic_segmentation_labels[1]:
                        itm.setCheckState(Qt.Checked)

        self.listWidget_Labels.itemChanged.connect(self.update_dataset_in_object)

    def update_dataset_in_object(self):
        if self.selected_class_object is not None:
            self.selected_class_object.obj.set_dataset(self.comboBox_Dataset.currentText())
            for cb in self.current_dataset_label_checkboxes:
                if cb.checkState() == Qt.Checked:
                    self.selected_class_object.obj.add_dataset_label(cb.label.value)

    # endregion

    def set_enabled(self, state):
        for c in self.children():
            if isinstance(c, QWidget):
                c.setEnabled(state)

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
        print("ON-Changed", project, item)

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


class LabelListItem(QListWidgetItem):
    def __init__(self, parent, label):
        super(LabelListItem, self).__init__(parent, Qt.ItemIsUserCheckable)
        self.label = label
        self.setText(label.name)
        self.setCheckState(Qt.Unchecked)


class AnalysisItem(QListWidgetItem):
    def __init__(self, parent, analysis_class, entry):
        super(AnalysisItem, self).__init__(parent)
        self.analysis_class = analysis_class
        self.analysis_entry = entry
        self.setText(self.analysis_entry['name'])
    def update_text(self):
        self.setText(self.analysis_entry['name'])


class TargetItem(QListWidgetItem):
    def __init__(self, parent, target_item, text):
        super(TargetItem, self).__init__(parent, Qt.ItemIsUserCheckable)
        self.target_item = target_item
        self.setText(text)
        self.setCheckState(Qt.Unchecked)