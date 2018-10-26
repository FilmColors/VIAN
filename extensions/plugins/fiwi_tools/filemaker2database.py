# from core.data.headless import *
# from sys import stdout as console
# from extensions.plugins.fiwi_tools.filemaker2projects import CorpusDBMapping, MasterDBMapping, load_stage, ScreenshotAsset, MovieAsset
# from core.corpus.shared.entities import *
#
#
# corpus_path = "F:/_input\\CorpusDB.csv"
# gloss_file = "F:/_input\\GlossaryDB_WordCount.csv"
# db_file = "F:/_input\\MasterDB_WordCount.csv"
# outfile = "../../results/counting.csv"
# asset_path = "F:\\fiwi_datenbank\\PIPELINE_RESULTS\\ASSETS\\"
# result_path = "F:/_output/"
# project_dir = "F:/_projects/"
# cache_dir = "F:/_cache/"
# template_path = "E:/Programming/Git/visual-movie-annotator/user/templates/ERC_FilmColors.viant"
#
#
# def filemaker_timestamp2ms(a):
#     a = a.zfill(8)
#     a = [a[i:i + 2] for i in range(0, len(a), 2)]
#     return ts_to_ms(a[0], a[1], a[2], a[3])
#
# def handle_error(fm_id, e):
#     pass
#
#
# def parse_glossary(glossary_path):
#     """
#     Parse the GlossaryDB CSV and create Unique Keywords from it.
#     :param glossary_path:
#     :return:
#     """
#     glossary_words, glossary_ids, glossary_categories, glossary_omit = [], [], [], []
#
#     with open(glossary_path, 'r') as input_file:
#         reader = csv.reader(input_file, delimiter=';')
#         counter = 0
#         for r in reader:
#             if counter == 0:
#                 print(r)
#                 idx_word = r.index("Term_EN")#TODO
#                 idx_id = r.index("Glossar ID")#TODO
#                 idx_column = r.index("exp Field")
#                 idx_omit = r.index("Disregard")
#             else:
#                 word = r[idx_word]
#                 word = word.strip()
#                 word = word.replace("’", "")
#                 word = word.replace("/", "")
#                 word = word.replace(" ", "_")
#                 word = word.replace("-", "_")
#                 glossary_words.append(word)
#                 glossary_ids.append(r[idx_id])
#                 glossary_categories.append(r[idx_column])
#
#                 if "yes" in r[idx_omit]:
#                     glossary_omit.append(True)
#                 else:
#                     glossary_omit.append(False)
#
#                 if "mind" in word:
#                     print(word)
#             counter += 1
#     return glossary_words, glossary_ids, glossary_categories, glossary_omit
#
#
# def parse_corpus(corpus_path):
#     """
#     Parse the CorpusDB CSV file an create the FilmographyData aswell as the mapping them to DBMovie and MovieAssets
#     :param corpus_path:
#     :param movie_assets:
#     :return:
#     """
#     filmography_result = []
#     movie_results = []
#     assignments = []
#
#     with open(corpus_path, 'r') as input_file:
#         reader = csv.reader(input_file, delimiter=';')
#         counter = 0
#         for r in reader:
#             try:
#                 if counter == 0:
#                     # Movie IDXs
#                     idx_filemaker_id = r.index(CorpusDBMapping['filemaker_id'])
#                     idx_country = r.index(CorpusDBMapping['country'])
#                     idx_title = r.index(CorpusDBMapping['title'])
#                     idx_year = r.index(CorpusDBMapping['year'])
#
#                     # Project IDXS
#                     idx_corpus_assignment = r.index(CorpusDBMapping['corpus_assignment'])
#                     idx_editors = r.index(CorpusDBMapping['editors'])
#
#                     #Filmography IDXs
#                     idx_imdb = r.index(CorpusDBMapping['imdb_id'])
#                     idx_color_process = r.index(CorpusDBMapping['color_process'])
#                     idx_director = r.index(CorpusDBMapping['director'])
#                     idx_genre = r.index(CorpusDBMapping['genre'])
#                     idx_cinematography = r.index(CorpusDBMapping['cinematography'])
#                     idx_color_consultant = r.index(CorpusDBMapping['color_consultant'])
#                     idx_production_design = r.index(CorpusDBMapping['production_design'])
#                     idx_art_director = r.index(CorpusDBMapping['art_director'])
#                     idx_costume_design = r.index(CorpusDBMapping['production_company'])
#                     idx_production_company = r.index(CorpusDBMapping['art_director'])
#
#                 else:
#                     row = r
#                     fm_id = row[idx_filemaker_id]
#
#                     dbmovie = DBMovie()
#                     dbmovie.movie_id = fm_id
#                     dbmovie.year = row[idx_year]
#                     dbmovie.movie_name = row[idx_title]
#
#                     fg = DBFilmographicalData()
#                     fg.imdb_id = row[idx_imdb]
#                     fg.color_process = row[idx_color_process]
#                     fg.director = row[idx_director]
#                     fg.genre = row[idx_genre]
#                     fg.cinematography = row[idx_cinematography]
#                     fg.color_consultant = row[idx_color_consultant]
#                     fg.production_design = row[idx_production_design]
#                     fg.art_director = row[idx_art_director]
#                     fg.costum_design = row[idx_costume_design]
#                     fg.country = row[idx_country]
#                     fg.production_company = row[idx_production_company]
#
#                     movie_results.append(dbmovie)
#                     filmography_result.append(fg)
#                     assignments.append((row[idx_corpus_assignment], row[idx_editors]))
#
#                 counter += 1
#             except Exception as e:
#                 handle_error(fm_id, e)
#     return (movie_results, filmography_result, assignments)
#
#
# def parse_masterdb(database_path, glossary_words, glossary_categories, glossary_ids, glossary_omit):
#     all_projects = [] # List of Tuples (<FM_ID>_<ITEM_ID>, [DB_SEGMENT, LIST[KeywordIDs]])
#     with open(database_path, 'r') as input_file:
#         reader = csv.reader(input_file, delimiter=';')
#         counter, idx_id, n_yes = 0, 0, 0
#         current_id, current_film, failed_words, failed_n, failed_column = [], [], [], [], []
#         for row in reader:
#             if counter == 0:
#                 idx_id = row.index("exp_ItemID")
#                 idx_start = row.index(MasterDBMapping['start'])
#                 idx_end = row.index(MasterDBMapping['end'])
#                 idx_annotation = row.index(MasterDBMapping['annotation'])
#                 idx_FMID = row.index("FileMaker ID")
#                 headers = row
#             else:
#                 # Print Progress
#                 if counter % 100 == 0:
#                     console.write("\r" + str(counter))
#
#                 # Get the Current FM-ID Item-ID
#                 new_id = row[idx_id].split("_")
#
#                 # If this id is not the same as the last
#                 # Store movie and create a new one
#                 if new_id != current_id:
#                     all_projects.append(current_film)
#                     current_id = new_id
#                     current_film = [current_id, []]
#
#                 # Create a new Segment
#                 dbsegment = DBSegment()
#                 dbsegment.segm_start = filemaker_timestamp2ms(row[idx_start])
#                 dbsegment.segm_end = filemaker_timestamp2ms(row[idx_end])
#                 dbsegment.segm_body = row[idx_annotation]
#                 dbkeywords = []
#
#                 # Iterate over all Columns and parse the keywords
#                 column_counter = 0
#                 for c in row:
#                     if column_counter in [idx_start, idx_end, idx_annotation, idx_id, idx_FMID]:
#                         continue
#
#                     ws = c.split("°")
#                     words = []
#                     for qw in ws:
#                         words.extend(qw.split("\n"))
#
#                     for w in words:
#                         success = False
#                         word = w.replace("\n", "")
#                         word = word.replace("’", "")
#                         word = word.replace("\'", "")
#                         word = word.replace("/", "")
#                         word = word.strip()
#                         word = word.replace(" ", "_")
#                         word = word.replace("-", "_")
#
#                         if word == "" or word == " ":
#                 try:
#                     # Create a new Segment
#                     dbsegment = DBSegment()
#                     dbsegment.segm_start = row[idx_start]
#                     dbsegment.segm_end = row[idx_end]
#                     dbsegment.segm_body = row[idx_annotation]
#                     dbkeywords = []
#
#                     # Iterate over all Columns and parse the keywords
#                     column_counter = 0
#                     for c in row:
#                         if column_counter in [idx_start, idx_end, idx_annotation, idx_id, idx_FMID]:
#
#                             continue
#
#                         ws = c.split("°")
#                         words = []
#                         for qw in ws:
#                             words.extend(qw.split("\n"))
#
#                         for w in words:
#                             success = False
#                             word = w.replace("\n", "")
#                             word = word.replace("’", "")
#                             word = word.replace("\'", "")
#                             word = word.replace("/", "")
#                             word = word.strip()
#                             word = word.replace(" ", "_")
#                             word = word.replace("-", "_")
#
#                             if word == "" or word == " ":
#                                 continue
#
#                             for idx, keyword in enumerate(glossary_words):
#                                 if keyword.lower() == word.lower() and headers[column_counter].lower() == glossary_categories[idx].lower():
#                                     if glossary_omit[idx] is False:
#                                         dbkeywords.append(glossary_ids[idx])
#                                         success = True
#                                     else:
#                                         print(idx, " omitted")
#                                     break
#
#                             if not success:
#                                 if word not in failed_words:
#                                     failed_words.append(word)
#                                     failed_column.append(headers[column_counter])
#                                     failed_n.append(1)
#                                     print("")
#                                     print("Failed \'" + word + "\'")
#                                 else:
#                                     failed_n[failed_words.index(word)] += 1
#                         column_counter += 1
#
#                     # Finally combine the dbsegment and keywords to a tuple and add them to the current film
#                     current_film[1].append((dbsegment, dbkeywords))
#                 except Exception as e:
#                     print(e)
#
#             counter += 1
#             #
#             # if counter == 300:
#             #     break
#     return all_projects
#
#
# def step_1_parse_filemaker(glossary_path, database_path, corpus_path, result_directory):
#     """
#     Generates VIAN Projects from Filemaker Data
#     :return:
#     """
#     # Only if no Cache exists
#     if not os.path.isfile(cache_dir + "pre_vian_projects.pickle"):
#         # Parse the Glossary
#         glossary_words, glossary_ids, glossary_categories, glossary_omit = parse_glossary(glossary_path)
#
#         # Parse the Corpus to get all Films from th eCorpus
#         (movie_results, filmography_result, assignments) = parse_corpus(corpus_path)
#
#         # Parse all Segments
#         all_projects = parse_masterdb(database_path, glossary_words, glossary_categories, glossary_ids, glossary_omit)
#
#
#         with open(cache_dir + "pre_vian_projects.pickle", "wb") as f:
#             data = dict(
#                 glossary_words = glossary_words,
#                 glossary_ids = glossary_ids,
#                 glossary_categories  =glossary_categories,
#                 glossary_omit = glossary_omit,
#                 movie_results = movie_results,
#                 filmography_result = filmography_result,
#                 assignments = assignments,
#                 all_projects =all_projects
#             )
#             pickle.dump(data,f)
#     else:
#         with open(cache_dir + "pre_vian_projects.pickle", "rb") as f:
#             d = pickle.load(f)
#             glossary_words = d['glossary_words']
#             glossary_ids = d['glossary_ids']
#             glossary_categories = d['glossary_categories']
#             glossary_omit = d['glossary_omit']
#             movie_results = d['movie_results']
#             filmography_result = d['filmography_result']
#             assignments = d['assignments']
#             all_projects = d['all_projects']
#
#     return (glossary_words, glossary_ids, glossary_categories, glossary_omit, movie_results, filmography_result, assignments, all_projects)
#
#
# def step_2_screenshots(all_projects, max_fails = 2):
#     """
#     Attaches Screenshots to VIAN Projects created in step 1
#     :return:
#     """
#     result = []
#     not_ok = []
#     movie_assets = load_stage(asset_path, 1)
#
#     for m in movie_assets:
#         r = []
#         n = []
#         c = 0
#         for scr in m.shot_assets:
#             try:
#                 r.append(int(scr.frame_pos))
#             except:
#                 c += 1
#                 n.append(scr.path)
#         if c <= max_fails:
#             result.append((m.fm_id, r))
#         else:
#             not_ok.append((m.fm_id, n))
#
#     result_2_dict = dict()
#     not_ok_2_dict = dict()
#
#     for r in result:
#         result_2_dict[str(r[0])] = r[1]
#     for r in not_ok:
#         not_ok_2_dict[str(r[0])] = r[1]
#
#     final_ok = []
#     final_not_ok = []
#     for p in all_projects:
#         if len(p) == 0:
#             continue
#         if str(p[0]) in result_2_dict:
#             final_ok.append((p, result_2_dict[str(p[0])]))
#             pass
#         elif str(p[0]) in not_ok_2_dict:
#             final_not_ok.append((p, not_ok_2_dict[str(p[0])]))
#             pass
#         else:
#             final_not_ok.append((p, None))
#
#     return (final_ok, final_not_ok)
#
#
# def step_3_masks(all_projects, movie_assets:List[MovieAsset]):
#     """
#     Attaches Masks to Screenshots Created in step 2
#     :return:
#     """
#
#     for m in movie_assets:
#     pass
#
#
# def step_4_palettes():
#     """
#     Attaches Palettes to mask analyses created in step 2
#     :return:
#     """
#
#
# def step_5_color_features():
#     """
#     Attaches Color Features to masks applied in step 2
#     :return:
#     """
#     pass
#
# if __name__ == '__main__':
#     total_ok = []
#     total_not_ok = [] # Tuple(ProjectInfo, MovieAsset)
#
#     (glossary_words, glossary_ids, glossary_categories, glossary_omit, movie_results, filmography_result, assignments,
#     all_projects) = step_1_parse_filemaker(gloss_file, db_file, corpus_path, "")
#
#     print("Step 2 - Screenshots")
#     (res_stage_2, not_ok_2) = step_2_screenshots(all_projects)
#     print("N-OK:", len(res_stage_2))
#     print("N-Not Ok", len(not_ok_2))
#     with open(cache_dir + "failed_step_2.pickle", "wb") as f:
#         pickle.dump(not_ok_2, f)
#     del not_ok_2
#
#
#
#
#
