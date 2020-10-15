import os
import cv2

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QPoint
from core.data.computation import pixmap_to_numpy
from core.data.log import log_error
from core.gui.ewidgetbase import EDialogWidget, EGraphicsView, FileBrowseBar


class ExportNamingConventionWidget(QWidget):
    last_convention = []

    def __init__(self, parent, naming_fields):
        super(ExportNamingConventionWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.upper = QHBoxLayout(self)
        self.lower = QHBoxLayout(self)
        self.preview = QLineEdit("preview_name", self)
        self.layout().addItem(self.upper)
        self.layout().addItem(self.lower)
        self.lower.addWidget(self.preview)
        self.boxes = []
        self.naming_fields = naming_fields
        self.convention_exists = False
        for i, (k, v) in enumerate(naming_fields.items()):
            cb = QComboBox(self)
            cb.addItem("None")
            cb.addItems(naming_fields.keys())
            if len(self.last_convention) > 0:
                try:
                    cb.setCurrentText(self.last_convention[i])
                    self.convention_exists = True
                except:
                    continue
            self.boxes.append(cb)
            self.upper.addWidget(cb)

            cb.currentIndexChanged.connect(self.on_changed)

        # This could fail because the fields are not guaranteed to be present. If so we just keep the default values
        try:
            if self.convention_exists is False:
                if  self.naming_fields['corpus_id'] != "":
                    self.boxes[0].setCurrentText("corpus_id")
                    self.boxes[1].setCurrentText("keywords_include")
                    self.boxes[2].setCurrentText("keywords_exclude")
                    self.boxes[3].setCurrentText("year")
                    self.boxes[4].setCurrentText("k_images")
                    self.boxes[5].setCurrentText("classification_obj")
                else:
                    self.boxes[0].setCurrentText("None")
                    self.boxes[1].setCurrentText("keywords_include")
                    self.boxes[2].setCurrentText("keywords_exclude")
                    self.boxes[3].setCurrentText("year")
                    self.boxes[4].setCurrentText("k_images")
                    self.boxes[5].setCurrentText("classification_obj")
        except:
            pass

        self.on_changed()
        self.show()

    def on_changed(self):
        self.preview.setText(self.get_naming())

    def get_naming(self):
        name = []
        self.last_convention.clear()

        for cb in self.boxes:
            if cb.currentText() != "None":
                v = self.naming_fields[cb.currentText()]
                if v != "":
                    name.append(v)
            self.last_convention.append(cb.currentText())
        name.append(self.naming_fields['plot_name'])
        return "_".join(name)


class ExportImageDialog(EDialogWidget):
    last_directories = []
    last_background = dict()
    last_grid_color = dict()
    last_size = dict()
    last_font_size = dict()
    last_preset = dict()

    def __init__(self, main_window, visualization):
        super(ExportImageDialog, self).__init__(visualization, main_window)
        path = os.path.abspath("qt_ui/DialogExportImage.ui")
        uic.loadUi(path, self)
        self.directory = ""
        self.visualization = visualization
        self.preview = ExportPreviewWidget(self, self.visualization)
        self.widgetNamingConvention.setLayout(QVBoxLayout())
        self.naming_widget = ExportNamingConventionWidget(self, visualization.naming_fields)
        self.widgetNamingConvention.layout().addWidget(self.naming_widget)
        self.file_browser = FileBrowseBar(self, mode="dir", name="Directory:")

        self.orig_grid_color = self.visualization.grid_color
        self.orig_font_size = self.visualization.font_size

        self.ratio = 1.0
        self.force_ratio = False
        self.load_cache()

        if self.visualization.get_scene() is not None:
            size = self.visualization.get_scene().itemsBoundingRect()
            self.ratio = size.height() / size.width()

        self.widgetNamingConvention.layout().addWidget(self.file_browser)
        self.widget_Preview.setLayout(QVBoxLayout(self))
        self.widget_Preview.layout().addWidget(self.preview)
        self.spinBox_BG_R.valueChanged.connect(self.on_update)
        self.spinBox_BG_G.valueChanged.connect(self.on_update)
        self.spinBox_BG_B.valueChanged.connect(self.on_update)
        self.spinBox_BG_A.valueChanged.connect(self.on_update)
        self.spinBox_GridR.valueChanged.connect(self.on_update)
        self.spinBox_GridG.valueChanged.connect(self.on_update)
        self.spinBox_GridB.valueChanged.connect(self.on_update)
        self.spinBox_GridA.valueChanged.connect(self.on_update)
        self.spinBox_Width.valueChanged.connect(self.on_update)
        self.spinBox_Height.valueChanged.connect(self.on_update)
        self.spinBoxFontSize.valueChanged.connect(self.on_update)
        self.spinBoxFontSize.setValue(self.visualization.font_size)
        self.comboBoxPreset.currentTextChanged.connect(self.on_preset)
        self.spinBox_GridLine.valueChanged.connect(self.on_update)

        self.spinBox_Height.setEnabled(False)

        self.btn_Export.clicked.connect(self.on_export)
        self.btn_Cancel.clicked.connect(self.on_close)
        self.btn_ResetRegion.clicked.connect(self.preview.reset_region)
        self.on_update()

    def on_preset(self):
        if self.comboBoxPreset.currentText() == "White Background":
            self.spinBox_BG_R.setValue(255)
            self.spinBox_BG_G.setValue(255)
            self.spinBox_BG_B.setValue(255)
            self.spinBox_BG_A.setValue(255)
            self.spinBox_GridR.setValue(0)
            self.spinBox_GridG.setValue(0)
            self.spinBox_GridB.setValue(0)
            self.spinBox_GridA.setValue(255)
        elif self.comboBoxPreset.currentText() == "Dark Background":
            self.spinBox_BG_R.setValue(27)
            self.spinBox_BG_G.setValue(27)
            self.spinBox_BG_B.setValue(27)
            self.spinBox_BG_A.setValue(255)
            self.spinBox_GridR.setValue(255)
            self.spinBox_GridG.setValue(255)
            self.spinBox_GridB.setValue(255)
            self.spinBox_GridA.setValue(255)
        else:
            self.spinBox_BG_R.setValue(255)
            self.spinBox_BG_G.setValue(255)
            self.spinBox_BG_B.setValue(255)
            self.spinBox_BG_A.setValue(255)
            self.spinBox_GridR.setValue(0)
            self.spinBox_GridG.setValue(0)
            self.spinBox_GridB.setValue(0)
            self.spinBox_GridA.setValue(0)

    def load_cache(self):
        if self.visualization.naming_fields['plot_name'] in self.last_preset:
            last_presets = self.last_preset[self.visualization.naming_fields['plot_name']]
            if len(last_presets) > 0:
                self.comboBoxPreset.setCurrentText(last_presets[0])

        if self.visualization.naming_fields['plot_name'] in self.last_background:
            last_backgrounds = self.last_background[self.visualization.naming_fields['plot_name']]
            if len(last_backgrounds) > 0:
                self.spinBox_BG_R.setValue(last_backgrounds[0].red())
                self.spinBox_BG_G.setValue(last_backgrounds[0].green())
                self.spinBox_BG_B.setValue(last_backgrounds[0].blue())
                self.spinBox_BG_A.setValue(last_backgrounds[0].alpha())

        if self.visualization.naming_fields['plot_name'] in self.last_grid_color:
            last_grid_color =  self.last_grid_color[self.visualization.naming_fields['plot_name']]
            if len(last_grid_color) > 0:
                self.spinBox_GridR.setValue(last_grid_color[0].red())
                self.spinBox_GridG.setValue(last_grid_color[0].green())
                self.spinBox_GridB.setValue(last_grid_color[0].blue())
                self.spinBox_GridA.setValue(last_grid_color[0].alpha())

        if self.visualization.naming_fields['plot_name'] in self.last_size:
            last_size = self.last_size[self.visualization.naming_fields['plot_name']]
            if len(last_size) > 0:
                self.spinBox_Width.setValue(last_size[0].width())
                self.spinBox_Height.setValue(last_size[0].height())

        if self.visualization.naming_fields['plot_name'] in self.last_font_size:
            last_font_size = self.last_font_size[self.visualization.naming_fields['plot_name']]
            if len(last_font_size) > 0:
                self.spinBoxFontSize.setValue(last_font_size[0])

        if len(self.last_directories) > 0:
            self.file_browser.line_edit.setText(self.last_directories[len(self.last_directories) - 1])

    def on_update(self):
        background = QColor(self.spinBox_BG_R.value(), self.spinBox_BG_G.value(), self.spinBox_BG_B.value(), self.spinBox_BG_A.value())
        grid = QColor(self.spinBox_GridR.value(), self.spinBox_GridG.value(), self.spinBox_GridB.value(), self.spinBox_GridA.value())
        font_size = self.spinBoxFontSize.value()

        if not self.checkBox_Transparent.isChecked():
            background.setAlpha(255)

        width = self.spinBox_Width.value()
        height = width * self.ratio
        size = QSize(width, height)
        self.visualization.grid_color = grid
        self.visualization.font_size = font_size
        self.visualization.grid_line_width = self.spinBox_GridLine.value()

        image = self.visualization.render_to_image(background, size)
        self.preview.set_image(image)

        # Caching
        if not self.visualization.naming_fields['plot_name'] in self.last_background:
            self.last_background[self.visualization.naming_fields['plot_name']] = []
        if not self.visualization.naming_fields['plot_name'] in self.last_grid_color:
            self.last_grid_color[self.visualization.naming_fields['plot_name']] = []
        if not self.visualization.naming_fields['plot_name'] in self.last_size:
            self.last_size[self.visualization.naming_fields['plot_name']] = []
        if not self.visualization.naming_fields['plot_name'] in self.last_font_size:
            self.last_font_size[self.visualization.naming_fields['plot_name']] = []
        if not self.visualization.naming_fields['plot_name'] in self.last_preset:
            self.last_preset[self.visualization.naming_fields['plot_name']] = []

        self.last_background[self.visualization.naming_fields['plot_name']].clear()
        self.last_grid_color[self.visualization.naming_fields['plot_name']].clear()
        self.last_size[self.visualization.naming_fields['plot_name']].clear()
        self.last_font_size[self.visualization.naming_fields['plot_name']].clear()
        self.last_preset[self.visualization.naming_fields['plot_name']].clear()

        self.last_background[self.visualization.naming_fields['plot_name']].append(background)
        self.last_grid_color[self.visualization.naming_fields['plot_name']].append(grid)
        self.last_size[self.visualization.naming_fields['plot_name']].append(size)
        self.last_font_size[self.visualization.naming_fields['plot_name']].append(font_size)
        self.last_preset[self.visualization.naming_fields['plot_name']].append(self.comboBoxPreset.currentText())
        return image

    def on_export(self):
        img = self.on_update()
        self.directory = self.file_browser.get_path()
        if not os.path.isdir(self.directory):
            if self.main_window is not None:
                file_name = QFileDialog.getSaveFileName(self, self.naming_widget.get_naming() + ".png",
                                                        directory=self.main_window.project.export_dir,
                                                        filter="*.png *.jpg")[0]
            else:
                file_name = QFileDialog.getSaveFileName(self, self.naming_widget.get_naming() + ".png",
                                                        filter="*.png *.jpg")[0]
        else:
            self.last_directories.append(self.directory)
            file_name = os.path.join(self.directory, self.naming_widget.get_naming() + ".png")

        if os.path.isfile(file_name):
            msgBox = QMessageBox()
            msgBox.setText("A File with this name already exists, "
                                                      "how do you want to proceed. ")
            msgBox.addButton(QPushButton('Overwrite'), QMessageBox.YesRole)
            msgBox.addButton(QPushButton('Create Unique Name'), QMessageBox.NoRole)
            msgBox.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)

            ret = msgBox.exec_()

            if ret == 0:
                file_name = file_name
            elif ret == 1:
                file_name_new = file_name
                ftype = "." + file_name.split(".")[-1:][0]
                c = 1
                while(os.path.isfile(file_name_new)):
                    file_name_new = file_name.replace(ftype, "") + "_" + str(c).zfill(2) + ftype
                    c += 1
                file_name = file_name_new
            else:
                return

        try:
            region = self.preview.region
            size = QSize(self.spinBox_Width.value(), self.spinBox_Height.value())

            img = pixmap_to_numpy(QPixmap(img))

            if region is not None:
                img = img[
                      int(region.y()):int(region.y() + region.height()),
                      int(region.x()):int(region.x() + region.width())
                      ]

                img = cv2.resize(img, (size.width(), size.height()), interpolation=cv2.INTER_CUBIC)

            cv2.imwrite(file_name, img)
            self.on_close()
        except Exception as e:
            log_error(e)
            pass

    def on_close(self):
        self.visualization.grid_color = self.orig_grid_color
        self.visualization.font_size = self.orig_font_size
        self.visualization.render_to_image(QColor(0, 0, 0, 255), size = QSize(self.spinBox_Width.value(), self.spinBox_Height.value()))
        self.close()


