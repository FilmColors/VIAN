from vian.core.analysis.analysis_import import *

from vian.core.container.project import *
from vian.core.container.vocabulary_library import VocabularyLibrary
from vian.core.data.exporters import ScreenshotExporter

# project =  VIANProject().load_project("C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni/Demo-Swissuni.eext")
#
# for s in project.screenshots:
#     print(s.get_connected_analysis())
#
# device = ScreenshotExporter("{Timestamp}.jpg", semantic_segmentation=ScreenshotExporter.SemSeg_Outlines)
# project.export(device, "C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni\shots")

library = VocabularyLibrary().load("data/library.json")
with VIANProject().load_project("C:/Users/gaude\Documents\VIAN\projects\megumi/4711_1_1_Saiyuki_1960_DVD - Kopie.eext", library=library) as project:
    uids = [v.unique_id for v in project.vocabularies]
    project.log_env("Saijyuki")
# library = None
# with VIANProject().load_project("C:/Users/gaude\Documents\VIAN\projects\megumi/4367_1_1_The_Old_Mill_1937_DVD - Kopie.eext", library=library) as project:
#     uids = [v.unique_id for v in project.vocabularies]
#     project.log_env("The_Band_Concert")

    # for i, uid in enumerate(uids):
    #     print(project.vocabularies[i].name, uids.count(uid))
    #
    # for v in project.vocabularies:
    #     if "Surface" in v.name:
    #         print(v.name)
    #         for w in v.words_plain:
    #             print(w.name)
    #         print("\n\n")
    #
    # for clobj in project.get_default_experiment().classification_objects:
    #     print(clobj.name)
    #
    #     ukws = [u.word_obj.unique_id for u in clobj.unique_keywords]
    #     for v in clobj.classification_vocabularies:
    #         print("\t --", v.name)
    #         if "Surface" in v.name:
    #             print("\t\t --", v.name, [(w.name, ukws.count(w.unique_id)) for w in v.words_plain])
    #
    #
