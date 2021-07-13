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

with VIANProject().load_project("C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni/Demo-Swissuni.eext") as project:
    pass
    for s in project.screenshots:
        print(s.get_connected_analysis())

    device = ScreenshotExporter("{Timestamp}_outline.jpg", semantic_segmentation=ScreenshotExporter.SemSeg_Outlines)
    project.export(device, "C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni\shots")

    device = ScreenshotExporter("{Timestamp}_both.jpg", semantic_segmentation=ScreenshotExporter.SemSeg_OutlinesFilled)
    project.export(device, "C:/Users/gaude\Documents\VIAN\projects\Demo-Swissuni\shots")