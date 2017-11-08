from PyQt5.QtCore import Qt
from enum import Enum


class Commands(Enum):
    KEY_SAVE = 0,
    KEY_OPEN = 1,
    KEY_SCREENSHOT = 2,
    KEY_SWITCH_PERSPECTIVE = 3,


class KeyBinding():
    def __init__(self, key, cmd, shift = False, alt = False, ctrl = False):
        self.key = key
        self.shift = shift
        self.alt = alt
        self.ctrl = ctrl
        self.cmd = cmd

# KEY BINDINGS
KEY_SAVE = KeyBinding(Qt.Key_S,Commands.KEY_SAVE, ctrl = True)
KEY_OPEN = KeyBinding(Qt.Key_O,Commands.KEY_OPEN, ctrl = True)
KEY_SCREENSHOT = KeyBinding(Qt.Key_F, Commands.KEY_SCREENSHOT, ctrl = True)
KEY_SWITCH_PERSPECTIVE = KeyBinding(Qt.Key_Q, Commands.KEY_SWITCH_PERSPECTIVE, ctrl = True)


key_binding = [
    KEY_SAVE,
    KEY_OPEN,
    KEY_SCREENSHOT,
    KEY_SWITCH_PERSPECTIVE
               ]






