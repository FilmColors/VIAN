from PyQt5.QtWidgets import QDockWidget, QMainWindow

GAPLUGIN_WNDTYPE_MAINWINDOW = 0
GAPLUGIN_WNDTYPE_DOCKWIDGET = 1

class GAPlugin(object):
    def __init__(self,main_window):
        self.plugin_name = "Plugin"
        self.main_window = main_window
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self):
        wnd = QMainWindow(self.main_window)
        wnd.setWindowTitle(self.plugin_name)
        wnd.show()


