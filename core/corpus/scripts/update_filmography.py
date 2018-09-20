import dataset as ds
import csv
from core.corpus.shared.entities import *
from core.corpus.scripts.utils import *
from sys import stdout as console
import glob

def inspect_filmography(filmography_result):
    attrs = dict()
    for f in filmography_result:
        for key, val in f.__dict__.items():
            if key not in attrs:
                attrs[key] = []
            if isinstance(val, list):
                for v in val:
                    attrs[key].append(v)

    for v, k in attrs.items():
        print(v, set(k))

    print("\n\n\n")
    print("Color Processes")
    for v in sorted(set(attrs['color_process'])):
        print(v)

    print("\n\n\n")
    print("Genres")
    for v in sorted(set(attrs['genre'])):
        print(v)

def insert_editors(assignment):

    db = ds.connect("sqlite:///F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus_sql")
    for r in db['CONTRIBUTORS'].all():
        print(r)

    all_movies_in_db = dict()
    for r in db['MOVIES'].all():
        all_movies_in_db[r['movie_id_a']] = dict(r)

    db.begin()
    db['CONTRIBUTOR_MAPPING'].drop()
    try:
        for r in assignments:
            if r[0] in all_movies_in_db:
                e = all_movies_in_db[r[0]]
                for t in r[2]:
                    print(e['id'], t)
                    db["CONTRIBUTOR_MAPPING"].insert(DBContributorMapping(e['id'], t[1]).to_database())
            else:
                print("Not in DB:", r[0])
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

def cleanup_screenshots(db_root = "F:\\_corpus\\ERC_FilmColorsCorpus"):
    db = ds.connect("sqlite:///F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus_sql")
    all_shots = dict()
    per_project_shots = dict() # nested dict[poject_id][time_ms][classificaftion_obj_id]
    for q in db["SHOTS"].all():
        all_shots[q['id']] = dict(q)
        if q['project_id'] not in per_project_shots:
            per_project_shots[q['project_id']] = dict()
        if not q['time_ms'] in per_project_shots[q['project_id']]:
            per_project_shots[q['project_id']][q['time_ms']] = dict()
        per_project_shots[q['project_id']][q['time_ms']][q['classification_object_id']] = q

    updated_analyses = []
    for r in db['ANALYSES'].find(analysis_name = "SemanticSegmentationAnalysis", classification_object_id = -1):
        old_shot = all_shots[r['target_container_id']]
        new_shot = per_project_shots[old_shot['project_id']][old_shot['time_ms']][1]
        updated_analyses.append(dict(id=r['id'], classification_object_id=1, target_container_id = new_shot['id']))

    db.begin()
    try:
        console.write("Updating Analyses...")
        c = 0
        for a in updated_analyses:
            if c % 100 == 0:
                console.write("\r" + str(round(c / len(updated_analyses) * 100,2)) + "%")
            c += 1
            db["ANALYSES"].update(a, ['id'])

        print("\nDone\n")
        console.write("Finding Shots...")
        to_remove = []
        t = db["SHOTS"].find(classification_object_id = -1)
        c = 0
        for r in t:
            if c % 1000 == 0:
                console.write("\r" + str(c) + "")
            c += 1
            to_remove.append(dict(r))

        console.write("Clearing Shots...")
        for s in to_remove:
            db["SCREENSHOT_SEGM_MAPPING"].delete(screenshot_id = s['id'])
        db["SHOTS"].delete(classification_object_id = -1)

        print("\nDone\n")
        console.write("Deleting Images")
        c = 0
        for t in to_remove:
            if c % 100 == 0:
                console.write("\r" + str(round(c / len(to_remove) * 100,2)) + "%")
            c += 1
            # print("Remove_IMG:", db_root + t['file_path'])
            if os.path.isfile(db_root + t['file_path']):
                os.remove(db_root + t['file_path'])

        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    # db["SHOTS"].find(classification_object_id = -1)
    # to_delete = []
    # for r in qres:
    #     to_delete.append(dict(r))
    #
    # for t in to_delete:
    #     print("Remove_IMG:", db_root + t['file_path'])





if __name__ == '__main__':
    movie_results, filmography_result, assignments = parse_corpus("F:/_input/CorpusDB_02.csv")
    cleanup_screenshots()
    # inspect_filmography(filmography_result)
    # insert_editors(assignments)

    # for f in glob.glob("F:\\_corpus\\ERC_FilmColorsCorpus\\screenshots\\*\\_glob.png*"):
    #     print(f)


    # ds = ds.connect("sqlite:///F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus_sql")
    # ds.begin()
    # i = 0
    # to_update = []
    # try:
    #     for r in ds['MOVIES'].all():
    #         if r['id']>=33:
    #             t = r
    #             t['id'] = t["id"] + 1
    #             to_update.append(t)
    #
    #     for r in to_update:
    #         ds['MOVIES'].update(r, ['id'])
    #     ds.commit()
    # except Exception as e:
    #     ds.rollback()
    #     print("Oups", e)
