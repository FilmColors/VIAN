
from core.data.headless import load_project_headless
from core.data.exporters import CSVExporter

project, mw = load_project_headless("F:\\_projects\\21_1_1_Imitation of Life\\21_1_1_Imitation of Life.eext")
project.export(CSVExporter(export_segmentations=True, export_keywords=True), "F:\\_projects\\21_1_1_Imitation of Life\\csv_out")