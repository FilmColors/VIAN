import os
import shutil
from core.container.project import VIANProject

from core.analysis.analysis_utils import run_analysis
from core.analysis.palette_analysis import ColorPaletteAnalysis
os.mkdir("test")

try:
    project = VIANProject(path="test/test_project.eext",
                          movie_path="C:\\Users\\gaude\\Documents\\VIAN\\projects\\trailer.mp4").__enter__()
    project.store_project()

    segmentation = project.create_segmentation("Some Segmentation")
    segment = segmentation.create_segment2(0, 1000, body="Region to Analyse")

    ColorPaletteAnalysis().fit(segment, callback=None)





except Exception as e:
    raise e
finally:
    project.close()
    shutil.rmtree("test")
