from PyQt5.QtWidgets import *
from PyQt5 import uic

from core.gui.ewidgetbase import EDockWidget
from core.data.interfaces import IProjectChangeNotify
from core.data.containers import *
from core.data.enums import MovieSource

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

        self.cB_ClassSegment.stateChanged.connect(self.source_changed)
        self.cB_ClassSegmentation.stateChanged.connect(self.source_changed)
        self.cB_ClassAnnotation.stateChanged.connect(self.source_changed)
        self.cB_ClassAnnotationLayer.stateChanged.connect(self.source_changed)

        self.lineEdit_ExperimentName.textChanged.connect(self.name_changed)
        self.lineEdit_ObjectName.returnPressed.connect(self.add_class_object)

        # self.treeWidget_Objects = QTreeWidget()
        self.treeWidget_Objects.itemSelectionChanged.connect(self.on_class_selection_changed)
        self.listView_Vocabularies.itemChanged.connect(self.update_vocabulary_list_in_object)
        self.listWidget_Analyses.itemChanged.connect(self.update_analysis_list_in_experiment)
        self.btn_AddObject.clicked.connect(self.add_class_object)
        self.btn_RemoveObject.clicked.connect(self.remove_class_object)

    def update_ui(self):
        if self.current_experiment is None or self.main_window.project is None:
            self.set_enabled(False)
        else:
            self.set_enabled(True)

            self.cB_ClassSegment.setChecked(SEGMENT in self.current_experiment.classification_sources)
            self.cB_ClassSegmentation.setChecked(SEGMENTATION in self.current_experiment.classification_sources)
            self.cB_ClassAnnotation.setChecked(ANNOTATION in self.current_experiment.classification_sources)
            self.cB_ClassAnnotationLayer.setChecked(ANNOTATION_LAYER in self.current_experiment.classification_sources)

            self.lineEdit_ExperimentName.setText(self.current_experiment.name)
            self.update_classification_object_tree()
            self.update_vocabulary_view()
            self.update_analysis_list()

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

    def on_class_selection_changed(self):
        self.inhibit_ui_signals = True
        if len(self.treeWidget_Objects.selectedItems()) > 0:
            self.selected_class_object = self.treeWidget_Objects.selectedItems()[0]
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
        if self.cB_ClassSegmentation.isChecked():
            sources.append(SEGMENTATION)
        if self.cB_ClassAnnotationLayer.isChecked():
            sources.append(ANNOTATION_LAYER)

        self.current_experiment.classification_sources = sources

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
                self.current_experiment = selected[0]
            self.update_ui()
        else:
            self.set_enabled(False)
        self.inhibit_ui_signals = False

    def on_loaded(self, project):
        self.update_ui()

    def on_closed(self):
        self.update_ui()

class ClassificationObjectItem(QTreeWidgetItem):
    def __init__(self, parent, obj):
        super(ClassificationObjectItem, self).__init__(parent)
        self.setText(0, obj.name)
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