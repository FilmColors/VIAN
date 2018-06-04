import dataset as ds
import json
from core.corpus.shared.entities import *
from core.data.computation import is_subdir
import glob
import shutil

TABLE_PROJECTS = "PROJECTS"
TABLE_MOVIES = "MOVIES"
TABLE_SEGMENTS = "SEGMENTS"
TABLE_SCREENSHOT_GRP = "SCREENSHOT_GROUPS"
TABLE_SCREENSHOTS = "SHOTS"
TABLE_ANNOTATION_LAYERS = "ANNOTATION_LAYERS"
TABLE_SEGMENTATIONS = "SEGMENTATIONS"
TABLE_ANNOTATIONS = "ANNOTATIONS"
TABLE_KEYWORDS = "KEYWORDS"
TABLE_VOCABULARIES = "VOCABULARIES"
TABLE_VOCABULARY_WORDS = "VOCABULARY_WORDS"
TABLE_CLASSIFICATION_OBJECTS = "CLASSIFICATION_OBJECTS"
TABLE_CONTRIBUTORS = "CONTRIBUTORS"
TABLE_KEYWORD_MAPPING_SEGMENTS = "KEYWORD_MAPPING_SEGMENTS"
TABLE_KEYWORD_MAPPING_SCREENSHOTS = "KEYWORD_MAPPING_SCREENSHOTS"
TABLE_KEYWORD_MAPPING_ANNOTATIONS = "KEYWORD_MAPPING_ANNOTATIONS"
TABLE_EXPERIMENTS = "EXPERIMENTS"
TABLE_SCEENSHOT_SEGMENTS_MAPPING = "SCREENSHOT_SEGM_MAPPING"
TABLE_SCEENSHOT_GROUPS_MAPPING = "SCREENSHOT_GROUPS_MAPPING"
TABLE_ANALYSES = "ANALYSES"


ALL_PROJECT_TABLES = [
    TABLE_SEGMENTS,
    TABLE_SEGMENTATIONS,
    TABLE_ANNOTATIONS,
    TABLE_ANNOTATION_LAYERS,
    TABLE_SCREENSHOT_GRP,
    TABLE_SCREENSHOTS,
    TABLE_SCEENSHOT_SEGMENTS_MAPPING,
    TABLE_SCEENSHOT_GROUPS_MAPPING,
    TABLE_KEYWORD_MAPPING_SEGMENTS,
    TABLE_KEYWORD_MAPPING_SCREENSHOTS,
    TABLE_KEYWORD_MAPPING_ANNOTATIONS
]

ALL_TABLES = [
    TABLE_PROJECTS,
    TABLE_MOVIES,
    TABLE_SEGMENTS,
    TABLE_SCREENSHOT_GRP,
    TABLE_SCREENSHOTS,
    TABLE_ANNOTATION_LAYERS,
    TABLE_SEGMENTATIONS,
    TABLE_ANNOTATIONS,
    TABLE_KEYWORDS,
    TABLE_VOCABULARIES,
    TABLE_CLASSIFICATION_OBJECTS,
    TABLE_CONTRIBUTORS,
    TABLE_KEYWORD_MAPPING_SEGMENTS,
    TABLE_KEYWORD_MAPPING_SCREENSHOTS,
    TABLE_KEYWORD_MAPPING_ANNOTATIONS,
    TABLE_EXPERIMENTS,
    TABLE_SCEENSHOT_SEGMENTS_MAPPING,
    TABLE_SCEENSHOT_GROUPS_MAPPING
]

