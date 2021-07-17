from core.analysis.analysis_import import *

from core.container.project import *
from core.data.exporters import ScreenshotExporter

# project =  VIANProject().load_project("C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni/Demo-Swissuni.eext")
#
# for s in project.screenshots:
#     print(s.get_connected_analysis())
#
# device = ScreenshotExporter("{Timestamp}.jpg", semantic_segmentation=ScreenshotExporter.SemSeg_Outlines)
# project.export(device, "C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni\shots")

with VIANProject().load_project("C:/Users/gaude\Documents\VIAN\projects\megumi/4711_1_1_Saiyuki_1960_DVD - Kopie.eext") as project:
    for v in project.vocabularies:
        print(v.name)
    pass
