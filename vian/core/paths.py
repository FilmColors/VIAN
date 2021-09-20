import os, sys


# If 'frozen' is set, this is a PyInstaller version, else we are in python source code
# In PyInstaller, this file does nto exist anymore, we thus have to define the source from the executable
if getattr(sys, 'frozen', False):
    _application_path = os.path.dirname(sys.executable)
elif __file__:
    _application_path = os.path.abspath(os.path.dirname(__file__) + "/../")


def get_root_dir():
    return _application_path


def get_vian_data(append = None) -> str:
    """
    Returns the absolut path of the data dir.
    If append is not none, append is added to the data dir path.

    :param append:
    :return:
    """
    data_root = os.path.join(get_root_dir(), "data")
    if append is not None:
        data_root = os.path.join(data_root, append)
    return data_root