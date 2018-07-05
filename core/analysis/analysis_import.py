from core.analysis.color_feature_extractor import *
from core.analysis.palette_analysis import *
from core.analysis.barcode_analysis import *
from core.analysis.movie_mosaic.movie_mosaic import *
from core.analysis.colorimetry.colormetry2 import *
try:
    from core.analysis.semantic_segmentation import *
except:
    class SemanticSegmentationAnalysis(IAnalysisJob):
        def __init__(self):
            super(SemanticSegmentationAnalysis, self).__init__("Semantic Segmentation", [SCREENSHOT, SCREENSHOT_GROUP],
                                                               author="Gaudenz Halter",
                                                               version="1.0.0",
                                                               multiple_result=False)