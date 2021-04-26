from core.container.project import VIANProject
from core.data.exporters import SegmentationExporter


project = VIANProject().load_project("myproject.eext")
project.export(SegmentationExporter(), "something.csv")