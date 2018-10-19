"""
The UserSettings Class is used to Store Variables from VIAN. 
DockWidgets States, Options etc.

Everything is serialized to the settings.json file in the UserDirectory/VIAN.

"""

import glob
import json
import os
from collections import namedtuple

from core.data.enums import ScreenshotNamingConventionOptions as naming
from PyQt5.QtGui import QFont, QColor

from PyQt5.QtWidgets import QApplication

Font = namedtuple('Font', ['font_family', 'font_size', 'font_color'])
Palette = namedtuple('Palette', ['palette_name', 'palette_colors'])


palette_sand = Palette(palette_name="Sand", palette_colors=[[203,212,194],[219,235,192],[195,178,153],[129,83,85],[82,50,73]])
palette_grass = Palette(palette_name="Grass", palette_colors=[[13,31,34],[38,64,39],[60,82,51],[111,115,47],[179,138,88]])
palette_difference = Palette(palette_name="Difference", palette_colors=[[34,36,32],[255,52,123],[251,255,39],[82,235,215],[255,255,255]])
palette_beach = Palette(palette_name="Ocean", palette_colors=[[3,63,99],[40,102,110],[124,151,133],[181,182,130],[254,220,151]])
palette_earth = Palette(palette_name="Earth", palette_colors=[[252,170,103],[176,65,62],[255,255,199],[84,134,135],[71,51,53]])
palette_gray = Palette(palette_name="Gray", palette_colors=[[0,0,0],[50,50,50],[100,100,100],[150,150,150],[200,200,200],[255,255,255]])


