
from core.data.headless import load_project_headless
from core.data.exporters import CSVExporter, _ScreenshotExporter, ImageType

project, mw = load_project_headless("C:\\Users\\gaude\\Desktop\\16_1_1_The Age of Innocence\\16_1_1_The Age of Innocence.eext")
project.export(CSVExporter(export_segmentations=True, export_keywords=True), "C:\\Users\\gaude\\Desktop\\16_1_1_The Age of Innocence\\csv_out")

project.movie_descriptor.set_movie_path("C:\\Users\\gaude\\Desktop\\16_1_1_MOV.mov")
mw.load_screenshots()
project.export(_ScreenshotExporter(naming = None, image_type=ImageType.JPG, smooth=False), "C:\\Users\\gaude\\Desktop\\16_1_1_The Age of Innocence\\shots\\")