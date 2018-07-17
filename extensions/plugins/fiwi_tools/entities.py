"""
All Assets that are produced during the Pipeline
"""
import os
import re

class MovieAsset(object):
    def __init__(self, movie_path_abs, segm_path_abs, shot_paths_abs):
        self.fm_id = os.path.split(segm_path_abs)[1].split(".")[0].split("_")[:3]
        self.movie_path_abs = movie_path_abs
        self.segm_path_abs = segm_path_abs
        self.shot_paths_abs = shot_paths_abs

        self.shot_assets = sorted([ScreenshotAsset(p) for p in self.shot_paths_abs], key=lambda x:(x.segm_id, x.segm_shot_id))
        self.palette_assets = [] # [sasset.segm_id, sasset.segm_shot_id, p_asset_fg, p_asset_bg, p_asset_glob]

        self.has_error = False
        self.error_stage = -1
        self.error_message = ""

    def get_shots_of_segm(self, idx):
        result = []
        for s in self.shot_assets:
            if s.segm_id == idx:
                result.append(s)
        return result

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

    def __str__(self):
        return str(self.fm_id[0]) + "_" + str(self.fm_id[1]) + "_" + str(self.fm_id[1])


class ScreenshotAsset(object):
    def __init__(self, filename):
        self.path = filename
        filename = filename.replace("\\", "/").split("/").pop().split(".")[0]
        filename = filename.split("_")
        self.frame_pos = None
        self.mask_file = None
        try:
            self.segm_id = int(filename[0])
            self.segm_shot_id = int(filename[1].strip(" ".join(re.findall("[a-zA-Z]+", filename[1]))))
            self.scr_grp = ""

        except:
            variation = " ".join(re.findall("[a-zA-Z]+", filename[0]))
            self.segm_id = int(filename[0].strip(variation))
            self.scr_grp = variation.lower()
            self.segm_shot_id = int(filename[1].strip(" ".join(re.findall("[a-zA-Z]+", filename[1]))))

        self.fg_file = ""
        self.bg_file = ""
        self.glob_file = ""

    def __str__(self):
        return str(self.segm_id) + "_" + str(self.segm_shot_id)


class PaletteAsset():
    def __init__(self, tree, merge_dists):
        self.tree = tree
        self.merge_dists = merge_dists