class CorpusDB():
    def __init__(self):
        self.name = ""
        self.root_dir = ""
        self.file_path = ""

    def commit_project(self, project:VIANProject):
        """
        If the project does not yet exist in the Database it is created, 
        else, it is updated, and checked in.
        :param project: 
        :return: 
        """
        pass

    def checkout_project(self, project_id, contributor=DBContributor):
        pass

    def checkin_project(self, project_id, contributor: DBContributor):
        pass

    def get_project_path(self, dbproject: DBProject):
        pass

    def import_dataset(self, segment_db, glossary_db, master_db, clear = True):
        pass

    def initialize(self, name, root_dir):
        self.name = name
        self.root_dir = root_dir + "/" + name + "/"

        if not os.path.isdir(self.root_dir):
            os.mkdir(self.root_dir)

        self.create_file_system(self.root_dir)
        self.file_path = self.root_dir + "/" + self.name + ".vian_corpus"
        self.save(self.file_path)

    def create_file_system(self, root):
        os.mkdir(root + SCR_DIR)
        os.mkdir(root + MOVIE_DIR)
        os.mkdir(root + ANALYSIS_DIR)
        os.mkdir(root + PROJECTS_DIR)
        os.mkdir(root + EXPERIMENTS_DIR)

    def connect(self, path):
        pass

    def disconnect(self):
        pass

    def remove_project(self, dbproject: DBProject):
        pass

    def add_user(self, contributor: DBContributor):
        table = self.db[TABLE_CONTRIBUTORS]
        table.inser(contributor.to_database())

    #region Querying
    def get_projects(self, filters):
        pass

    def get_annotation_layers(self, filters):
        pass

    def get_segmentations(self, filters):
        pass

    def get_segments(self, filters):
        pass

    def get_screenshots(self, filters):
        pass

    def get_annotations(self, filters):
        pass

    def get_vocabularies(self):
        pass

    def get_analysis_results(self, filters):
        pass

    def get_keywords(self):
        pass

    def get_settings(self):
        pass

    # endregion Querying

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.__dict__, f)

    def load(self, path):
        with open(path, "r") as f:
            data = json.load(f)
            for attr, value in data.items():
                setattr(self, attr, value)

    def clear(self, tables = None):
        pass


