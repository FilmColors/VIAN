from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt5 import uic
from core.gui.ewidgetbase import EDockWidget, EDialogWidget
from core.data.interfaces import IProjectChangeNotify, IHasVocabulary
import os
from functools import partial
from core.data.enums import *

class VocabularyManager(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(VocabularyManager, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Vocabulary Manager")
        self.vocabulary_view = VocabularyView(self, self.main_window)
        self.setWidget(self.vocabulary_view)

        self.show()

    def on_changed(self, project, item):
        self.vocabulary_view.on_changed(project, item)

    def on_selected(self, sender, selected):
        self.vocabulary_view.on_selected( sender, selected)

    def on_loaded(self, project):
        self.vocabulary_view.on_loaded(project)


class VocabularyView(QWidget, IProjectChangeNotify):
    def __init__(self, parent, main_window):
        super(VocabularyView, self).__init__(parent)
        path = os.path.abspath("qt_ui/VocabularyManager.ui")
        uic.loadUi(path, self)
        self.main_window = main_window
        self.project = main_window.project


        self.treeView = VocabularyTreeView(self)
        self.inner.layout().addWidget(self.treeView)

        self.vocabulary_model = QStandardItemModel(self.treeView)

        self.btn_addItem.clicked.connect(self.add_word)
        self.lineEdit_Item.returnPressed.connect(self.add_word)
        self.show()

    def add_vocabulary(self, voc):
        self.vocabulary_model.appendRow(voc.get_vocabulary_item_model())
        self.treeView.setModel(self.vocabulary_model)
        # self.treeView = QTreeView()

    def add_word(self):
        name = self.lineEdit_Item.text()
        if name != "" and len(self.treeView.selectedIndexes()) > 0:
            selected = self.vocabulary_model.itemFromIndex(self.treeView.selectedIndexes()[0])
            selected_item = selected.voc_object

            if selected_item.get_type() == VOCABULARY_WORD:
                word = selected_item.vocabulary.create_word(name, selected_item.name)
                item = VocabularyItem(word.name, word)
            elif selected_item.get_type() == VOCABULARY:
                word = selected_item.create_word(name)
                item = VocabularyItem(word.name, word)

            else:
                print("FAILED TO CREAE WORD")
            # if isinstance(selected_item, Vocabulary):
            #     selected_item.add_word(VocabularyWord(name))
            # elif isinstance(selected_item, VocabularyWord):
            #     selected_item.add_children(VocabularyWord(name))

            self.add_to_tree(selected, item)
        self.lineEdit_Item.setText("")

    def recreate_tree(self):
        self.vocabulary_model.clear()
        for v in self.project.vocabularies:
            self.add_vocabulary(v)

    def add_to_tree(self, selected, item):
        selected.appendRow(item)

    def on_loaded(self, project):
        self.project = project
        self.recreate_tree()

    def on_changed(self, project, item):
        if item is None:
            self.recreate_tree()

    def on_selected(self, sender, selected):
        pass


class VocabularyTreeView(QTreeView):
    def __init__(self, parent):
        super(VocabularyTreeView, self).__init__(parent)
        self.is_editing = False


    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() == Qt.RightButton:
            self.open_context_menu(QMouseEvent)
        else:
            super(VocabularyTreeView, self).mousePressEvent(QMouseEvent)

    def open_context_menu(self, QMouseEvent):
        pos = self.mapToGlobal(QMouseEvent.pos())
        try:
            obj = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        except:
            obj = None
        cm = VocabularyContextMenu(self.parent().parent().main_window, pos, obj)

    def apply_name_changed(self):
        current_word = self.model().itemFromIndex(self.selectedIndexes()[0]).voc_object
        new_name = self.model().itemFromIndex(self.selectedIndexes()[0]).text()
        current_word.name = new_name

    def edit(self, *args, **kwargs):
        self.is_editing = True
        return super(VocabularyTreeView, self).edit(*args, **kwargs)

    def closeEditor(self, *args, **kwargs):
        super(VocabularyTreeView, self).closeEditor(*args, **kwargs)
        self.is_editing = False
        self.apply_name_changed()

    def editorDestroyed(self, *args, **kwargs):
        self.is_editing = False
        self.apply_name_changed()
        super(VocabularyTreeView, self).editorDestroyed(*args, **kwargs)


class VocabularyContextMenu(QMenu):
    def __init__(self, parent, pos, item):
        super(VocabularyContextMenu, self).__init__(parent)
        self.item = item
        self.main_window = parent

        if item is not None:
            self.a_remove = self.addAction("Remove Word")
            self.a_remove.triggered.connect(self.on_remove)
            self.a_add_word = self.addAction("Add Word")
            if self.item.get_type() == VOCABULARY and self.main_window.project is not None:
                self.a_copy = self.addAction("Copy Vocabulary")
                self.a_copy.triggered.connect(partial(self.main_window.project.copy_vocabulary, self.item))

        self.a_new_voc = self.addAction("New Vocabulary")
        self.a_new_voc.triggered.connect(self.on_new_voc)




        self.popup(pos)

    def on_new_voc(self):
        self.main_window.project.create_vocabulary("New Vocabulary")

    def on_remove(self):
        if self.item.get_type() == VOCABULARY:
            self.main_window.project.remove_vocabulary(self.item)
        else:
            self.item.vocabulary.remove_word(self.item)


class VocabularyItem(QStandardItem):
    def __init__(self, text, object):
        super(VocabularyItem, self).__init__(text)
        self.voc_object = object


class VocabularyExportDialog(EDialogWidget):
    def __init__(self, main_window):
        super(VocabularyExportDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("qt_ui/DialogExportVocabulary.ui")
        uic.loadUi(path, self)
        self.project = main_window.project
        self.lineEdit_Path.setText(self.project.export_dir)

        self.entries = []
        for voc in self.project.vocabularies:

            item = QWidget(self.vocList)
            item.setLayout(QHBoxLayout(item))
            item.layout().addWidget(QLabel(voc.name, item))
            cb = QCheckBox(item)
            item.layout().addWidget(cb)
            self.entries.append([cb, voc])
            self.vocList.layout().addWidget(item)


        self.btn_Export.clicked.connect(self.export)
        self.btn_Cancel.clicked.connect(self.close)
        self.btn_Browse.clicked.connect(self.on_browse)

    def on_browse(self):
        path = QFileDialog.getExistingDirectory(directory=self.project.export_dir)
        self.lineEdit_Path.setText(path)

    def export(self):
        if not os.path.isdir(self.lineEdit_Path.text()):
            QMessageBox.warning(self, "No valid Directory", "Please select a valid Directory first")
        else:
            dir = self.lineEdit_Path.text()
            for itm in self.entries:
                if itm[0].isChecked():
                    itm[1].export_vocabulary(dir + "/" +itm[1].name + ".json")

            self.close()


class VocabularyMatrix(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(VocabularyMatrix, self).__init__(main_window,limit_size=False)

        self.main_window = main_window
        self.n_per_row = 20
        self.setWindowTitle("Vocabulary Matrix")
        self.all_boxes = []
        self.current_segment = 0

        self.tabs_list = []
        self.voc_categories = []

        # Header Segment Selection Buttons
        self.segment_selection = QWidget(self)
        self.segment_selection.setLayout(QHBoxLayout(self.segment_selection))
        self.btn_previous = QPushButton("Previous Segment", self.segment_selection)
        self.btn_previous.clicked.connect(self.on_button_previous)
        self.btn_previous.setMinimumHeight(30)
        self.lbl_current = QLabel(str(self.current_segment), self.segment_selection)
        self.btn_next = QPushButton("Next Segment", self.segment_selection)
        self.btn_next.clicked.connect(self.on_button_next)
        self.btn_next.setMinimumHeight(30)
        self.segment_selection.layout().addWidget(self.btn_previous)
        self.segment_selection.layout().addItem(QSpacerItem(10, 2, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.segment_selection.layout().addWidget(self.lbl_current)
        self.segment_selection.layout().addItem(QSpacerItem(10, 2, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.segment_selection.layout().addWidget(self.btn_next)

        self.central = QWidget(self)
        self.central.setLayout(QVBoxLayout(self.central))

        self.tabs = QTabWidget(self)

        self.central.layout().addWidget(self.segment_selection)
        self.central.layout().addWidget(self.tabs)
        # self.setLayout(QHBoxLayout(self))
        self.setWidget(self.central)
        self.recreate_widget()


    def on_changed(self, project, item):
        if item is not None:
            if item.get_type() == VOCABULARY or item.get_type() == VOCABULARY_WORD:
                self.recreate_widget()
            else:
                self.update_widget()

    def on_loaded(self, project):
        self.recreate_widget()

    def on_selected(self, sender, selected):
        self.update_widget()

    def update_widget(self):
        if len(self.project().selected) > 0 and isinstance(self.project().selected[0], IHasVocabulary):
            for itm in self.all_boxes:
                itm[0].setEnabled(True)
                itm[0].setChecked(self.project().selected[0].has_word(itm[1]))
        else:
            for itm in self.all_boxes:
                itm[0].setEnabled(False)

    def recreate_widget(self):
        self.tabs.clear()
        self.voc_categories = []
        self.tabs_list = []

        for voc in self.project().vocabularies:
            if voc.category not in self.voc_categories:
                self.voc_categories.append(voc.category)
                area = QScrollArea(self.tabs)
                area.setWidgetResizable(True)
                t = QWidget(None)
                # t.setMinimumSize(200,200)
                # t.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
                l = QVBoxLayout(t)
                t.setLayout(l)
                # l.setSizeConstraint(l.SetMinAndMaxSize)

                area.setWidget(t)
                self.tabs.addTab(area, voc.category)
                self.tabs_list.append(t)

        for voc in self.project().vocabularies:
            tab_idx = self.voc_categories.index(voc.category)
            tab = self.tabs_list[tab_idx]
            # l = QVBoxLayout(tab)
            # tab.setLayout(l)
            outer = QFrame(tab)
            # outer.setFrameStyle(QFrame.Panel)
            outer.setLayout(QVBoxLayout(outer))
            outer.setStyleSheet("QWidget{background: rgb(30,30,30)}")
            tab.layout().addWidget(outer)

            frame = QWidget(tab)
            # frame.setFrameStyle(QFrame.StyledPanel)


            # tab.layout().addWidget(frame)

            frame.setLayout(QHBoxLayout(frame))
            lbl = QLabel(voc.name)
            lbl.setStyleSheet("QLabel{color:#6391b5;}")
            # lbl.setFixedWidth(150)
            lbl.setWordWrap(True)
            outer.layout().addWidget(lbl)
            outer.layout().addWidget(frame)
            col_count = 0
            hbox = QVBoxLayout(frame)
            hbox.setSpacing(2)
            voc_list = voc.get_vocabulary_as_list()

            voc_list = sorted(voc_list, key=lambda x:x.name.lower())
            for w in voc_list:
                cb = QCheckBox(w.name, frame)
                cb.stateChanged.connect(self.on_cb_change)
                cb.setStyleSheet("QCheckBox:unchecked{ color: #b1b1b1; }QCheckBox:checked{ color: #3f7eaf; }")
                if len(self.project().selected) > 0 and self.project().selected[0].has_word(w):
                    cb.setChecked(True)
                hbox.addWidget(cb)
                col_count += 1
                self.all_boxes.append([cb, w])

                if col_count == self.n_per_row:
                    frame.layout().addItem(hbox)
                    hbox = QVBoxLayout(tab)
                    col_count = 0

            if col_count != 0:
                hbox.addItem(QSpacerItem(1, 1, QSizePolicy.Preferred, QSizePolicy.Expanding))
                frame.layout().addItem(hbox)

            # frame.layout().addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Fixed))
            # frame.layout().addItem(QSpacerItem(1, 1, QSizePolicy.Fixed, QSizePolicy.Expanding))
            # tab.layout().addItem(QSpacerItem(1, 1, QSizePolicy.Fixed, QSizePolicy.Expanding))

        for t in self.tabs_list:
            t.layout().addItem(QSpacerItem(2,2,QSizePolicy.Preferred, QSizePolicy.Expanding))
        # for voc in self.project().vocabularies:
        #     model = voc.get_vocabulary_item_model()
        #     # model = QStandardItemModel()
        #     tab_idx = self.voc_categories.index(voc.category)
        #     tab = self.tabs_list[tab_idx]
        #     l = QVBoxLayout(tab)
        #     tab.setLayout(l)
        #     for i in range(model.rowCount()):
        #         word_model = model.child(i, 0)
        #         word = word_model.voc_object
        #         l.addWidget(QLabel(word.name))
        #         frame = QFrame(tab)
        #         vbox = QVBoxLayout(frame)
        #         frame.setLayout(vbox)
        #         l.addWidget(frame)
        #
        #         col_count = 0
        #         hbox = QHBoxLayout(frame)
        #         for j in range(word_model.rowCount()):
        #             w = word_model.child(j , 0).voc_object
        #             cb = QCheckBox(w.name, frame)
        #             cb.stateChanged.connect(self.on_cb_change)
        #             hbox.addWidget(cb)
        #             col_count += 1
        #             if col_count == self.n_per_row:
        #                 vbox.addItem(hbox)
        #                 hbox = QHBoxLayout(frame)
        #                 col_count = 0

                # vbox.addItem(hbox)


            # tab.layout().addItem(QSpacerItem(1,1,QSizePolicy.Fixed, QSizePolicy.Expanding))

            # self.tabs.addTab(tab, voc.name)

    def on_cb_change(self):
        sender = self.sender()
        state = sender.isChecked()
        name = sender.text()
        word = self.project().get_word_object_from_name(name)

        for itm in self.project().selected:
            if isinstance(itm, IHasVocabulary):
                if state:
                    itm.add_word(word)
                else:
                    itm.remove_word(word)
                    sender.setStyleSheet("QCheckBox{color: #b1b1b1;}")

    def on_button_previous(self):
        segm = self.project().get_main_segmentation()
        if segm is None:
            return
        if self.current_segment > 0:
            self.current_segment -= 1
        self.frame_segment(segm)

    def frame_segment(self, segmentation):
        if self.current_segment - 1 < len(segmentation.segments):
            s = segmentation.segments[self.current_segment]
            self.main_window.timeline.timeline.frame_time_range(s.get_start() + 1000, s.get_end())
            self.lbl_current.setText(str(s.ID).zfill(3))
            self.main_window.player.set_media_time(s.get_start() + 1000)
            self.project().set_selected(self, [s])

    def on_button_next(self):
        segm = self.project().get_main_segmentation()
        if segm is None:
            return
        if self.current_segment + 1 < len(segm.segments):
            self.current_segment += 1
        self.frame_segment(segm)

    def resizeEvent(self, *args, **kwargs):
        super(VocabularyMatrix, self).resizeEvent(*args, **kwargs)
#endregion











""