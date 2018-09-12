from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from core.corpus.shared.entities import *
from core.gui.ewidgetbase import EMultiGraphicsView

class SegmentVisualization(QScrollArea):
    onSegmentSelected = pyqtSignal(object)

    def __init__(self, parent, visualizer = None):
        super(SegmentVisualization, self).__init__(parent)
        self.setWidgetResizable(True)
        self.setWidget(QWidget())
        self.widget().setLayout(QVBoxLayout())
        self.entries = dict()
        self.screenshot_segm_mapping = dict()
        #
        # if visualizer is not None:
        #     self.onSegmentSelected.connect(visualizer.on_segment_selected)

    def add_entry(self, db_project:DBProject, db_segment:DBSegment, db_screenshots = None, imgs = None):
        itm = SegmentVisualizationItem(db_project, db_segment, db_screenshots, imgs)
        itm.onSelected.connect(self.onSegmentSelected)
        for scr in db_screenshots:
            self.screenshot_segm_mapping[scr.screenshot_id] = db_segment.segment_id
        self.entries[db_segment.segment_id] = itm
        self.widget().layout().addWidget(itm)

    def clear_view(self):
        for e in self.entries.keys():
            self.entries[e].deleteLater()
        self.entries = dict()

    def add_item_to_segment(self, scr_id, img):
        if scr_id in self.screenshot_segm_mapping:
            self.entries[self.screenshot_segm_mapping[scr_id]].screenshot_view.add_image(numpy_to_pixmap(img))

class SegmentVisualizationItem(QWidget):
    onSelected = pyqtSignal(object)

    def __init__(self, db_project:DBProject, db_segment:DBSegment, db_screenshots = None, imgs = None):
        super(SegmentVisualizationItem, self).__init__()
        self.setLayout(QHBoxLayout())
        self.info_widget = QWidget(self)
        self.screenshot_view = EMultiGraphicsView(self, True)
        self.layout().addWidget(self.info_widget)
        self.layout().addWidget(self.screenshot_view)
        self.info_widget.setLayout(QVBoxLayout())
        self.info_widget.setFixedWidth(200)
        self.db_segment = db_segment
        self.setStyleSheet("QWidget{background:transparent;}")


        self.lbl_movie = QLabel(db_project.name, self)
        self.lbl_segment_id = QLabel(str(db_segment.segment_id), self)
        self.lbl_segment_dsc = QLabel(db_segment.segm_body, self)
        self.lbl_segment_dsc.setWordWrap(True)

        self.info_widget.layout().addWidget(self.lbl_movie)
        self.info_widget.layout().addWidget(self.lbl_segment_id)
        self.info_widget.layout().addWidget(self.lbl_segment_dsc)
        self.hovered = False

    def mousePressEvent(self, a0: QtGui.QMouseEvent):
        self.onSelected.emit(self.db_segment)

    def enterEvent(self, a0: QEvent):
        self.hovered = True

    def leaveEvent(self, a0: QEvent):
        self.hovered = False

    def paintEvent(self, a0: QPaintEvent):
        if self.hovered:
            qp = QPainter()
            pen = QPen()

            qp.begin(self)
            pen.setColor(QColor(255, 160, 47, 100))
            qp.setPen(pen)
            qp.fillRect(self.rect(), QColor(255, 160, 47, 50))
            qp.drawRect(self.rect())

            qp.end()



