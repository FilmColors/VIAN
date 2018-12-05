from core.visualization.basic_vis import *

class VisualizationCache():
    def __init__(self, vis_class:IVIANVisualization.__class__, raw_data):
        self.vis_class = vis_class
        self.raw_data = raw_data