class ExportPreviewWidget(QGraphicsView):
    onResize = pyqtSignal()
    def __init__(self, parent, visualization):
        super(ExportPreviewWidget, self).__init__(parent)
        self.visualization = visualization
        self.gscene = QGraphicsScene()
        self.setScene(self.gscene)

        self.image = None
        self.image_item = None

        self.is_selecting = False
        self.p_start = QPoint()
        self.p_end = QPoint()
        self.region = None
        self.selector_frame = self.gscene.addRect(self.sceneRect(), QColor(255, 255, 255))
        self.onResize.connect(self.frame_image)
        self.last_size = QSize()


    def reset_region(self):
        self.region = None
        self.selector_frame.setRect(self.sceneRect())

    def set_image(self, image:QImage):
        self.image = image
        self.gscene.clear()
        pen = QPen()
        pen.setWidthF(10)
        pen.setColor(QColor(255,255,255))
        self.image_item = self.gscene.addPixmap(QPixmap(image))
        self.selector_frame = self.gscene.addRect(self.sceneRect(), pen)

    def frame_image(self):
        if self.image_item is not None:
            rect = self.image_item.sceneBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent):
        super(ExportPreviewWidget, self).resizeEvent(event)
        if abs(self.last_size.width() - self.width()) > 5 or abs(self.last_size.height() - self.height()) > 5:
            self.onResize.emit()
            self.last_size = self.size()

    def start_selection(self, pos):
        self.is_selecting = True
        self.p_start = pos

    def update_selection(self, pos):
        new_s = QPoint()
        new_e = QPoint()
        if pos.x() > self.p_start.x():
            new_s.setX(self.p_start.x())
            new_e.setX(pos.x())
        else:
            new_s.setX(pos.x())
            new_e.setX(self.p_start.x())

        if pos.y() > self.p_end.y():
            new_s.setY(self.p_start.y())
            new_e.setY(pos.y())
        else:
            new_s.setY(pos.y())
            new_e.setY(self.p_start.y())

        self.selector_frame.setRect(new_s.x(), new_s.y(), new_e.x() - new_s.x(), new_e.y() - new_s.y())

    def end_selection(self):
        self.is_selecting = False
        self.region = self.selector_frame.sceneBoundingRect()

    def mousePressEvent(self, event: QMouseEvent):
        self.start_selection(self.mapToScene(event.pos()))

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_selecting:
            self.update_selection(self.mapToScene(event.pos()))

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.end_selection()

    def update(self):
        super(ExportPreviewWidget, self).update()
        self.onResize.emit()




