from PyQt5 import uic
import os

from PyQt5 import uic

from core.gui.ewidgetbase import EDialogWidget


class WelcomeDialog(EDialogWidget):
    def __init__(self, parent, main_window):
        super(WelcomeDialog, self).__init__(main_window, parent)
        path = os.path.abspath("qt_ui/DialogWelcome.ui")
        uic.loadUi(path, self)


        self.checkBox.stateChanged.connect(self.on_changed)
        self.btn_OK.clicked.connect(self.on_ok)
        self.show()

    def on_changed(self, bool):
        self.main_window.settings.SHOW_WELCOME = not bool


    def on_ok(self):
        self.main_window.settings.store()
        self.close()