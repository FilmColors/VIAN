.. _Plugins:

Plug-Ins
========
A Plugin is the most basic class you can implement. Essentially a Plugin is a QMainWindow or a EDockWidget,
having access to the current project and the MainWindow.

Subclass the GAPlugin class an put your module into the *extensions/plugins* and your plugin will be listed in the MainWindow's menu under
tools/plugins.


..  autoclass:: core.data.plugin.GAPlugin
    :members: __init__, get_window


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`