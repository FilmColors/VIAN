from PyQt5.QtWidgets import QDockWidget, QMainWindow

GAPLUGIN_WNDTYPE_MAINWINDOW = 0
GAPLUGIN_WNDTYPE_DOCKWIDGET = 1

class GAPlugin(object):
    """
    The GAPlugin is the Base-Class for all Plugins. 
    For creating your own Plugin, subclass GAPlugin an overwrite the GAPlugin.get_window() function. 
    Access current Project by using GAPlugin.get_project().
    """
    def __init__(self, main_window, plugin_name = "Plugin", windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW):
        """
        Initializes a Plugin.
        
        :param main_window: The VIAN MainWindow. 
        :param plugin_name: The Name of the Plugin
        :param windowtype: The returned WindowType, specified in plugin.py. This should be a variant of GAPLUGIN_WNDTYPE_*
        """
        self.plugin_name = plugin_name
        self.main_window = main_window
        self.windowtype = windowtype

    def get_window(self, parent):
        """
        This function should be overwritten shows your Plugin-Window. This can either be an EDockWidget or a WMainWindow. 
        (Specified accordingly to the GAplugin.windowtype)
        :param parent: 
        
        """
        wnd = QMainWindow(self.main_window)
        wnd.setWindowTitle(self.plugin_name)
        wnd.show()

    def get_project(self):
        return self.main_window.project

