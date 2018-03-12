import sqlite3
import csv
import dataset as ds
import numpy as np
import re
import os



TB_SEGM = "segments"
TB_STILL_FG = "Stills_FG"
TB_STILL_BG = "Stills_BG"
TB_STILL_GLOB = "Stills_GLOB"
TB_KEYWORDS = "keywords"
TB_MOVIES = "movies"


class DBMovie():
    def __init__(self, name, database_id, filemaker_id, year):
        self.name = name
        self.database_id = database_id
        self.fm_id = filemaker_id

        try:
            self.year = int(year)
        except:
            print(year)
            self.year = 0


    def __str__(self):
        return self.database_id + " " + self.name + " " + str(self.year)


class Corpus():
    def __init__(self, name):
        self.name = name
        self.movies = []

    def serialize(self):
        fm_ids = []
        for m in self.movies:
            fm_ids.append(m.fm_id)
        data = dict(
            name = self.name,
            fm_ids = fm_ids
        )
        return data

    def deserialize(self, serialization, all_movies):
        self.name = serialization['name']
        for fm_id in serialization['fm_ids']:
            for m in all_movies:
                if m.fm_id == fm_id:
                    self.movies.append(m)
                    break
        return self

    def add_movie(self, movie: DBMovie):
        if movie not in self.movies:
            self.movies.append(movie)

    def remove_movie(self, movie: DBMovie):
        if movie in self.movies:
            self.movies.remove(movie)

    def to_fm_ids(self):
        result = []
        for m in self.movies:
            result.append(m.fm_id)
        return result


class DBSegment():
    def __init__(self, fm_id, segm_id, t_start = 0, t_end = 100):
        self.fm_id = fm_id

        try:
            self.segm_id = int(segm_id)
            self.variation = "a"
        except:
            variation = " ".join(re.findall("[a-zA-Z]+", segm_id))
            self.segm_id = int(segm_id.strip(variation))
            self.variation = variation.lower()
        try:
            self.t_start = int(t_start)
            self.t_end = int(t_end)
        except:
            self.t_start = 0
            self.t_end = 0
        

class UniqueKeyword():
    def __init__(self, voc, word, class_name, gloss_id = 0):
        self.voc = voc
        self.word = word
        self.class_name = class_name
        self.ref_segments = []
        self.gloss_id = gloss_id

    def to_query(self):
        table_name = self.class_name + ":" + self.voc
        return table_name, self.word

    def to_string(self):
        return self.class_name + ":" + self.voc + ":" + self.word


class DBStill():
    def __init__(self, row, t_type):
        self.fm_id = row['FM_ID']
        self.segm_id = row['SEGM_ID']
        self.shot_id = row['SHOT_ID']
        self.variation = row['SEGM_VAR']
        self.col = [float(row['L']),float(row['A']),float(row['B'])]
        self.sat = float(row['S'])
        self.rel_path = row["SCR_PATH"]
        self.pixmap = None
        self.t_type = t_type


