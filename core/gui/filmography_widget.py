from PyQt5.QtWidgets import QCompleter, QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea


from core.gui.ewidgetbase import MultiItemTextInput, QLabel

class FilmographyWidget2(QWidget):
    def __init__(self, parent, project = None, persons = None, processes = None, genres = None, countries = None, companies=None):
        super(FilmographyWidget2, self).__init__(parent)
        self.setLayout(QVBoxLayout(self))

        self.area = QScrollArea(self)
        self.layout().addWidget(self.area)

        self.w = QWidget(self)
        self.area.setWidgetResizable(True)
        self.area.setWidget(self.w)
        self.w.setLayout(QVBoxLayout())
        
        self.lineEdit_IMDB = QLineEdit(self.w)
        lt = QHBoxLayout(self.w)
        self.w.layout().addItem(lt)

        lt.addWidget(QLabel("IMDB ID:", self.w))
        lt.addWidget(self.lineEdit_IMDB)

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
        self.w.layout().addWidget(self.lineEdit_ProductionCountry)

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

        # if project is not None:

    def get_filmography(self):
        filmography_meta = dict()
        filmography_meta['imdb_id'] = self.lineEdit_IMDB.text().split(",")
        filmography_meta['genre'] = self.lineEdit_Genre.get_items()
        filmography_meta['color_process'] = self.comboBox_ColorProcess.get_items()
        filmography_meta['director'] = self.lineEdit_Director.get_items()
        filmography_meta['cinematography'] = self.lineEdit_Cinematography.get_items()
        filmography_meta['color_consultant'] = self.lineEdit_ColorConsultant.get_items()
        filmography_meta['production_design'] = self.lineEdit_ProductionDesign.get_items()
        filmography_meta['art_director'] = self.lineEdit_ArtDirector.get_items()
        filmography_meta['costum_design'] = self.lineEdit_CostumDesign.get_items()
        filmography_meta['production_company'] = self.lineEdit_ProductionCompany.get_items()
        filmography_meta['country'] = self.lineEdit_ProductionCountry.get_items()

        return filmography_meta