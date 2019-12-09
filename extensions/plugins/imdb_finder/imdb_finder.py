from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import os
import csv
from core.data.plugin import *
from imdb import IMDb
import requests
from core.concurrent.worker import MinimalThreadWorker
from core.data.computation import open_web_browser
from collections import namedtuple

class MovieTuple():
    def __init__(self, FilemakerID, MovieName, IMDb_ID, Status):
        self.FilemakerID = FilemakerID
        self.MovieName = MovieName
        self.IMDb_ID = IMDb_ID
        self.Status = Status


class FiwiVisualizerExtension(GAPlugin):
    def __init__(self, main_window):
        super(FiwiVisualizerExtension, self).__init__(main_window)
        self.plugin_name = "IMDB Finder"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = IMDBFinder(parent, self)
        wnd.show()


class IMDBFinder(QMainWindow):
    def __init__(self, parent, extension):
        super(IMDBFinder, self).__init__(parent)
        self.extension = extension
        path = os.path.abspath("extensions/plugins/imdb_finder/imdb_finder.ui")
        uic.loadUi(path, self)

        self.progress_bar = QProgressBar(self)
        self.statusBar().addWidget(self.progress_bar)
        self.thread_pool = QThreadPool()
        self.items = []

        self.movie_list = []
        self.cache = []
        self.btn_Find.clicked.connect(self.find_movies)

        self.current_idx = 0

        self.actionImport_List.triggered.connect(self.import_list)
        self.actionExport_List.triggered.connect(self.export_list)
        self.tableWidget_AllMovies.itemSelectionChanged.connect(self.load_cache)

        self.actionHelp.triggered.connect(self.on_help)

    def find_movies(self, movie_list):
        name = self.lineEdit_Name.text()
        db = IMDb()
        result = db.search_movie(name)

        for itm in self.items:
            itm.close()
        self.items = []

    # self.scrollArea = QScrollArea
        self.scrollArea.setWidgetResizable(True)

        for i, r in enumerate(result):
            movieobj = db.get_movie(r.movieID)
            itm = IMDBBEntry(self, movieobj, r.movieID)
            itm.onMovieClicked.connect(self.apply_selected)
            self.scrollArea.widget().layout().addWidget(itm)
            self.items.append(itm)

            if i > 2:
                break

    def find_all_movies(self, movie_list):
        lst = []
        for m in movie_list:
            lst.append(m.MovieName)

        self.progress_bar.setValue(0.0)
        worker = ConcurrentQuery(lst, None)
        worker.signals.callback.connect(self.cache_movie)
        self.thread_pool.start(worker)

    def load_cache(self):
        index = -1
        for idx in self.tableWidget_AllMovies.selectedIndexes():
            index = idx.row()

        self.current_idx = index

        if index >= 0:
            try:
                for itm in self.items:
                    itm.close()
                self.items = []

                for movie in self.cache[index]:
                    itm = IMDBBEntry(self, movie[1], movie[0])
                    itm.onMovieClicked.connect(self.apply_selected)
                    self.scrollArea.widget().layout().addWidget(itm)
                    self.items.append(itm)

            except Exception as e:
                print(e)
                print("Movie not yet Loaded, please wait until it is retrieved from IMDb.")
                pass


        pass

    def cache_movie(self, movie):
        self.cache.append(movie)
        self.movie_list[len(self.cache) - 1].Status = "Ready"
        self.progress_bar.setValue(int(len(self.cache) / len(self.movie_list) * 100))
        self.update_movie_list()

    def import_list(self):
        try:
            path = QFileDialog.getOpenFileName(filter="*.csv *.txt")[0]

            with open(path, "r") as f:
                reader = csv.reader(f, delimiter=";")
                counter = 0

                for r in reader:
                    print(r)
                    if counter == 0:
                        idx_fmID = r.index("FilemakerID")
                        idx_name = r.index("MovieName")

                    else:
                        movie = MovieTuple(r[idx_fmID], r[idx_name], -1, "Not Ready")
                        self.movie_list.append(movie)
                    counter += 1
            self.update_movie_list()

            self.find_all_movies(self.movie_list)
        except Exception as e:
            print(e)
            print("Please make sure that there is a Columns \"FilemakerID\" and a Column \"MovieName\"")

    def update_movie_list(self):
        to_select = self.tableWidget_AllMovies.currentIndex()
        # self.tableWidget_AllMovies = QTableWidget()
        self.tableWidget_AllMovies.clear()
        self.tableWidget_AllMovies.setSelectionBehavior(self.tableWidget_AllMovies.SelectRows)
        self.tableWidget_AllMovies.setColumnCount(4)
        self.tableWidget_AllMovies.setRowCount(0)
        self.tableWidget_AllMovies.setHorizontalHeaderLabels(["FilemakerID", "MovieName", "IMDB-ID", "Status"])

        for i, m in enumerate(self.movie_list):
            self.tableWidget_AllMovies.insertRow(self.tableWidget_AllMovies.rowCount())
            self.tableWidget_AllMovies.setItem(i, 0, QTableWidgetItem(m.FilemakerID))
            self.tableWidget_AllMovies.setItem(i, 1, QTableWidgetItem(m.MovieName))
            self.tableWidget_AllMovies.setItem(i, 2, QTableWidgetItem(m.imdb))
            self.tableWidget_AllMovies.setItem(i, 3, QTableWidgetItem(m.Status))

        try:
            self.tableWidget_AllMovies.setCurrentIndex(to_select)
        except:
            pass

    def export_list(self):
        try:
            path = QFileDialog.getSaveFileName(filter="*.csv *.txt")[0]
            with open(path, "w", newline='') as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow(["FilemakerID", "MovieName", "IMDb-ID"])
                for m in self.movie_list:
                    writer.writerow([m.FilemakerID, m.MovieName, m.IMDb_ID])
        except Exception as e:
            print(e)


    @pyqtSlot(str)
    def apply_selected(self, IMDB_ID):
        print("Recieved")
        try:
            self.movie_list[self.current_idx].IMDb_ID = IMDB_ID
            self.movie_list[self.current_idx].Status = "Complete"
            self.update_movie_list()
        except Exception as e:
            print(e)

    def on_help(self):
        open_web_browser("https://www.vian.app/static/manual/plugins/imdb_finder/imdb_finder.html")


