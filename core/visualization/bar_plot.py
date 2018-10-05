from core.visualization.basic_vis import IVIANVisualization
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class BarPlot(QGraphicsView, IVIANVisualization):
    def __init__(self, parent, title =""):
        super(BarPlot, self).__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.curr_scale = 1.0
        self.bar_height = 20
        self.raw_data = []
        self.points = []
        self.ctrl_is_pressed = False

    def clear_view(self):
        self.scene().clear()
        self.raw_data = []
        self.points = []

    def add_bar(self, title, x, col_bar = QColor(255,255,255,100), col_text = QColor(255,255,255,255)):
        p = QPen()
        p.setColor(col_bar)
        p.setWidth(0.1)

        px = 0
        py = len(self.points) * (self.bar_height + 5)

        point = self.scene().addRect(px, py, x, self.bar_height, p, QBrush(col_bar))

        text = self.scene().addText(title)
        text.setPos(px - 10 - len(title) * 5, py)
        text.setDefaultTextColor(col_text)

        self.points.append((point, text))
        self.raw_data.append((title, x, col_bar, col_text))

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-1000, -1000, 2000, 2000)
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