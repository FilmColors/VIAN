"""
Converts a pre HDF5 managed project to such a project.
This change has been happening in the 0.7.0
"""

import glob

from vian.core.data.headless import *

if __name__ == '__main__':
    for f in glob.glob("F:\\_webapp\\old\\229_1_1_Jigokumon_1953\\*.eext"):
        old_project, mw = load_project_headless(f)
        old_project.hdf5_manager.initialize_all()
        new_analyses = []
        to_remove = []
        for i, a in enumerate(old_project.analysis):
            if a.analysis_job_class == "Colormetry":
                continue
            elif a.analysis_job_class == "SemanticSegmentationAnalysis":
                try:
                    data = a.dep_get_adata()
                    new = SemanticSegmentationAnalysisContainer(
                            name="Semantic Segmentation",
                            results=data['mask'],
                            analysis_job_class=SemanticSegmentationAnalysis,
                            parameters=a.parameters,
                            container=a.target_container,
                            dataset=data['dataset']
                        )
                    new_analyses.append(new)
                    to_remove.append(a)
                except Exception as e:
                    print(e)
            else:
                try:
                    a.set_adata(a.dep_get_adata())
                except Exception as e:
                    print(a.name, e)
        for a in to_remove:
            old_project.remove_analysis(a)
        for a in new_analyses:
            old_project.add_analysis(a)

        old_project.store_project()
