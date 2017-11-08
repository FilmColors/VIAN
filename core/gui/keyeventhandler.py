from core.data.keybinding import key_binding, Commands
from PyQt5.QtCore import Qt


class EKeyEventHandler():
    def __init__(self, main_window, focused_window = None):
        self.ctrl = False
        self.alt = False
        self.shift = False


        self.main_window = main_window
        self.focused_window = focused_window


    def pressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Control:
            self.ctrl = True
            return

        if key == Qt.Key_Alt:
            self.alt = True
            return

        if key == Qt.Key_Shift:
            self.shift = True
            return

        cmd = None
        for b in key_binding:
            if key == b.key and self.ctrl == b.ctrl and self.shift == b.shift and self.alt == b.alt:
                cmd = b.cmd

        if cmd is not None:
            self.handleEvent(cmd)

    def releaseEvent(self, event):
        key = event.key()
        if key == Qt.Key_Control:
            self.ctrl = False
            return

        if key == Qt.Key_Alt:
            self.alt = False
            return

        if key == Qt.Key_Shift:
            self.shift = False
            return

    def handleEvent(self, cmd):
        if cmd == Commands.KEY_OPEN:
            self.main_window.on_load_project()
            return

        if cmd == Commands.KEY_SAVE:
            self.main_window.on_save_project()
            return

        if cmd == Commands.KEY_SCREENSHOT:
            self.main_window.screenshot()
            return
