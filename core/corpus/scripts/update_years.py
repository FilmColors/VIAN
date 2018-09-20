import dataset as ds
import csv
from core.corpus.shared.entities import *
from core.corpus.scripts.utils import *

if __name__ == '__main__':
    movie_results, filmography_result, assignments = parse_corpus("F:/_input/CorpusDB.csv")

    ds = ds.connect("sqlite:///F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus_sql")
    ds.begin()
    i = 0
    to_update = []
    try:
        for r in ds['MOVIES'].all():
            if r['id']>=33:
                t = r
                t['id'] = t["id"] + 1
                to_update.append(t)

        for r in to_update:
            ds['MOVIES'].update(r, ['id'])
        ds.commit()
    except Exception as e:
        ds.rollback()
        print("Oups", e)


