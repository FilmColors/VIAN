import glob
import json
import os
from collections import namedtuple

from core.data.enums import ScreenshotNamingConventionOptions as naming
from PyQt5.QtGui import QFont, QColor
Font = namedtuple('Font', ['font_family', 'font_size', 'font_color'])
Palette = namedtuple('Palette', ['palette_name', 'palette_colors'])


palette_sand = Palette(palette_name="Sand", palette_colors=[[203,212,194],[219,235,192],[195,178,153],[129,83,85],[82,50,73]])
palette_grass = Palette(palette_name="Grass", palette_colors=[[13,31,34],[38,64,39],[60,82,51],[111,115,47],[179,138,88]])
palette_difference = Palette(palette_name="Difference", palette_colors=[[34,36,32],[255,52,123],[251,255,39],[82,235,215],[255,255,255]])
palette_beach = Palette(palette_name="Ocean", palette_colors=[[3,63,99],[40,102,110],[124,151,133],[181,182,130],[254,220,151]])
palette_earth = Palette(palette_name="Earth", palette_colors=[[252,170,103],[176,65,62],[255,255,199],[84,134,135],[71,51,53]])
palette_gray = Palette(palette_name="Gray", palette_colors=[[0,0,0],[50,50,50],[100,100,100],[150,150,150],[200,200,200],[255,255,255]])

class UserSettings():
    def __init__(self, path = "settings.json"):

        self.PROJECT_FILE_EXTENSION = ".eext"
        self.SCREENSHOTS_EXPORT_NAMING_DEFAULT = [
            naming.Scene_ID.name,
            naming.Shot_ID_Segment.name,
            naming.Movie_ID.name,
            naming.Movie_Name.name,
            naming.Movie_Year.name,
            naming.Movie_Source.name,

        ]
        self.USER_NAME = ""#"User Name"
        self.CORPUS_IP = "127.0.0.1"
        self.COPRUS_PORT = 5006
        self.COPRUS_PW = "CorpusPassword"

        self.SHOW_WELCOME = True

        self.OPENCV_PER_FRAME = False

        self.SCREENSHOTS_EXPORT_NAMING = self.SCREENSHOTS_EXPORT_NAMING_DEFAULT
        self.SCREENSHOTS_STATIC_SAVE = False
        self.GRID_SIZE = 100
        # Theme
        self.THEME_PATH = "qt_ui/themes/qt_stylesheet_dark.css"

        # FILES
        self.AUTOSAVE = True
        self.AUTOSAVE_TIME = 5

        self.DIR_BASE = (os.path.abspath(".") + "/").replace("\\", "/")
        self.DIR_USERHOME = os.path.expanduser("~") + "/"
        self.DIR_USER = "user/"
        self.DIR_SCREENSHOTS = "shots/"
        self.DIR_PROJECT = self.DIR_USERHOME + "documents/VIAN/"
        self.store_path = self.DIR_PROJECT + path
        self.MASTERFILE_PATH = self.DIR_USER + "master_file.ems"
        self.DIR_TEMPLATES = self.DIR_PROJECT + "/templates/"

        self.UPDATE_SOURCE = ""#"\\\\130.60.131.134\\team\\Software\\VIAN\\OSX\\"

        if not os.path.isdir(self.DIR_PROJECT):
            os.mkdir(self.DIR_PROJECT)

        if not os.path.isdir(self.DIR_TEMPLATES):
            os.mkdir(self.DIR_TEMPLATES)


        # Annotation Viewer
        self.AUTO_COLLAPSE = True

        self.MAIN_FONT = Font(font_family="Lucida Console", font_color=(50,50,50,255), font_size=14)
        self.PALETTES = [palette_sand, palette_grass, palette_difference, palette_beach, palette_earth, palette_gray]


    def get_qt_color(self, color):
        font = QFont(color.font_family)
        font.setPixelSize(color.font_size)
        color = QColor(color.font_color[0], color.font_color[0], color.font_color[0], color.font_color[0])
        return font, color

    def main_font(self):
        return self.get_qt_color(self.MAIN_FONT)

    def store(self):
        dict = vars(self)
        try:
            with open(self.store_path, 'w') as f:
                json.dump(dict, f)
            print "Stored Settings to: ", self.store_path
        except Exception as e:
            print e.message


    def load(self):
        try:
            with open(self.store_path ,"r") as f:
                dict = json.load(f)
                for attr, value in dict.iteritems():
                    if not attr == "PALETTES" and not attr=="MAIN_FONT":
                        setattr(self, attr, value)
                print "Loaded Settings from: ", self.store_path
        except IOError as e:
            print "No Settings found", e.message

    def load_last(self):
        files = glob.glob(self.DIR_PROJECT)
        if len(files) > 0:
            files.sort(key=os.path.getmtime, reverse=True)
            self.store_path = files[0]
            self.load()


