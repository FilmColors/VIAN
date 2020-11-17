from PyQt5.QtWidgets import QCompleter, QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea
from PyQt5.QtCore import pyqtSignal

from core.gui.ewidgetbase import MultiItemTextInput, QLabel

# We query the database at startup once
_persons = None
_processes = None
_genres = None
_countries = None
_companies = None

def query_initial(corpus_client):
    global _persons
    global _processes
    global _genres
    global _countries
    global _companies

    try:
        _persons = corpus_client.get_persons()
        _processes = corpus_client.get_color_processes()
        _genres = corpus_client.get_genres()
        _countries = corpus_client.get_countries()
        _companies = corpus_client.get_companies()
    except Exception as e:
        print(e)



class FilmographyWidget2(QWidget):
    onFilmographyChanged = pyqtSignal()

    def __init__(self, parent, project = None, persons = None, processes = None, genres = None, countries = None, companies=None):
        super(FilmographyWidget2, self).__init__(parent)
        self.setLayout(QVBoxLayout(self))

        persons = _persons if persons is None else None
        processes = _processes if processes is None else None
        genres = _genres if genres is None else None
        countries = _countries if countries is None else None
        companies = _companies if companies is None else None

        self.area = QScrollArea(self)
        self.layout().addWidget(self.area)

        self.w = QWidget(self)
        self.area.setWidgetResizable(True)
        self.area.setWidget(self.w)
        self.w.setLayout(QVBoxLayout())
        
        self.lineEdit_IMDB = QLineEdit(self.w)
        self.lt = QHBoxLayout(self.w)

        self.lt.addWidget(QLabel("IMDB URL:", self.w))
        self.lt.addWidget(self.lineEdit_IMDB)

        self.w.layout().addItem(self.lt)

        self.lineEdit_Genre = MultiItemTextInput(self.w, "Genre")
        self.lineEdit_Director = MultiItemTextInput(self.w, "Director")
        self.lineEdit_Cinematography = MultiItemTextInput(self.w, "Cinematography")
        self.lineEdit_ColorConsultant = MultiItemTextInput(self.w, "Color Consultant")
        self.lineEdit_ProductionDesign = MultiItemTextInput(self.w, "Production Design")
        self.lineEdit_ArtDirector = MultiItemTextInput(self.w, "Art Director")
        self.lineEdit_CostumDesign = MultiItemTextInput(self.w, "Costume Design")

        self.lineEdit_ColorProcess = MultiItemTextInput(self.w, "Color Process")

        self.lineEdit_ProductionCompany = MultiItemTextInput(self.w, "Production Company")
        self.lineEdit_ProductionCountry = MultiItemTextInput(self.w, "Production Country")

        self.w.layout().addWidget(self.lineEdit_IMDB)
        self.w.layout().addWidget(self.lineEdit_Genre)
        self.w.layout().addWidget(self.lineEdit_Director)
        self.w.layout().addWidget(self.lineEdit_Cinematography)
        self.w.layout().addWidget(self.lineEdit_ColorConsultant)
        self.w.layout().addWidget(self.lineEdit_ProductionDesign)
        self.w.layout().addWidget(self.lineEdit_ArtDirector)
        self.w.layout().addWidget(self.lineEdit_CostumDesign)
        self.w.layout().addWidget(self.lineEdit_ColorProcess)
        self.w.layout().addWidget(self.lineEdit_ProductionCompany)
        self.w.layout().addWidget(self.lineEdit_ProductionCountry)

        self.lineEdit_Genre.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_Director.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_Cinematography.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_ColorConsultant.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_ProductionDesign.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_ArtDirector.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_CostumDesign.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_ColorProcess.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_ProductionCompany.onChanged.connect(self.onFilmographyChanged)
        self.lineEdit_ProductionCountry.onChanged.connect(self.onFilmographyChanged)

        if persons is not None:
            q = QCompleter([p['name'] for p in persons])
            self.lineEdit_Director.setCompleter(q)
            self.lineEdit_Cinematography.setCompleter(q)
            self.lineEdit_ColorConsultant.setCompleter(q)
            self.lineEdit_ProductionDesign.setCompleter(q)
            self.lineEdit_ArtDirector.setCompleter(q)
            self.lineEdit_CostumDesign.setCompleter(q)
        if processes is not None:
            q = QCompleter([p['name'] for p in processes])
            self.lineEdit_ColorProcess.setCompleter(q)

        if companies is not None:
            q = QCompleter([p['name'] for p in companies])
            self.lineEdit_ProductionCompany.setCompleter(q)

        if genres is not None:
            q = QCompleter([p['name'] for p in genres])
            self.lineEdit_Genre.setCompleter(q)

        if countries is not None:
            q = QCompleter([p['name'] for p in countries])
            self.lineEdit_ProductionCountry.setCompleter(q)

        if project is not None:
            self.set_filmography(project.movie_descriptor.meta_data)

    def get_filmography(self):
        filmography_meta = dict()
        try:
            imdb_url = self.lineEdit_IMDB.text()
            imdb_url = imdb_url.split("/")
            if imdb_url[-1:] == "":
                imdb_url = imdb_url[:-1]
            imdb_id = imdb_url[-1:]
            imdb_id = filter(lambda x: x.isdigit(), imdb_id)
        except Exception as e:
            imdb_id = ""
            print(e)
        filmography_meta['imdb_id'] = imdb_id
        filmography_meta['genre'] = self.lineEdit_Genre.get_items()
        filmography_meta['color_process'] = self.lineEdit_ColorProcess.get_items()
        filmography_meta['director'] = self.lineEdit_Director.get_items()
        filmography_meta['cinematography'] = self.lineEdit_Cinematography.get_items()
        filmography_meta['color_consultant'] = self.lineEdit_ColorConsultant.get_items()
        filmography_meta['production_design'] = self.lineEdit_ProductionDesign.get_items()
        filmography_meta['art_director'] = self.lineEdit_ArtDirector.get_items()
        filmography_meta['costum_design'] = self.lineEdit_CostumDesign.get_items()
        filmography_meta['production_company'] = self.lineEdit_ProductionCompany.get_items()
        filmography_meta['country'] = self.lineEdit_ProductionCountry.get_items()

        return filmography_meta

    def set_filmography(self, d):
        self.clear()

        if 'imdb_id' in d: self.lineEdit_IMDB.setText(", ".join(d['imdb_id']))
        if 'genre' in d: self.lineEdit_Genre.set_items(d['genre'])
        if 'color_process' in d: self.lineEdit_ColorProcess.set_items(d['color_process'])
        if 'director' in d: self.lineEdit_Director.set_items(d['director'])
        if 'cinematography' in d: self.lineEdit_Cinematography.set_items(d['cinematography'])
        if 'color_consultant' in d: self.lineEdit_ColorConsultant.set_items(d['color_consultant'])
        if 'production_design' in d: self.lineEdit_ProductionDesign.set_items(d['production_design'])
        if 'art_director' in d: self.lineEdit_ArtDirector.set_items(d['art_director'])
        if 'costum_design' in d: self.lineEdit_CostumDesign.set_items(d['costum_design'])
        if 'production_company' in d: self.lineEdit_ProductionCompany.set_items(d['production_company'])
        if 'country' in d: self.lineEdit_ProductionCountry.set_items(d['country'])

    def clear(self):
        self.lineEdit_Genre.clear()
        self.lineEdit_Director .clear()
        self.lineEdit_Cinematography.clear()
        self.lineEdit_ColorConsultant.clear()
        self.lineEdit_ProductionDesign.clear()
        self.lineEdit_ArtDirector.clear()
        self.lineEdit_CostumDesign.clear()
        self.lineEdit_ColorProcess.clear()
        self.lineEdit_ProductionCompany.clear()
        self.lineEdit_ProductionCountry.clear()