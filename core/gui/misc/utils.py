from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

def dialog_with_margin(mw:QMainWindow, dialog:QMainWindow):
    rw = int(mw.width() * 0.68)
    rh = int(mw.height() * 0.68)
    ow = int((mw.width() - rw)/ 2)
    oh = int((mw.height() - rh) / 2)

    dialog.move(ow, oh)
    dialog.resize(rw, rh)