class DatasetCorpusDB(CorpusDB):
    def __init__(self):
        super(DatasetCorpusDB, self).__init__()
        self.sql_path = ""
        self.db = None

        # Constrain means: A Segmentation can only be commited if there exists a Segmentation
        # with this name in the Database (No new Segmentations can be added)
        self.constrain_segmentations = False
        self.constrain_ann_layer = False
        self.constrain_class_objs = False
        self.constrain_screenshot_grps = False
        self.constrain_experiments = False
        self.constrain_vocabularies = False
        self.constrain_analyses = False

        self.default_annotation_layers = []
        self.default_segmentations = []
        self.default_screenshot_groups = []
        self.default_analyses = []
        self.default_experiments = []

        self.allow_project_download = True
        self.allow_movie_upload = False

    def connect(self, path):
        self.path = path
        self.db = ds.connect(path)

    def disconnect(self):
        pass

    def initialize(self, name, root_dir):
        CorpusDB.initialize(self, name, root_dir)
        self.sql_path = 'sqlite:///' + self.root_dir + "/" +self.name + ".vian_corpus_sql"

        print("\nCORPUS CREATED")
        print("  SQL:", self.sql_path)
        print(" ROOT:", self.root_dir)
        print(" FILE:", self.file_path)

        print()
        print("Attributes:")
        for attr, val in self.__dict__.items():
            print(attr, val)

        self.db = ds.connect(self.sql_path)
        self.db.begin()
        self.db["SETTINGS"].insert(dict(name=name, root_dir=root_dir, created=str(get_current_time())))

        for s in self.default_segmentations:
            self.db[TABLE_SEGMENTATIONS].insert(DBSegmentation(s).to_database(False))
        for l in self.default_annotation_layers:
            self.db[TABLE_ANNOTATION_LAYERS].insert(DBAnnotationLayer(l).to_database(False))

        self.db.commit()
        print("\n\n")
        self.save(self.file_path)

    def commit_project(self, project: VIANProject, contributor: DBContributor):
        """
        
        :param project: 
        :return: 
        """

        log = []
        project_obj = DBProject().from_project(project)
        table = self.db[TABLE_PROJECTS]

        #region Check if Project exists
        existing = False
        local_project = self.get_project(project_obj.project_id)
        if local_project is not None:
            existing = True
        #endregion

        # Is Project Checked Out by another User?
        if existing and local_project.is_checked_out:
            return False, "Project is checked out by another User"

        try:
            self.db.begin()
            #region Zip the Project
            #and store it in the projects directory
            archive_file = self.root_dir + PROJECTS_DIR + project.name
            project_obj = DBProject().from_project(project)
            shutil.make_archive(archive_file, 'zip', project.folder)
            project_obj.archive = archive_file + ".zip"
            #endregion
            classifiable_containers_db = []
            classifiable_containers_proj = []
            project_id = -1
            # Update the Project Entry, remove all associated container from the Database
            if existing:
                print("Project already exists... Cleaning")
                d = project_obj.to_database(include_id=True)
                table.update(d, ['id'])
                project_id = project_obj.project_id
                # Clear all Containers of this project from the Database
                for t in ALL_PROJECT_TABLES:
                    self.db[t].delete(project_id=project_obj.project_id)
            else:
                print("New Project Adding...")
                d = project_obj.to_database(include_id=False)
                table.insert(d)
                res = table.find_one(**project_obj.to_database(include_id=False))
                project.corpus_id = res['id']
                project_obj.project_id = res['id']
                project_id = res['id']

            #region Movie
            dbentry = DBMovie().from_project(project.movie_descriptor)
            dbmovies = self.get_movies(dict(movie_id_a = dbentry.movie_id[0],
                                            movie_id_b = dbentry.movie_id[1],
                                            movie_id_c = dbentry.movie_id[2]))
            if len(dbmovies) > 0:
                movie_id = dbmovies[0].movie_id_db
            else:
                movie_id = self.db[TABLE_MOVIES].insert(dbentry.to_database(False))

            #endregion

            #region Segmentation
            db_segmentations = [] # All DBSegments of the Main Segmentation
            for s in project.segmentation:
                segmentation_id = -1

                # Insert a Segmentation if allowed
                if self.constrain_segmentations:
                     dbsegms = self.get_segmentations(dict(name=s.get_name()))
                     if len(dbsegms) > 0:
                         segmentation_id = dbsegms[0].segmentation_id
                     else:
                         log.append("Segmentation skipped due to missing root segmentation: " + s.get_name())
                         continue
                else:
                    dbsegms = self.get_segmentations(dict(name=s.get_name()))
                    if len(dbsegms) > 0:
                        segmentation_id = dbsegms[0].segmentation_id
                    else:
                        segmentation_entry = DBSegmentation().from_project(s)
                        segmentation_id = self.db[TABLE_SEGMENTATIONS].insert(segmentation_entry.to_database(False))

                all_db_segments = []
                for segm in s.segments:
                    dbsegm = DBSegment().from_project(segm, project_id, movie_id, segmentation_id)
                    dbsegm.segment_id = self.db[TABLE_SEGMENTS].insert(dbsegm.to_database(False))
                    all_db_segments.append(dbsegm)

                    # We Will later need these two array to map the Classification Results
                    classifiable_containers_db.append(dbsegm)
                    classifiable_containers_proj.append(segm)

                db_segmentations.append(all_db_segments)


            #endregion

            # region Annotations
            for layer in project.annotation_layers:
                # Insert a AnnotationLayer if allowed
                if self.constrain_ann_layer:
                    db_ann_lay = self.get_annotation_layers(dict(name=layer.get_name()))
                    if len(db_ann_lay) > 0:
                        layer_id = db_ann_lay.layer_id
                    else:
                        log.append("Annotation Layer skipped due to missing root Annotation Layer: " + s.get_name())
                        continue
                else:
                    db_ann_lay = self.get_annotation_layers(dict(name=layer.get_name()))
                    if len(db_ann_lay) > 0:
                        layer_id = db_ann_lay[0].layer_id
                    else:
                        ann_layer_entry = DBAnnotationLayer().from_project(layer)
                        layer_id = self.db[TABLE_ANNOTATION_LAYERS].insert(ann_layer_entry.to_database(False))

                for ann in layer.annotations:
                    dbann = DBAnnotation().from_project(project_id, ann, movie_id, layer_id)
                    self.db[TABLE_ANNOTATIONS].insert(dbann.to_database(False))
                    # We Will later need these two array to map the Classification Results
                    classifiable_containers_db.append(dbann)
                    classifiable_containers_proj.append(ann)
            #endregion

            #region Screenshots
            all_db_scrs = []
            added_proj_scrs = []
            all_db_scr_mapped_groups = []
            all_db_scr_mapped_segments = []
            for scr_grp in project.screenshot_groups:
                if self.constrain_screenshot_grps:
                    db_scr_grp = self.get_screenshot_groups(dict(name=scr_grp.get_name()))
                    if len(db_scr_grp) > 0:
                        scr_grp_id = db_scr_grp[0].group_id
                    else:
                        log.append("Screenshot Group skipped due to missing root Screenshot Group: " + s.get_name())
                        continue
                else:
                    db_scr_grp = self.get_screenshot_groups(dict(name=scr_grp.get_name()))
                    if len(db_scr_grp) > 0:
                        scr_grp_id = db_scr_grp[0].group_id
                    else:
                        scr_group_entry = DBScreenshotGroup().from_project(scr_grp)
                        scr_grp_id = self.db[TABLE_SCREENSHOT_GRP].insert(scr_group_entry.to_database(False))

                for scr in scr_grp.screenshots:
                    # Make sure a Screenshot is only added once
                    if scr in added_proj_scrs:
                        all_db_scr_mapped_groups[added_proj_scrs.index(scr)].append(scr_grp_id)
                        continue
                    dbscr = DBScreenshot().from_project(scr, project_id, movie_id, scr_grp_id, self.root_dir)
                    dbscr.screenshot_id = self.db[TABLE_SCREENSHOTS].insert(dbscr.to_database(False))
                    all_db_scrs.append(dbscr)
                    added_proj_scrs.append(scr)
                    all_db_scr_mapped_groups.append([scr_grp_id])

                    # We Will later need these two array to map the Classification Results
                    classifiable_containers_db.append(dbscr)
                    classifiable_containers_proj.append(scr)

                    mapped_segments = []
                    for segments in db_segmentations:
                        for segm in segments:
                            if segm.segm_start <= dbscr.time_ms < segm.segm_end:
                                mapped_segments.append([segm.segment_id, segm.segmentation_id])
                                break

                    all_db_scr_mapped_segments.append(mapped_segments)

            for idx, dbscr in enumerate(all_db_scrs):
                for grp in all_db_scr_mapped_groups[idx]:
                    d = dict(
                        screenshot_id = dbscr.screenshot_id,
                        sceenshot_group_id = grp,
                        project_id=project_id
                    )
                    self.db[TABLE_SCEENSHOT_GROUPS_MAPPING].insert(d)

                for segm in all_db_scr_mapped_segments[idx]:
                    d = dict(
                        screenshot_id=dbscr.screenshot_id,
                        segment_id = segm[0],
                        segmentation_id = segm[1],
                        project_id = project_id
                    )
                    self.db[TABLE_SCEENSHOT_SEGMENTS_MAPPING].insert(d)



            #endregion

            #region Experiment
            for exp in project.experiments:
                if self.constrain_experiments:
                    db_exps = self.get_experiments(dict(name=exp.get_name()))
                    if len(db_exps) > 0:
                        exp_id = db_exps[0].experiment_id
                    else:
                        log.append("Experiment skipped due to missing root Experiment: " + s.get_name())
                        continue
                else:
                    db_exps = self.get_experiments(dict(name=exp.get_name()))
                    if len(db_scr_grp) > 0:
                        exp_id = db_scr_grp[0].group_id
                    else:
                        exp_entry = DBExperiment(self.root_dir).from_project(exp)
                        exp_id = self.db[TABLE_EXPERIMENTS].insert(exp_entry.to_database(False))

                all_vocs_db = []
                all_vocs_proj = []

                all_words_db = []
                all_words_proj = []
                for voc in exp.get_vocabularies():
                    if self.constrain_vocabularies:
                        db_vocs = self.get_vocabularies(dict(name=voc.get_name()))
                        # if the Vocabulary exists, we want to have a sorted list of all words,
                        # ordered in the same fashion as the words of the project
                        if len(db_vocs) > 0:
                            voc_id = db_vocs[0].vocabulary_id
                            all_vocs_db.append(db_vocs[0])
                            all_vocs_proj.append(voc)
                            all_words_unsorted = self.get_vocabulary_words(dict(vocabulary_id = voc_id))
                            for w in voc.get_vocabulary_as_list():
                                for wdb in all_words_unsorted:
                                    if w.name == wdb.name:
                                        all_words_db.append(wdb)
                                        all_words_proj.append(w)
                                        break
                        else:
                            log.append(
                                "Classification Object skipped due to missing root Classification Object: " + s.get_name())
                            continue
                    else:
                        db_vocs = self.get_vocabularies(dict(name=voc.get_name()))
                        if len(db_vocs) > 0:
                            voc_id = db_vocs[0].vocabulary_id
                            all_vocs_db.append(db_vocs[0])
                            all_vocs_proj.append(voc)
                            all_words_unsorted = self.get_vocabulary_words(dict(vocabulary_id = voc_id))
                            for w in voc.get_vocabulary_as_list():
                                for wdb in all_words_unsorted:
                                    if w.name == wdb.name:
                                        all_words_db.append(wdb)
                                        all_words_proj.append(w)
                                        break

                        else:
                            voc_entry = DBVocabulary().from_project(voc)
                            voc_entry.vocabulary_id = self.db[TABLE_VOCABULARIES].insert(voc_entry.to_database(False))
                            all_vocs_db.append(voc_entry)
                            all_vocs_proj.append(voc)

                            for w in voc.get_vocabulary_as_list():
                                word_entry = DBVocabularyWord().from_project(w, voc_entry.vocabulary_id)
                                word_entry.word_id = self.db[TABLE_VOCABULARY_WORDS].insert(word_entry.to_database(False))
                                all_words_proj.append(w)
                                all_words_db.append(word_entry)

                all_cl_objs_db = []
                all_cl_objs_proj = []
                all_unique_keywords_db = []
                all_unique_keywords_proj = []
                for cl_obj in exp.get_classification_objects_plain():
                    if self.constrain_class_objs:
                        db_clobjs = self.get_classification_objects(dict(name=cl_obj.get_name(), experiment_id=exp_id))
                        if len(db_clobjs) > 0:
                            cl_id = db_clobjs[0].experiment_id
                            all_cl_objs_db.append(db_clobjs[0])
                            all_cl_objs_proj.append(cl_obj)
                            unique_keywords_db_unsorted = self.get_keywords(dict(class_obj_id=cl_id, experiment_id=exp_id))
                            for keyw_proj in cl_obj.unique_keywords:
                                for keywdb in unique_keywords_db_unsorted:
                                    if keyw_proj.name == keywdb.name:
                                        all_unique_keywords_db.append(keywdb)
                                        all_unique_keywords_proj.append(keyw_proj)
                                        break


                        else:
                            log.append(
                                "Classification Object skipped due to missing root Classification Object: " + s.get_name())
                            continue
                    else:
                        db_clobjs = self.get_classification_objects(dict(name=cl_obj.get_name(), experiment_id=exp_id))
                        if len(db_clobjs) > 0:
                            cl_id = db_clobjs[0].experiment_id
                            all_cl_objs_db.append(db_clobjs[0])
                            all_cl_objs_proj.append(cl_obj)
                            unique_keywords_db_unsorted = self.get_keywords(dict(class_obj_id=cl_id, experiment_id=exp_id))
                            for keyw_proj in cl_obj.unique_keywords:
                                for keywdb in unique_keywords_db_unsorted:
                                    if keyw_proj.name == keywdb.name:
                                        all_unique_keywords_db.append(keywdb)
                                        all_unique_keywords_proj.append(keyw_proj)
                                        break
                        else:
                            cl_entry = DBClassificationObject().from_project(cl_obj, exp_id)
                            cl_entry.classification_object_id = self.db[TABLE_CLASSIFICATION_OBJECTS].insert(
                                cl_entry.to_database(False))
                            all_cl_objs_db.append(cl_entry)
                            all_cl_objs_proj.append(cl_obj)
                            for keyw_proj in cl_obj.unique_keywords:
                                voc_obj_db = None
                                # Find the corresponding DBVocabulary
                                for v in all_vocs_db:
                                    if v.name == keyw_proj.voc_obj.name:
                                        voc_obj_db = v
                                        break
                                if voc_obj_db is None:
                                    log.append("Vocabulary Object not found in all Vocabularies")
                                    continue

                                # Find the corresponding DBVocabulary
                                word_obj_db = None
                                for w in all_words_db:
                                    if w.name == keyw_proj.word_obj.name and w.vocabulary_id == voc_obj_db.vocabulary_id:
                                        word_obj_db = w
                                        break

                                if word_obj_db is not None and voc_obj_db is not None:
                                    keyword_entry = DBUniqueKeyword().from_project(keyw_proj, voc_obj_db.vocabulary_id,
                                                                                   word_obj_db.word_id,
                                                                                   cl_entry.classification_object_id)
                                    keyword_entry.unique_keyword_id = self.db[TABLE_KEYWORDS].insert(keyword_entry.to_database(False))
                                    all_unique_keywords_db.append(keyword_entry)
                                    all_unique_keywords_proj.append(keyw_proj)


                for res in exp.classification_results:
                    try:
                        container_proj = res[0]
                        keyword_proj = res[1]
                        container_db = classifiable_containers_db[classifiable_containers_proj.index(container_proj)]
                        keyword_db = all_unique_keywords_db[all_unique_keywords_proj.index(keyword_proj)]
                        if isinstance(container_db, DBSegment):
                            self.db[TABLE_KEYWORD_MAPPING_SEGMENTS].insert(dict
                                                                           (segment_id = container_db.segment_id,
                                                                            keyword_id = keyword_db.unique_keyword_id,
                                                                            project_id = project_id)
                                                                           )
                        elif isinstance(container_db, DBAnnotation):
                            self.db[TABLE_KEYWORD_MAPPING_ANNOTATIONS].insert(dict
                                                                           (annotation_id = container_db.annotation_id,
                                                                            keyword_id = keyword_db.unique_keyword_id,
                                                                            project_id = project_id)
                                                                           )
                        elif isinstance(container_db, DBScreenshot):
                            self.db[TABLE_KEYWORD_MAPPING_SEGMENTS].insert(dict
                                                                           (screenshot_id = container_db.screenshot_id,
                                                                            keyword_id = keyword_db.unique_keyword_id,
                                                                            project_id = project_id)
                                                                           )
                        else:
                            print(container_db, keyword_db)
                    except Exception as e:
                        print (e)
            #endregion

            #region Analysis
            for a in project.analysis:
                if self.constrain_analyses and a.get_name() not in self.default_analyses:
                    log.append("Analysis skipped due to missing root Analysis: " + s.get_name())
                    continue
                else:
                    db_analysis = DBAnalysis().from_project(a, project_id)
                    db_analysis.analysis_id = self.db[TABLE_ANALYSES].insert(db_analysis.to_database(False))


            #endregion
            self.db.commit()

            self.checkin_project(project.corpus_id, contributor)
            print(log)
            return True, project_obj
        except Exception as e:
            print("Exception in CorpusDB:commit_project(): ", str(e))
            self.db.rollback()
            return False, str(e)

    def checkout_project(self, project_id, contributor:DBContributor):
        project = self.get_project(project_id)

        # If the project is not checked out at all
        if not project.is_checked_out:
            project.is_checked_out = True
            project.checked_out_user = contributor.contributor_id
            self.db.begin()
            self.db[TABLE_PROJECTS].update(project.to_database(True), ['id'])
            self.db.commit()

            return True, project.archive
        else:
            # If the project is checked out by this user
            if project.checked_out_user == contributor.contributor_id:
                return True, project.archive
            # Else it is checked out by another user
            else:
                return False, None

    def checkin_project(self, project_id, contributor:DBContributor):
        user = self.get_users(dict(id=contributor.contributor_id))
        local_project = self.get_project(project_id)
        if len(user) > 0 and local_project is not None:
            if int(local_project.checked_out_user) == int(user[0].contributor_id):
                try:
                    self.db.begin()
                    local_project.is_checked_out = False
                    local_project.checked_out_user = -1
                    self.db[TABLE_PROJECTS].update(local_project.to_database(True), ['id'])
                    self.db.commit()
                    return True
                except Exception as e:
                    print("Exception in CorpusDB:checkin_project(): ", str(e))
                    self.db.rollback()
            else:
                print("User not regconized or not matching the Check Out User")
        return False

    def remove_project(self, dbproject: DBProject):
        local_project = self.get_project(dbproject.project_id)
        try:
            os.remove(local_project.archive)
        except Exception as e:
            print("Exception in CorpusDB:remove_project(): ", e)
        self.db[TABLE_PROJECTS].delete(id=dbproject.project_id)

    def import_dataset(self, segment_db, glossary_db, master_db, clear = True):
        pass

    def clear(self, tables = None):
        if tables is None:
            tables = ALL_TABLES
        try:
            self.db.begin()
            for t in tables:
                self.db[t].drop()
            self.db.commit()
        except Exception as e:
            print("Exception in CorpusDB:clear(): ", str(e))
            self.db.rollback()


    #region Users
    def add_user(self, contributor: DBContributor):
        try:
            self.db.begin()
            table = self.db[TABLE_CONTRIBUTORS]
            contributor.contributor_id = table.insert(contributor.to_database())
            self.db.commit()
        except Exception as e:
            print("Exception in CorpusDB:add_user(): ", str(e))
            self.db.rollback()

    def connect_user(self, contributor: DBContributor):
        users = self.get_users(dict(name=contributor.name, password=contributor.password))
        if len(users) == 0:
            self.add_user(contributor)
            return contributor
        else:
            return users[0]

    def remove_user(self, contributor:DBContributor):
        try:
            self.db.begin()
            self.db[TABLE_CONTRIBUTORS].delete(id=contributor.contributor_id)
            self.db.commit()
        except Exception as e:
            print("Exception in CorpusDB:remove_user(): ", str(e))
            self.db.rollback()

    def get_users(self, filters = None):
        if filters is None:
            query = self.db[TABLE_CONTRIBUTORS].find()
        else:
            query = self.db[TABLE_CONTRIBUTORS].find(**filters)

        result = []
        for q in query:
            result.append(DBContributor("", "").from_database(q))
        return result

    #endregion

    #region Query
    def get_project(self, project_id):
        project = self.db[TABLE_PROJECTS].find_one(id=project_id)
        if project is None:
            return None

        dbproject = DBProject().from_database(project)
        return dbproject

    def get_projects(self, filters = None):
        if filters is None:
            query = self.db[TABLE_PROJECTS].all()
        else:
            query = self.db[TABLE_PROJECTS].find(**filters)
        result = []
        for r in query:
            result.append(DBProject().from_database(r))
        return result

    def get_project_path(self, dbproject: DBProject):
        for r in self.get_projects(filters=dict(id=dbproject.project_id)):
            return r.archive
        return None

    def get_annotation_layers(self, filters = None):
        if filters is None:
            query = self.db[TABLE_ANNOTATION_LAYERS].all()
        else:
            query = self.db[TABLE_ANNOTATION_LAYERS].find(**filters)

        result = []
        for q in query:
            result.append(DBAnnotationLayer().from_database(q))
        return result

    def get_segmentations(self, filters = None):
        if filters is None:
            query = self.db[TABLE_SEGMENTATIONS].all()
        else:
            query = self.db[TABLE_SEGMENTATIONS].find(**filters)

        result = []
        for q in query:
            result.append(DBSegmentation().from_database(q))
        return result

    def get_segments(self, filters = None):
        if filters is None:
            query = self.db[TABLE_SEGMENTS].all()
        else:
            query = self.db[TABLE_SEGMENTS].find(**filters)

        result = []
        for q in query:
            result.append(DBSegment().from_database(q))
        return result

    def get_screenshots(self, filters = None):
        if filters is None:
            query = self.db[TABLE_SCREENSHOTS].all()
        else:
            query = self.db[TABLE_SCREENSHOTS].find(**filters)

        result = []
        for q in query:
            result.append(DBScreenshot().from_database(q))
        return result

    def get_screenshot_groups(self, filters = None):
        if filters is None:
            query = self.db[TABLE_SCREENSHOT_GRP].all()
        else:
            query = self.db[TABLE_SCREENSHOT_GRP].find(**filters)

        result = []
        for q in query:
            result.append(DBScreenshotGroup().from_database(q))
        return result

    def get_annotations(self, filters = None):
        if filters is None:
            query = self.db[TABLE_ANNOTATIONS].all()
        else:
            query = self.db[TABLE_ANNOTATIONS].find(**filters)

        result = []
        for q in query:
            result.append(DBAnnotation().from_database(q))
        return result

    def get_vocabularies(self, filters = None):
        if filters is None:
            query = self.db[TABLE_VOCABULARIES].all()
        else:
            query = self.db[TABLE_VOCABULARIES].find(**filters)

        result = []
        for q in query:
            result.append(DBVocabulary().from_database(q))
        return result

    def get_vocabulary_words(self, filters = None):
        if filters is None:
            query = self.db[TABLE_VOCABULARY_WORDS].all()
        else:
            query = self.db[TABLE_VOCABULARY_WORDS].find(**filters)

        result = []
        for q in query:
            result.append(DBVocabularyWord().from_database(q))
        return result

    def get_classification_objects(self, filters = None):
        if filters is None:
            query = self.db[TABLE_CLASSIFICATION_OBJECTS].all()
        else:
            query = self.db[TABLE_CLASSIFICATION_OBJECTS].find(**filters)

        result = []
        for q in query:
            result.append(DBClassificationObject().from_database(q))
        return result

    def get_experiments(self, filters = None):
        if filters is None:
            query = self.db[TABLE_EXPERIMENTS].all()
        else:
            query = self.db[TABLE_EXPERIMENTS].find(**filters)

        result = []
        for q in query:
            result.append(DBExperiment(self.root_dir).from_database(q))
        return result

    def get_analyses(self, filters = None):
        if filters is None:
            query = self.db[TABLE_ANALYSES].all()
        else:
            query = self.db[TABLE_ANALYSES].find(**filters)

        result = []
        for q in query:
            result.append(DBAnalysis().from_database(q))
        return result

    def get_settings(self):
        pass

    def get_keywords(self, filters = None):
        if filters is None:
            query = self.db[TABLE_KEYWORDS].all()
        else:
            query = self.db[TABLE_KEYWORDS].find(**filters)

        result = []
        for q in query:
            result.append(DBUniqueKeyword().from_database(q))
        return result

    def get_movies(self, filters = None):
        if filters is None:
            query = self.db[TABLE_MOVIES].all()
        else:
            query = self.db[TABLE_MOVIES].find(**filters)

        result = []
        for entry in query:
            result.append(DBMovie().from_database(entry))
        return result
    #endregion

    #region IO
    def save(self, path):
        with open(path, "w") as f:
            data = dict(
                name = self.name,
                file_path = self.file_path,
                root_dir = self.root_dir,
                sql_path = self.sql_path,
                constrain_segmentations = self.constrain_segmentations,
                constrain_ann_layer = self.constrain_ann_layer,
                constrain_class_objs = self.constrain_class_objs,
                constrain_screenshot_grps = self.constrain_screenshot_grps ,
                constrain_experiments = self.constrain_experiments,
                constrain_vocabularies = self.constrain_vocabularies,
                constrain_analyses = self.constrain_analyses,

                default_annotation_layers = self.default_annotation_layers,
                default_screenshot_groups = self.default_screenshot_groups,
                default_segmentations = self.default_segmentations,
            )
            json.dump(data, f)

    def load(self, path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                for attr, value in data.items():
                    setattr(self, attr, value)
            self.connect(self.sql_path)
        except Exception as e:

            print(e)
            return False
        return self
    #endregion

    def __str__(self):
        result = ""
        for t in ALL_TABLES:
            entries = self.db[t].find()
            for e in entries:
                result += str(e) + "\n"
        return result

