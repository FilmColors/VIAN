import os
import shutil
from core.container.project import VIANProject

from core.analysis.analysis_utils import run_analysis
from core.analysis.palette_analysis import ColorPaletteAnalysis

with VIANProject().load_project("C:\\Users\\gaude\\Documents\\VIAN\\projects\\506_1_1_SouthPacific_1958_DVD\\506_1_1_SouthPacific_1958_DVD.eext") as p:
    p.analysis = []
    p.store_project()
