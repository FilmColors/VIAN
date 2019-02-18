import glob
from core.data.headless import *
from threading import Thread

ALL_ANALYSES = [BarcodeAnalysisJob, MovieMosaicAnalysis, ColorHistogramAnalysis, ColorFeatureAnalysis, ColorPaletteAnalysis, SemanticSegmentationAnalysis]

for file in glob.glob("F:\\_webapp\\new\\*\\*.eext"):
    print(file)
    if "3460_1_1_Do" in file:
        continue
    try:
        # # file = "F:\\_webapp\\new\\016_1_1_The Age of Innocence_1993\\016_1_1_The Age of Innocence_1993.eext"
        project, mw = load_project_headless(file)
        # project.hdf5_manager.initialize_all(ALL_ANALYSES)
        #
        # # to_remove = []
        # # for a in project.analysis:
        # #     if a.analysis_job_class != "SemanticSegmentationAnalysis":
        # #         to_remove.append(a)
        # # for o in to_remove:
        # #     project.remove_analysis(o)
        #
        # fps = project.movie_descriptor.fps
        # glob = [project.experiments[0].get_classification_object_by_name("Global")]
        # cl_obj = [project.experiments[0].get_classification_object_by_name("Global"),
        #           project.experiments[0].get_classification_object_by_name("Foreground"),
        #           project.experiments[0].get_classification_object_by_name("Background")
        #           ]
        #
        # # project.clean_hdf5(ALL_ANALYSES)
        # # project.store_project(HeadlessUserSettings())
        # # project.hdf5_manager._index['ColorHistograms'] = 0
        # # project.hdf5_manager._index['ColorFeatures'] = 0
        # # project.hdf5_manager._index['ColorPalettes'] = 0
        #
        # mw.run_analysis_threaded(ColorFeatureAnalysis(), project.get_main_segmentation().segments, dict(resolution=30), glob, fps)
        # mw.run_analysis_threaded(ColorHistogramAnalysis(), project.get_main_segmentation().segments, dict(resolution=10), glob, fps)
        #
        # # mw.run_analysis_threaded(ColorFeatureAnalysis(), project.screenshots, dict(resolution=30), cl_obj, fps, n_targets=10)
        # # mw.run_analysis_threaded(ColorHistogramAnalysis(), project.screenshots, dict(resolution=30), cl_obj, fps, n_targets=10)
        # # mw.run_analysis_threaded(ColorPaletteAnalysis(), project.screenshots, dict(resolution=30), cl_obj, fps, n_targets=10)
        # # mw.run_analysis_threaded(ColorPaletteAnalysis(), project.get_main_segmentation().segments, dict(resolution=30), glob, fps, n_targets=10)
        # # mw.run_analysis_threaded(ColorPaletteAnalysis(), project.screenshots, dict(resolution=10), cl_obj, fps)
        #
        # project.store_project(HeadlessUserSettings())
        # mw.load_screenshots()
        t = project.name.split(".")[0].split("_")
        project.movie_descriptor.movie_name = t[3]
        project.movie_descriptor.movie_id = "_".join(t[:3])
        print(project.movie_descriptor.movie_id)
        project.store_project(HeadlessUserSettings())

        to_webapp(project, "gaudenz.halter@uzh.ch", "Graz@VMML", "http://127.0.0.1:5000/api/")
    except:
        continue

