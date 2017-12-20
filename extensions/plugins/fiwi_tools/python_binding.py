"""
Gaudenz Halter
VMML University of Zurich, FIWI University of Zurich

This binding provides easy access to the files located on the database server.
"""

import os
import glob
import pickle


class MovieAsset(object):
    def __init__(self, movie_path_abs, segm_path_abs, shot_paths_abs):
        self.movie_path_abs = movie_path_abs
        self.segm_path_abs = segm_path_abs
        self.shot_paths_abs = shot_paths_abs

    def get_segmentation_ms(self):
        """
        Loads the segment to a python list
        :return:    a list of lists, where each [index, start, stop], (int, long, long)
                    or None on Exception
        """
        try:
            segments = []
            counter = 1
            print_after = False
            with open(self.segm_path_abs, mode="rb") as f:
                for l in f:
                    l = l.decode()
                    segm_source = l.replace("\n", "")
                    segm_source = segm_source.split("\t")
                    if segm_source[0] == "Sequence_No":
                        continue
                    try:
                        segments.append([int(segm_source[0]), int(segm_source[1]), int(segm_source[2])])
                        counter += 1
                    except:
                        try:
                            print_after = True
                            segments.append([counter, int(segm_source[1]), int(segm_source[2])])
                            counter += 1
                        except:
                            print("Error in", segm_source, "\t", self.segm_path_abs)
                            return None

            if print_after:
                for s in segments:
                    print(s)
            return segments
        except IOError as e:
            print (e)
            return None


class Fetcher(object):
    def __init__(self, root_path, cache_path="fetcher_cache.pickle"):
        self.root_path = root_path.replace("\\", "/")
        self.movie_dir = self.root_path + "MOV/"
        self.segm_dir = self.root_path + "SEGM/"
        self.scr_dir = self.root_path + "SCR/"

        self.cache_path = cache_path

    def fetch(self, cache=True):
        """
        This function creates the MovieAsset objects. 
        Since it has to loop over all files within the database folder, it's result is cached by default, 
        such that the file-walk only has to be performed once. 


        :param cache: If the Result should be cached to Fetcher.cache_path
        :return: a list of MovieAssets
        """
        if os.path.isfile(self.cache_path):
            print ("LOADING FROM CACHE")
            with open(self.cache_path, "rb") as f:
                return pickle.load(f)

        shot_dirs = glob.glob(self.scr_dir + "*")

        movie_idxs = [d.replace("\\", "/").replace(self.scr_dir, "") for d in shot_dirs]

        movie_assets = []
        for idx in movie_idxs:
            try:
                movie_path = glob.glob(self.movie_dir + idx + "*")[0]
                segm_path = glob.glob(self.segm_dir + idx + "*")[0]
                shots_paths = glob.glob(self.scr_dir + idx + "/*")

                movie_assets.append(MovieAsset(movie_path, segm_path, shots_paths))
            except Exception as e:
                print (e, "Movie Path: ", movie_path, "Tried FIWI_ID: ", idx)

        if cache:
            with open(self.cache_path, "wb") as f:
                pickle.dump(movie_assets, f)

        return movie_assets


if __name__ == '__main__':
    # USAGE

    fetcher = Fetcher("\\\\130.60.131.134\\fiwi_datenbank\\".replace("\\", "/"))
    movie_assets = fetcher.fetch(cache=True)


    for movie in movie_assets:
        # print ("\n\n#############################################")
        # print ("Movie Path:".ljust(25), movie.movie_path_abs)
        # print ("Segmentation Path:".ljust(25), movie.segm_path_abs)
        # print ("Shot Paths:".ljust(25), movie.shot_paths_abs)

        # The Segmentation can be loaded from File
        # Each Segment consist of an ID, start and end Time.
        # Time is given in [ms]

        segmentation = movie.get_segmentation_ms()
        # print ("\nSEGMENTATION")
        # print ("index\tstart\tend\t")
        # for s in segmentation:
        #     print (str(s[0]) + "\t" + str(s[1]) + "\t" + str(s[2]))


