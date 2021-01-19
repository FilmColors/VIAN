from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

def dialog_with_margin(mw:QMainWindow, dialog:QMainWindow, mode="md"):
    if isinstance(mode, str):
        if mode == "lg":
            f = 0.86
        elif mode == "md":
            f = 0.68
        else:
            f = 0.32
    else:
        f = mode

    rw = int(mw.width() * f)
    rh = int(mw.height() * f)
    ow = int((mw.width() - rw)/ 2)
    oh = int((mw.height() - rh) / 2)

    dialog.move(ow, oh)
    dialog.resize(rw, rh)