class IMDBBEntry(QWidget):
    onMovieClicked = pyqtSignal(str)

    def __init__(self, parent, movie, movie_id):
        super(IMDBBEntry, self).__init__(parent)
        path = os.path.abspath("extensions/plugins/imdb_finder/imdb_entry.ui")
        uic.loadUi(path, self)
        self.movie_obj = movie
        self.movie_id = movie_id
        self.hovered = False
        self.setStyleSheet("QWidget{background: transparent;}")

        try:
            self.title = movie['title']
            self.lbl_Title.setText(self.title)
        except Exception as e:
            print(e)
        try:
            self.year = movie['year']
            self.lbl_Year.setText(str(self.year))
        except Exception as e:
            print(e)

        try:
            self.genres = movie['genres']
            self.lbl_Genre.setText(str(self.genres))
            self.lbl_Cast.setText(str(self.movie_id))
        except Exception as e:
            print(e)

        try:
            url = movie['cover url']
            data = requests.urlopen(url).read()
            image = QImage()
            image.loadFromData(data)
            self.lbl_img.setPixmap(QPixmap(image))

        except Exception as e:
            self.lbl_img.setPixmap(QPixmap("extensions/plugins/imdb_finder/icon_no_preview.png"))
            print(e)

        self.show()

    def enterEvent(self, a0: QEvent):
        self.hovered = True

    def leaveEvent(self, a0: QEvent):
        self.hovered = False

    def paintEvent(self, a0: QPaintEvent):
        if self.hovered:
            qp = QPainter()
            pen = QPen()

            qp.begin(self)
            pen.setColor(QColor(255, 160, 47, 100))
            qp.setPen(pen)
            qp.fillRect(self.rect(), QColor(255, 160, 47, 50))
            qp.drawRect(self.rect())

            qp.end()


    def mousePressEvent(self, a0: QMouseEvent):
        self.onMovieClicked.emit(self.movie_id)
        print("Pressed")


class ConcurrentQuery(MinimalThreadWorker):
    def __init__(self, movie_list, func):
        super(ConcurrentQuery, self).__init__(self.process)
        self.movie_list = movie_list

    @pyqtSlot()
    def process(self):
        for name in self.movie_list:
            print(name)
            try:
                db = IMDb()
                result = db.search_movie(name)
                movie_ids = []
                cache = []
                for i, r in enumerate(result):
                    movieobj = db.get_movie(r.movieID)
                    cache.append([r.movieID, movieobj])
                    movie_ids.append(r.movieID)

                    if i > 5:
                        break

                self.signals.callback.emit(cache)


            except Exception as e:
                self.error.emit(e)


if __name__ == '__main__':
    db = IMDb()
    m = db.get_movie("0075640")
    for k in m.__dict__.keys():
        print(k, m.__dict__[k])
    print(db.get_imdbID(m))
    # result = db.search_movie("Matrix")
    # for r in result:
    #     movieobj = db.get_movie(r.movieID)
    #     print(movieobj.keys())