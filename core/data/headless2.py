# import os
#
# from core.container.project import VIANProject
#
#
# def create_project(name, path = None):
#     if path is not None:
#         folder = os.path.split(path)[0]
#     else:
#         folder = ""
#
#     new = VIANProject(name=name, path=path, folder=folder)
#     if path is not None:
#         new.create_file_structure()
#         new.connect_hdf5()
#         new.store_project()
#     return new