class FilmColorsDatabase():
    def __init__(self):
        self.path = None
        self.db = None

        self.segm_tables = []
        self.segm_tables_filters = []

    def connect(self, path):

        self.path = path
        self.db = ds.connect(path)

    def clear(self, name=None):
        if name is None:
            for t in self.db.tables:
                self.db[t].drop()
        else:
            if name == "segments":
                for t in self.db.tables:
                    if t not in [TB_KEYWORDS, TB_STILL_GLOB, TB_STILL_BG, TB_STILL_FG, TB_MOVIES]:
                        self.db[t].drop()
            else:
                self.db[name].drop()

    def import_segments_csv(self, csv_file, table_names):
        print("Importing: Segments")
        self.db.begin()
        try:
            with open(csv_file, "r") as f:
                reader = csv.reader(f, delimiter=";")
                keywords = []
                for i, row in enumerate(reader):
                    if i % 100 == 0:
                        print(i)
                    if i == 0:
                        table_mapping = table_names
                        table_mapping_idx = []
                        # print(table_mapping)
                        for z in range(len(table_names)):
                            table_mapping_idx.append([])
                        for j, r in enumerate(row):
                            for k, n in enumerate(table_mapping):
                                if n in r:
                                    table_mapping_idx[k].append(j)
                                    break
                        for k in row:
                            keywords.append(k.split(":").pop())

                        # Printing all Tables and their Columns
                        for q in range(len(table_mapping)):
                            if "Global:Lit" in table_mapping[q]:
                                print(table_mapping[q], np.array(keywords)[table_mapping_idx[q]].tolist())

                    else:
                        for j, map in enumerate(table_mapping_idx):
                            # if "Global:Lit" in table_mapping[j]:
                            #     print(kword)
                            kword = np.array(keywords)[map].tolist()
                            values = np.array(row)[map].tolist()
                            segm = dict(zip(kword, values))
                            self.db[table_mapping[j]].insert(segm)
            self.db.commit()
        except Exception as e:
            print(e)
            print(table_mapping[j])
            raise e
            self.db.rollback()

    def import_keywords_csv(self, csv_file):
        print("Importing: Keywords")
        table = self.db[TB_KEYWORDS]
        table.delete()
        self.db.begin()

        keywords_list = []
        try:
            with open(csv_file, "r") as f:
                reader = csv.reader(f, delimiter=";")
                for i, row in enumerate(reader):
                    print(row)
                    if i == 0:
                        keywords = row
                        idx_voc = row.index("voc")
                        idx_class = row.index("class")
                        idx_word = row.index("word")
                        idx_gloss = row.index("gloss_id")
                    else:
                        d = dict(zip(keywords, row))
                        table.insert(d)
                        keywords_list.append(
                            UniqueKeyword(row[idx_voc], row[idx_word], row[idx_class], row[idx_gloss]))

            self.db.commit()

            # Creating a Table for each Vocabulary-Class Tuple
            segm_table_names = []
            segm_table_words = []
            words = []

            for keyw in keywords_list:
                if keyw.class_name + ":" + keyw.voc not in segm_table_names:
                    segm_table_names.append(keyw.class_name + ":" + keyw.voc)
                    segm_table_words.append(words)
                    words = []
                    words.append(keyw.word)
                else:
                    words.append(keyw.word)

            for tpl in segm_table_names:
                self.db.create_table(tpl)
                self.segm_tables.append(tpl)

            self.segm_tables_filters = words

        except Exception as e:
            print(e)
            self.db.rollback()
            return None

        return keywords_list, segm_table_names, segm_table_words

    def import_stills_csv(self, csv_file, type=TB_STILL_GLOB):
        print("Importing Stills: " + type)
        table = self.db[type]
        self.db.begin()

        try:
            with open(csv_file, "r") as f:
                reader = csv.reader(f, delimiter=";")
                for i, row in enumerate(reader):
                    if i == 0:
                        keywords = row
                    else:
                        d = dict(zip(keywords, row))
                        table.insert(d)
            self.db.commit()
        except Exception as e:
            print(e)
            self.db.rollback()

    def import_movies_csv(self, csv_file):
        print("Importing Movies")
        table = self.db[TB_MOVIES]
        self.db.begin()
        try:
            with open(csv_file, "r") as f:
                reader = csv.reader(f, delimiter=";")
                for i, row in enumerate(reader):
                    if i == 0:
                        keywords = row
                    else:
                        d = dict(zip(keywords, row))
                        table.insert(d)
            self.db.commit()
        except Exception as e:
            print(e)
            self.db.rollback()

    def get_filters(self):
        # Creating a Table for each Vocabulary-Class Tuple
        segm_table_names = []
        segm_table_words = []
        words = []

        keywords = []
        for row in self.db[TB_KEYWORDS].all():
            keywords.append(UniqueKeyword(voc=row['voc'],
                                          word=row['word'],
                                          class_name=row['class'],
                                          gloss_id=row['gloss_id']
                                          )
                            )

        for keyw in keywords:
            if keyw.class_name + ":" + keyw.voc not in segm_table_names:
                segm_table_names.append(keyw.class_name + ":" + keyw.voc)
                segm_table_words.append(words)
                words = []
                words.append(keyw.word)
            else:
                words.append(keyw.word)

        return keywords, segm_table_names, segm_table_words

    def get_movies_objs(self):
        db_movies = self.db[TB_MOVIES].all()
        result = []
        for dm in db_movies:
            result.append(DBMovie(dm['Title'], dm['FileMaker ID'], dm['Item_ref_1_1'], dm['Year']))
        return result

    def get_segments(self, voc, filters):
        return self.db[voc].find(**filters)

    def get_keywords(self, filters):
        return self.db[TB_KEYWORDS].find(**filters)

    def get_stills(self, filters, type):
        return self.db[type].find(**filters)

    def get_stills_of_movie(self, movie:DBMovie):

        fg = [DBStill(rs, TB_STILL_FG) for rs in self.get_stills(dict(FM_ID=movie.fm_id), TB_STILL_FG)]
        bg = [DBStill(rs, TB_STILL_BG) for rs in self.get_stills(dict(FM_ID=movie.fm_id), TB_STILL_BG)]
        glob = [DBStill(rs, TB_STILL_GLOB) for rs in self.get_stills(dict(FM_ID=movie.fm_id), TB_STILL_GLOB)]

        return[fg, bg, glob]


    def get_tables(self):
        return self.db.tables

    def get_columns(self, table):
        return self.db[table].columns

    def get_stills_of_segment(self, voc, filters):
        pass


if __name__ == '__main__':
    database = FilmColorsDatabase()
    database.connect("sqlite:///../../results/filemaker_db.db")
    # database.clear("segments")
    # database.clear(TB_KEYWORDS)
    # database.clear()
    # keywords, tables, class_voc_words = database.import_keywords_csv("../../results/keywords.csv")
    # database.import_segments_csv("../../results/segments_absolut.csv", tables)

    # database.import_stills_csv("../../results/stills_bg.csv", TB_STILL_BG)
    # database.import_stills_csv("../../results/stills_fg.csv", TB_STILL_FG)
    # database.import_stills_csv("../../results/stills_glob.csv", TB_STILL_GLOB)

    #
    # res = database.get_stills(filters=dict(FM_ID = "1018_1_1",), type=TB_STILL_GLOB)
    # for r in res:
    #     print(1, r)
    print(database.get_columns("Global:Literal"))
    res = database.get_segments(voc = "Global:Literal", filters=dict(FileMaker_ID="1018_1_1"))

    for r in res:
        print(1, r)