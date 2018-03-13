import csv
from core.data.containers import Vocabulary, VocabularyWord

class Converter():
    def __init__(self, input_path):
        self.path = input_path

    def convert(self):
        id_counter = 0
        with open(self.path, newline='') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=';', quotechar='|')

            rows = []
            for row in spamreader:
                rows.append(row)

            vocabulary_names = []
            vocabularies = []
            for r in rows:
                if r[1] not in vocabulary_names:
                    voc = Vocabulary(r[1])
                    voc.unique_id = id_counter
                    voc.category = r[0]
                    id_counter += 1
                    vocabularies.append(voc)
                    vocabulary_names.append(r[1])
                else:
                    for v in vocabularies:
                        if v.name == r[1]:
                            voc = v
                word = VocabularyWord(r[2], voc)
                word.unique_id = id_counter
                id_counter += 1
                voc.add_word(word)

            # for v in vocabularies:
            #     print(v.category.ljust(30), v.name)
            #     print([w.name for w in v.get_vocabulary_as_list()])
            #     print("")

            for v in vocabularies:
                path = "E:\\Programming\\Git\\visual-movie-annotator\\user\\vocabularies\\" + v.name.replace(" ", "").replace("/","").replace("\\", "") + ".txt"
                v.export_vocabulary(path)






if __name__ == '__main__':
    conv = Converter("C:\\Users\\Gaudenz Halter\\Desktop\\Glossary_FilmColors_Concepts.CSV")
    conv.convert()