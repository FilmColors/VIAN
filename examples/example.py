
from core.data.headless import load_project_headless
from core.data.exporters import CSVExporter, _ScreenshotExporter, ImageType

project, context = load_project_headless("F:\\_projects\\328_1_1_Total Recall\\328_1_1_Total Recall.eext")
context.load_screenshots()
