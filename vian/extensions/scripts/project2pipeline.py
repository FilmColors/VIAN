import os
import os.path
import pickle
from core.data.headless import load_project_headless, create_project_headless
projects = []
all_scrs = []
# 122;1;1;2;1;default;880.0;F:/fiwi_datenbank/SCR/122_1_1\2_1_122_1_1.jpg
# for dirpath, dirnames, filenames in os.walk("E:\Programming\Datasets\MPI\Analysiert"):
#     for filename in [f for f in filenames if f.endswith(".eext")]:
#         projects.append(os.path.join(dirpath, filename))
#
# with open("E:\Programming\Datasets\MPI\_cache\parsing.pickle", "rb") as f:
#     d = pickle.load(f)
#
# all_projects = dict()
# for t in d['all_projects']:
#     all_projects["_".join(t[0])] = t[1]
#
#
# # n_found = 0
# # n_not_fount = 0
# # out = "E:\Programming\Datasets\MPI\_projects\\"
# for f in projects:
#     project, mw = load_project_headless(f)
#     if project is None:
#         continue
#     mid = project.movie_descriptor.movie_id
#     if not mid in all_projects:
#         continue
#
#     segmentation = None
#     for s in project.segmentation:
#         if len(s.segments) == len(all_projects[mid]):
#             segmentation = s
#             break
#     if segmentation is None:
#         continue
#
#     print("OK", segmentation)
#     print(len(all_projects[mid]))
#     print("#################")
#     print()
#     print()
project, mw = load_project_headless("E:\Programming\Datasets\MPI\_projects\\205_Vertigo_1958\\205_2_1_Vertigo_1958\\205_2_1_Vertigo_1958_MPI_02072018_1040_VR_VIAN\\205_2_1_Vertigo_1958_MPI_02072018_1040_VR_VIAN.eext")
project.apply_template("../../data/templates/ERC_FilmColors.viant")
new = Experiment().deserialize(e, self)