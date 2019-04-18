from core.analysis.analysis_import import *
import json

def write_requirements_file(file, segment_analyses, screenshot_analyses, annotation_analyses):
    with open(file, "w") as f:
        data = dict(
            segment_analyses = segment_analyses,
            screenshot_analyses = screenshot_analyses,
            annotation_analyses = annotation_analyses,
            threshold = 0.9
        )
        json.dump(data, f)

def read_requirements_file(file):
    with open(file, "r") as f:
        d = json.load(f)
    return d

if __name__ == '__main__':
    segment_analyses = [
        (ColorFeatureAnalysis.__name__, "Global"),
        (ColorPaletteAnalysis.__name__, "Global"),
        (ColorHistogramAnalysis.__name__, "Global")
    ]
    screenshot_analyses = [
        (SemanticSegmentationAnalysis.__name__, "Global"),
        (ColorFeatureAnalysis.__name__, "Foreground"),
        (ColorFeatureAnalysis.__name__, "Background"),
        (ColorFeatureAnalysis.__name__, "Global"),
        (ColorPaletteAnalysis.__name__, "Foreground"),
        (ColorPaletteAnalysis.__name__, "Background"),
        (ColorPaletteAnalysis.__name__, "Global")
    ]
    write_requirements_file("pipeline_requirements.json", segment_analyses, screenshot_analyses, [])