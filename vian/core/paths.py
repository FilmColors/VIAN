import os

def get_root_dir():
    return os.path.abspath(os.path.split(__file__)[0] + "/../") + "/"