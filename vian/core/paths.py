import os


def get_root_dir():
    return os.path.abspath(os.path.split(__file__)[0] + "/../") + "/"


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