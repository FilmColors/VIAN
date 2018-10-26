from core.data.headless import *




if __name__ == '__main__':
    old_project, mw = load_project_headless("F:/_webapp/old/3460_1_1_Do the Right Thing_1989/3460_1_1_Do the Right Thing_1989.eext")
    old_project.hdf5_manager.initialize_all()
    new_analyses = []
    to_remove = []
    for i, a in enumerate(old_project.analysis):
        if a.analysis_job_class == "Colormetry":
            continue
        elif a.analysis_job_class == "SemanticSegmentationAnalysis":
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
        else:
            a.set_adata(a.dep_get_adata())
    for a in to_remove:
        old_project.remove_analysis(a)
    for a in new_analyses:
        old_project.add_analysis(a)

    old_project.store_project(HeadlessUserSettings())