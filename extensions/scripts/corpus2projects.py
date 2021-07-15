# """
# Converts a pre HDF5 managed project to such a project.
# This change has been happening in the 0.7.0
# """
#
# import glob
#
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
#
# from core.corpus.legacy.sqlalchemy_entities import *
# from core.data.headless import *
#
#
# def fm_unique_keywords(path="resources/fm2gl.csv"):
#     res = dict()
#     with open(path, "r") as f:
#         reader = csv.reader(f, delimiter=";")
#         for i, r in enumerate(reader):
#             if i == 0:
#                 continue
#             if r != []:
#                 t = r[0].split(",")
#                 res[int(t[0])] = int(t[1])
#     return res
#
#
# def get_movie(ida = None, idb = None, idc = None, path = "E:\Programming\Git\ERC_FilmColors/resources\movie_table.csv"):
#     with open(path, "r") as f:
#         reader = csv.reader(f, delimiter=";")
#         result = []
#         for i, r in enumerate(reader):
#             if ida is None and idb is None and idc is None:
#                 result.append(r)
#                 continue
#             if int(r[0]) == int(ida) and (idb is None or int(idb) == int(r[1])) and (idc is None or int(idc) == int(r[2])):
#                 return r[3]
#
#     if ida is None and idb is None and idc is None:
#         return result
#     return None
#
# def create_meta_data(movie: DBMovie):
#     filmography_meta = dict()
#     filmography_meta['imdb_id'] = movie.imdb_id
#     filmography_meta['genre'] = ",".join([g.name for g in  movie.genres])
#     filmography_meta['color_process'] = movie.color_process
#     filmography_meta['director'] = movie.director
#     filmography_meta['cinematography'] = movie.cinematography
#     filmography_meta['color_consultant'] = movie.color_consultant
#     filmography_meta['production_design'] = movie.production_design
#     filmography_meta['art_director'] = movie.art_director
#     filmography_meta['costum_design'] = movie.costum_design
#     filmography_meta['production_company'] = movie.production_company
#     filmography_meta['country'] = movie.country
#     return filmography_meta
#
# if __name__ == '__main__':
#     db_path = "sqlite:///F:/_corpus/ERCFilmColors_02/database.db"
#     template_path = "E:\\Programming\\Git\\visual-movie-annotator\\data\\templates\\ERC_FilmColors.viant"
#     use_cache = True
#
#     engine = create_engine(db_path, echo=False)
#     Base.metadata.create_all(engine)
#     Session = sessionmaker(bind=engine)
#     db_session = Session()
#     hdf5_manager = HDF5Manager()
#     hdf5_manager.set_path("F:/_corpus/ERCFilmColors_02/analyses.hdf5")
#     mw = HeadlessMainWindow()
#     root = "F:/_projects/a02/"
#
#     c = 0
#     n = len(db_session.query(DBProject).all())
#
#     to_export = [16, 69, 184, 216, 229, 238, 256, 852, 3460, 3400]
#     for p in db_session.query(DBProject).all(): #type:DBProject
#         if p.corpus_id not in to_export:
#             continue
#         c += 1
#         name = "_".join([str(p.corpus_id),str(p.manifestation_id),str(p.copy_id), p.movie.name])
#         name = name.replace(":", "").replace("?", "")
#         dir_name = root + "/" +name + "/"
#         file_name = root + "/" +name + "/" + name + ".eext"
#         movie_path = get_movie(int(p.corpus_id), int(p.manifestation_id), int(p.copy_id))
#         if len(glob.glob(dir_name + "/*")) > 0:
#             continue
#         print(c, "/", n, file_name)
#         if movie_path is None:
#             print("No movie found")
#             continue
#
#         cap = cv2.VideoCapture(movie_path)
#         fps = cap.get(cv2.CAP_PROP_FPS)
#         project = create_project_headless(name + ".eext", location=dir_name, movie_path = movie_path, template_path=template_path)
#         project.movie_descriptor.meta_data['ERC_FilmColorsFilmography'] = create_meta_data(p.movie)
#         project.movie_descriptor.movie_id = "".join([str(p.corpus_id),str(p.manifestation_id),str(p.copy_id)])
#
#         keyword_idx = dict()
#         experiment = project.experiments[0] #type: Experiment
#         cl_obj_fg = experiment.get_classification_object_by_name("Foreground")
#         cl_obj_bg = experiment.get_classification_object_by_name("Background")
#         cl_obj_glob = experiment.get_classification_object_by_name("Global")
#
#         cl_obj_index = { 1:cl_obj_glob,2:cl_obj_fg,7:cl_obj_bg }
#         for f in experiment.get_unique_keywords():
#             keyword_idx[int(f.external_id)] = f
#
#         main_seg = project.segmentation[0]
#         for s in p.segments: #type:DBSegment
#             segment = main_seg.create_segment2(s.start_ms, s.end_ms, body = s.body)
#             for ukw in s.unique_keywords:
#                 ukw_p = keyword_idx[int(ukw.id)]
#                 if segment is not None and ukw_p is not None:
#                     experiment.tag_container(segment, ukw_p)
#                 else:
#                     print("Missing:", ukw_p, segment, s.__dict__)
#
#         curr_id = 0
#         curr_segment = None
#         for scr in db_session.query(DBScreenshot).filter(DBScreenshot.project == p): #type:DBScreenshot
#             if curr_segment != scr.segment:
#                 curr_id += 1
#                 curr_segment = scr.segment
#             scr_p = project.create_screenshot_headless("_".join([str(scr.segment.movie_segm_id), str(curr_id)]), ms_to_frames(scr.time_ms, fps))
#
#             for mask in scr.masks: # type:DBMask
#                 try:
#                     m = cv2.imread("F:\_corpus\ERCFilmColors_02\masks\\" + mask.mask_path, cv2.IMREAD_GRAYSCALE)
#                     analysis = SemanticSegmentationAnalysisContainer(
#                         name="Fg/Bg Segmentation",
#                         results=m.astype(np.uint8),
#                         analysis_job_class=SemanticSegmentationAnalysis,
#                         parameters=dict(model=DATASET_NAME_ADE20K, resolution=50),
#                         container=scr_p,
#                         dataset = "ADE20K"
#                     )
#                     project.add_analysis(analysis)
#                 except Exception as e:
#                     print(e)
#
#             for analysis in scr.analyses: #type: DBScreenshotAnalysis
#                 try:
#                     if analysis.analysis_class_name == "ColorFeatures":
#                         d = hdf5_manager.h5_file['features'][analysis.hdf5_index]
#                         a = IAnalysisJobAnalysis(
#                             name="Features:" + str(analysis.classification_object.name),
#                             results=dict(color_lab=d[0:3],
#                                          color_bgr=d[3:6],
#                                          saturation_l=d[6],
#                                          saturation_p=d[7]
#                                          ),
#                             analysis_job_class=ColorFeatureAnalysis,
#                             parameters=dict(),
#                             container=scr_p,
#                             target_classification_object= cl_obj_index[analysis.classification_obj_id]
#                         )
#                         project.add_analysis(a)
#
#                     elif analysis.analysis_class_name == "ColorPalette":
#                         d = hdf5_manager.h5_file['palettes'][analysis.hdf5_index]
#                         a = IAnalysisJobAnalysis(
#                             name="Palette:" + str(analysis.classification_object.name),
#                             results = ColorPaletteAnalysis().from_hdf5(d),
#                             analysis_job_class=ColorPaletteAnalysis,
#                             parameters=dict(),
#                             container=scr_p,
#                             target_classification_object=cl_obj_index[analysis.classification_obj_id]
#                         )
#                         project.add_analysis(a)
#                 except Exception as e:
#                     print(e)
#
#         project.store_project(project.path)
