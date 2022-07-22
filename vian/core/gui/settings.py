from PyQt6 import QtCore
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QLabel, QFrame, QVBoxLayout, QWidget, QComboBox


class SettingsLabel(QLabel):
    onSizeChanged = pyqtSignal()
    def __init__(self):
        super(SettingsLabel, self).__init__()
        self.setText("Settings")

    def paintEvent(self, a0):
        super(SettingsLabel, self).paintEvent(a0)
        self.onSizeChanged.emit()


class SettingsWidgetBase(QFrame):
    onSizeChanged = pyqtSignal()
    def __init__(self, settingsWidget, parent=None):
        super(SettingsWidgetBase, self).__init__(parent=parent)

        self.main_layout = QVBoxLayout()

        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.title = SettingsLabel()
        self.title.onSizeChanged.connect(self.titleSizeChanged)
        self.main_layout.addWidget(self.title)

        self.settings_widget = settingsWidget

        self.main_layout.addWidget(self.settings_widget)
        self.settings_widget.setVisible(False)

        self.setLayout(self.main_layout)

        parent.installEventFilter(self)

    def eventFilter(self, a0: 'QObject', a1: 'QEvent') -> bool:
        if isinstance(a1, QResizeEvent):
            self.repositionSettings()
        return False  # pass all the event further to the parent. We don't stop any event here.

    def enterEvent(self, event) -> None:
        self.settings_widget.setVisible(True)
        self.adjustSize()
        self.repositionSettings()

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        elementsList = self.settings_widget.findChildren(QComboBox)
        for element in elementsList:
            if element.view().isVisible():
                return
        self.settings_widget.setVisible(False)
        self.adjustSize()
        self.repositionSettings()

    def titleSizeChanged(self):
        self.adjustSize()
        self.repositionSettings()

    def repositionSettings(self):
        self.raise_()
        self.move(self.parent().size().width() - self.geometry().width(), 0)