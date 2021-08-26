from vian.core.visualization.basic_vis import IVIANVisualization
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np

class BarPlot(QGraphicsView, IVIANVisualization):
    def __init__(self, parent, title ="", naming_fields = None):
        QGraphicsView.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "bar_plot"
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.curr_scale = 1.0
        self.bar_height = 20
        self.max_width = 1000
        self.raw_data = []
        self.points = []
        self.ctrl_is_pressed = False

    def clear_view(self):
        self.scene().clear()
        self.raw_data = []
        self.points = []

    def add_title(self, text):
        f = QFont()
        f.setPointSize(30)
        p = self.scene().addText(text, f)
        p.setPos(0, -30)

    def add_bar(self, title, x, col_bar = QColor(255,255,255,100), col_text = QColor(255,255,255,255)):
        self.raw_data.append((title, x, col_bar, col_text))

        xmax = np.amax([t[1] for t in self.raw_data])
        if xmax == 0:
            xmax = 1.0
        self.scene().clear()
        self.points = []
        py = 0
        for r in self.raw_data:
            title = r[0]
            x = r[1]
            col_bar = r[2]
            col_text = r[3]

            p = QPen()
            p.setColor(col_bar)
            p.setWidth(0.1)

            px = 0
            py = len(self.points) * (self.bar_height + 5)

            point = self.scene().addRect(px, py, x / xmax * self.max_width, self.bar_height, p, QBrush(col_bar))

            text = self.scene().addText(title)
            text.setPos(px - 10 - len(title) * 5, py)
            text.setDefaultTextColor(col_text)

            self.points.append((point, text))

        p = QPen()
        p.setColor(QColor(255,255,255,200))
        f = QFont()
        f.setPointSize(12)
        if xmax < 10:
            label_step = 1
        else:
            label_step = xmax / 10
        for i, val in enumerate(range(int(xmax + 1))):

            x = val / xmax * self.max_width
            self.scene().addLine(x, py, x, py + 20, p)
            if int(xmax) % label_step == 0:
                lbl = self.scene().addText(str(round(val, 2)), f)
                lbl.setDefaultTextColor(QColor(255,255,255,200))
                center_delta = lbl.boundingRect().width() / 2
                lbl.setPos(x - center_delta, py + 20)

        self.frame_default()

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-50, -50, 100, 100)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        elif event.key() == Qt.Key_F:
            self.frame_default()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.001:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(QGraphicsView, self).wheelEvent(event)
