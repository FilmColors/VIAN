from functools import partial

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon

from core.container.project import Segmentation, ScreenshotGroup, ClassificationObject, VIANProject
from core.container.experiment import Vocabulary, VocabularyWord
from core.gui.ewidgetbase import EDialogWidget
from core.data.interfaces import IProjectChangeNotify
from core.gui.misc.utils import dialog_with_margin
from core.gui.vocabulary import VocabularyTreeView
from core.container.vocabulary_library import VocabularyLibrary, VocabularyCollection


class VocabularySelectorDialog(EDialogWidget):
    def __init__(self, main_window, target: Segmentation, vocabulary_library: VocabularyLibrary):
        super(VocabularySelectorDialog, self).__init__(main_window, main_window)
        self.setWindowTitle("Vocabulary")
        # self.setWindowFlag(Qt.FramelessWindowHint)

        self.setLayout(QHBoxLayout())
        self.inner = VocabularySelectorWidget(self, target, vocabulary_library)
        self.layout().addWidget(self.inner)
        self.show()
        dialog_with_margin(self.main_window, self)


class VocabularySelectorWidget(QWidget):
    def __init__(self, parent, target:Segmentation , vocabulary_library: VocabularyLibrary):
        super(VocabularySelectorWidget, self).__init__(parent)
        self.target = target                            # type: Segmentation | ScreenshotGroup
        self.project = target.project                   # type: VIANProject
        self.selected_clobj = None                      # type: None | ClassificationObject
        self.vocabulary_library = vocabulary_library    # type: VocabularyLibrary
        self.tree = VocabularyTreeView(self, self.vocabulary_library, mode=VocabularyTreeView.MODE_SELECTING)

        self.clobj_list = ClassificationObjectList(self, target, target.project)
        self.clobj_list.onClassificationObjectSelected.connect(self.set_classification_object)
        self.tree.onCheckStateChanged.connect(self.apply_changes)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.clobj_list)
        self.layout().addWidget(self.tree)

    @pyqtSlot(object)
    def set_classification_object(self, obj:ClassificationObject):
        self.selected_clobj = obj
        vocabularies = obj.get_vocabularies()
        self.tree.set_check_status(vocabularies)

    def apply_changes(self, voc_selection):
        if self.selected_clobj is not None:
            obj_vocabulary = [v.unique_id for v in self.selected_clobj.get_vocabularies()]

            for v in voc_selection:
                voc = v['vocabulary']
                state = v['state']
                if voc.unique_id not in obj_vocabulary and state == True:
                    self.project.add_vocabulary(voc)
                    self.selected_clobj.add_vocabulary(voc)
                elif voc.unique_id in obj_vocabulary and state == False:
                    self.selected_clobj.remove_vocabulary(voc)


class ClassificationObjectList(QWidget):
    onClassificationObjectSelected = pyqtSignal(object)

    def __init__(self, parent, target:Segmentation, project: VIANProject):
        super(ClassificationObjectList, self).__init__(parent)
        self.list = QListWidget()
        self.target = target        # type: Segmentation | ScreenshotGroup
        self.project = project      # type: VIANProject

        self.setLayout(QVBoxLayout())

        self.add_bar = QHBoxLayout()
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("Type here to add a new classification object")
        self.completer = QCompleter([c.name for c in self.project.get_all_classification_objects()])
        self.input_line.setCompleter(self.completer)

        self.btn_add = QPushButton("Add", self)
        self.btn_add.clicked.connect(self.add_classification_object)
        self.add_bar.addWidget(self.input_line)
        self.add_bar.addWidget(self.btn_add)

        self.layout().addItem(self.add_bar)
        self.layout().addWidget(self.list)

        self.list.itemSelectionChanged.connect(self.on_selected)
        self.update_list()

    def update_list(self):
        self.list.clear()
        for clobj in self.project.get_classification_objects_for_target(self.target):
            self.list.addItem(ClassificationObjectItem(self.list, clobj))

    def on_selected(self):
        if len(self.list.selectedItems()) > 0:
            selected = self.list.selectedItems()[0]
            self.onClassificationObjectSelected.emit(selected.clobj)

    def add_classification_object(self):

        # TODO MULTI EXPERIMENT
        clobj = self.project.get_classification_object_global(self.input_line.text())
        clobj.target_container.append(self.target)
        self.update_list()


class ClassificationObjectItem(QListWidgetItem):
    def __init__(self, parent, clobj:ClassificationObject):
        super(ClassificationObjectItem, self).__init__(parent)
        self.clobj = clobj
        self.setText(clobj.name)


