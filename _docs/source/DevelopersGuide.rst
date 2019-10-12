.. filmpalette documentation master file, created by
   sphinx-quickstart on Sun Jul 30 23:04:30 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=================
Developer's Guide
=================

Welcome to the Developer's Guide to VIAN.
The following Sections are devoted to explain the fundamental programming interfaces for extending
VIAN's functionality.

In a nutshell there exist three different interfaces to implement your own functionality into VIAN:

.. toctree::
    :maxdepth: 4

    dev_guide/analyses
    dev_guide/nodes
    dev_guide/plugins

Deciding which Interface to use
===============================
Depending on what method you want to implement, choose on of these Interfaces.

**Plug-Ins** are allow you to implement your completely own idea, the plug-in interface will give you access to the
VIAN Project. As such, **Plug-Ins** should be used if neither of **IAnalysisJob** and **Node** will do.

**IAnalysisJob** will give you the possibility to implement your own analysis procedure, which the user can call.
Such an implementation contains an *Procedure* and a *Visualization* of the yielded result.

**Node** a node is the most basic implementation, which allows you to enrich the functionality if VIAN's Node Editor.


Documentation
=============
.. toctree::
    :maxdepth: 4

    dev_guide/container
    dev_guide/data

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`