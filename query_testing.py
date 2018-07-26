from core.corpus.shared.entities import *
from core.corpus.client.corpus_interfaces import LocalCorpusInterface

def project_query():
    pquery = QueryRequestData("projects")
    print(c.submit_query(pquery))


CORPUS_PATH = "F:\\_corpus\\ERC_FilmColorsCorpus\\ERC_FilmColorsCorpus.vian_corpus"
if __name__ == '__main__':
    c = LocalCorpusInterface()
    user = DBContributor(name="Gaudenz", image_path="C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\user_img.jpg",
                         affiliation="Nahh")
    c.connect_user(user, CORPUS_PATH)
    project_query()