class UserSettings():
    """
    The UserSettings File contains information that persists over projects,
    this includes setings in the QDockWidgets, Contributor information, Default settings etc.
    Settings are serialized into the Documents directory of the user.
    If it does not exist it will be created.

    """
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
        self.CONTRIBUTOR = None
        self.CORPUS_IP = "127.0.0.1"
        self.COPRUS_PORT = 5006
        self.COPRUS_PW = "CorpusPassword"

        self.EARLY_STOP = 1000
        self.SHOW_WELCOME = True

        self.OPENCV_PER_FRAME = 0

        self.SCREENSHOTS_EXPORT_NAMING = self.SCREENSHOTS_EXPORT_NAMING_DEFAULT
        self.SCREENSHOTS_STATIC_SAVE = False

        # Timeline Grid
        self.USE_GRID = True
        self.GRID_SIZE = 100
        # Theme
        self.THEME_PATH = "qt_ui/themes/qt_stylesheet_dark.css"

        # FILES
        self.AUTOSAVE = True
        self.AUTOSAVE_TIME = 5

        self.DIR_BASE = (os.path.abspath(".") + "/").replace("\\", "/")
        self.DIR_USERHOME = os.path.expanduser("~") + "/"
        self.DIR_APPDATA = "data/"
        self.DIR_SCREENSHOTS = "shots/"
        self.DIR_PROJECT = self.DIR_USERHOME + "documents/VIAN/"
        self.DIR_PLUGINS = self.DIR_PROJECT + "/plugins/"
        self.store_path = self.DIR_PROJECT + path
        self.MASTERFILE_PATH = self.DIR_APPDATA + "master_file.ems"
        self.DIR_TEMPLATES = self.DIR_PROJECT + "/templates/"
        self.DIR_BACKUPS = self.DIR_PROJECT + "backups/"
        self.DIR_CORPORA = self.DIR_PROJECT + "/corpora/"

        self.UPDATE_SOURCE = ""#"\\\\130.60.131.134\\team\\Software\\VIAN\\OSX\\"

        if not os.path.isdir(self.DIR_PROJECT):
            os.mkdir(self.DIR_PROJECT)

        if not os.path.isdir(self.DIR_TEMPLATES):
            os.mkdir(self.DIR_TEMPLATES)

        self.AUTO_START_COLORMETRY = False

        # Annotation Viewer
        self.AUTO_COLLAPSE = True

        self.FONT_NAME = "Lucida Console"
        self.FONT_SIZE = 14
        self.MAIN_FONT = Font(font_family="Lucida Console", font_color=(50,50,50,255), font_size=14)
        self.PALETTES = [palette_sand, palette_grass, palette_difference, palette_beach, palette_earth, palette_gray]

        self.recent_files_name = []
        self.recent_files_path = []

        self.USE_CORPUS = False
        self.USE_ELAN = False

        self.dock_widgets_data = []

    def set_contributor(self, contributor):
        self.CONTRIBUTOR = contributor

    def get_qt_color(self, color):
        """
        Returns Font and Color
        :param color: 
        :return: 
        """
        font = QFont(color.font_family)
        font.setPixelSize(color.font_size)
        color = QColor(color.font_color[0], color.font_color[0], color.font_color[0], color.font_color[0])
        return font, color

    def main_font(self):
        """
        Returns the Main Font of the Settings
        :return: font, color 
        """
        return self.get_qt_color(self.MAIN_FONT)

    def generate_dir_paths(self):
        """
        Generates the default Directory Paths
        :return: 
        """
        self.DIR_BASE = (os.path.abspath(".") + "/").replace("\\", "/")
        self.DIR_USERHOME = os.path.expanduser("~") + "/"
        self.DIR_APPDATA = "data/"
        self.DIR_SCREENSHOTS = "shots/"
        self.DIR_PROJECT = self.DIR_USERHOME + "documents/VIAN/"
        self.DIR_PLUGINS = self.DIR_PROJECT + "/plugins/"
        self.DIR_BACKUPS = self.DIR_PROJECT + "backups/"
        self.store_path = self.DIR_PROJECT + "settings.json"
        self.MASTERFILE_PATH = self.DIR_APPDATA + "master_file.ems"
        self.DIR_TEMPLATES = self.DIR_PROJECT + "/templates/"
        self.DIR_CORPORA = self.DIR_PROJECT + "/corpora/"

        for d in [self.DIR_PROJECT, self.DIR_TEMPLATES, self.DIR_BACKUPS, self.DIR_PLUGINS, self.DIR_CORPORA]:
            if not os.path.isdir(d):
                os.mkdir(d)
                print(d + "\t Directory created.")

    def integritiy_check(self):
        """
        Check if the settings are possible, 
        else regenereate it.
        :return: 
        """

        integer = True
        for dir in [self.DIR_BASE, self.DIR_USERHOME, self.DIR_PROJECT, self.DIR_TEMPLATES, self.DIR_PLUGINS, self.DIR_CORPORA]:
            if not os.path.isdir(dir):
                self.generate_dir_paths()
                integer = False
                print("Recreated Missing Directories")
                break


        if not integer:
            print("Settings regenerated")
        else:
            print("Successfully Loaded Settings from: ", self.store_path)

    def add_to_recent_files(self, project):
        """
        Adds a project to the Recent Files
        :param project: a VIANProject object
        :return: 
        """
        path = project.path
        name = project.name

        if name not in self.recent_files_name:
            n_name = [name]
            n_name.extend(self.recent_files_name)
            self.recent_files_name = n_name

            n_path = [path]
            n_path.extend(self.recent_files_path)
            self.recent_files_path = n_path
        else:
            idx = self.recent_files_name.index(name)

            n_name = [self.recent_files_name.pop(idx)]
            n_name.extend(self.recent_files_name)
            self.recent_files_name = n_name

            #Update the File Path
            self.recent_files_path.pop(idx)
            n_path = [path]
            n_path.extend(self.recent_files_path)
            self.recent_files_path = n_path

    def remove_from_recent_files(self, file):
        """
        Removes a specific file from the recent list
        :param file: The FilePath to be removed
        :return: 
        """
        idx = self.recent_files_path.index(file)
        self.recent_files_name.pop(idx)
        self.recent_files_path.pop(idx)

    def store(self, dock_widgets):
        """
        Saves all current settings and the settings of the EDockWidgets
        :param dock_widgets: 
        :return: 
        """
        self.dock_widgets_data = []
        for w in dock_widgets:
            data = dict(
                class_name=w.__class__.__name__,
                settings = w.get_settings()
            )
            self.dock_widgets_data.append(data)

        ddict = vars(self)
        if ddict["CONTRIBUTOR"] is not None:
            ddict['CONTRIBUTOR'] = ddict["CONTRIBUTOR"].serialize()
        try:
            with open(self.store_path, 'w') as f:
                json.dump(ddict, f)
        except Exception as e:
            print(e)

    def load(self):
        """
        Loads the Settings from the UserDir, and checks if the necessary folders exist
        in the User/VIAN Directory
        :return: 
        """
        try:
            with open(self.store_path ,"r") as f:
                data = json.load(f)
                for attr, value in data.items():

                    # Palettes and MAIN_FONT should not be taken into Account,
                    # CONTRIBUTOR needs special treatment
                    if not attr == "PALETTES" and not attr =="MAIN_FONT" and not attr == "CONTRIBUTOR":
                        setattr(self, attr, value)

                    # If this attribute is the contributor deserialize it and apply it to the settings
                    elif attr == "CONTRIBUTOR":
                        if value is not None:
                            self.CONTRIBUTOR = Contributor().deserialize(value)

        except IOError as e:
            print("No Settings found", e)

        self.integritiy_check()

    def clean_up_recent(self):
        # Check if recent files exist:
        new_paths = []
        new_names = []
        for i, q in enumerate(self.recent_files_path):
            if os.path.isfile(q):
                new_names.append(self.recent_files_name[i])
                new_paths.append(self.recent_files_path[i])
        self.recent_files_name = new_names
        self.recent_files_path = new_paths

    def apply_dock_widgets_settings(self, dock_widgets):
        """
        Applies the Settings of the EDockWidgets to them
        
        :param dock_widgets: A list of EDockWidgets
        :return: None
        """
        for sett in self.dock_widgets_data:
            try:
                for w in dock_widgets:
                    if w.__class__.__name__ == sett['class_name']:
                        w.apply_settings(sett['settings'])
                        break
            except Exception as e:
                print(e)
                pass


class Contributor():
    """
    This class contains the user information currently using VIAN.
    It is used to sign a created project and is stored in the VIANProject History
    """
    def __init__(self, full_name = "", user_name = "", email = "", password = "", image_path = "", affiliation = ""):
        self.full_name = full_name
        self.user_name = user_name
        self.email = email
        self.password = password
        self.image_path = ""
        self.affiliation = affiliation

        #TODO @SILAS, This is the entity that represents the user of VIAN, add additional fields here, they get serialized automatically

    def serialize(self):
        return self.__dict__

    def deserialize(self, serialization):
        for attr, value in serialization.items():
                setattr(self, attr, value)
        return self