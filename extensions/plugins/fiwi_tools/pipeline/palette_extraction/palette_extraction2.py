"""
Author: Gaudenz Halter
University of Zurich
"""
from scipy.cluster.hierarchy import dendrogram
from scipy.spatial.distance import pdist
from matplotlib import pyplot as plt

from scipy.cluster.hierarchy import *
from pipeline.misc_utils import all_test_images
from fastcluster import linkage
from sklearn.cluster.hierarchical import AgglomerativeClustering
import numpy as np
import cv2
from typing import List
import pickle


class PaletteAsset():
    def __init__(self, tree, merge_dists):
        self.tree = tree
        self.merge_dists = merge_dists


class PaletteExtractorModel:
    def __init__(self, img, n_pixels = 100, num_levels = 4):
        self.model = cv2.ximgproc.createSuperpixelSEEDS(img.shape[1], img.shape[0], img.shape[2], n_pixels, num_levels=num_levels)

    def forward(self, img, n_pixels = 100):

        self.model.iterate(img)
        return self.model.getLabels()

    def labels_to_avg_color_mask(self, lab, labels):
        indices = np.unique(labels)
        for idx in indices:
            pixels = np.where(labels == idx)
            lab[pixels] = np.mean(lab[pixels], axis = 0)
        return lab

    def labels_to_palette(self, lab, labels):
        indices = np.unique(labels)
        bins = []
        for idx in indices:
            pixels = np.where(labels == idx)
            avg_col = np.mean(lab[pixels], axis = 0)
            n_pixels = pixels[0].shape[0]
            bins.append([avg_col, n_pixels])

        bins = np.array(sorted(bins, key=lambda x:x[1], reverse=True))

        n_palette = 10
        preview = np.zeros(shape=(100,1500,3))
        total = np.sum(bins[0:n_palette, 1])
        last  = 0
        for b in range(n_palette):
            preview[:, last : last + (int(bins[b][1] * 1500 / total))] = bins[b, 0]
            last += int(bins[b][1] * 1500 / total)

        return preview.astype(np.uint8)

    # def labels_to_hist_palette(self, lab, labels):
    #     img = self.labels_to_avg_color_mask(lab, labels)
    #     hist1 = calculate_histogram(img, n_bins=64)
    #
    #     return self.hist_to_palette(hist1, n_col=10)
    #     # hist2 = calculate_histogram(img, n_bins=32)
    #     # hist3 = calculate_histogram(img, n_bins=64)

    def hist_to_palette(self, hist, n_col = 10):
        hist_lin = hist.reshape(hist.shape[1] * hist.shape[1] * hist.shape[2])
        shist = np.sort(hist_lin, axis=0)[-n_col:]
        bins = []
        for s in range(shist.shape[0]):
            indices = np.where(hist == shist[s])
            col = np.array([indices[0][0] * (256 / hist.shape[0]) + (256 / hist.shape[0] / 2),
                    indices[1][0] * (256 / hist.shape[0]) + (256 / hist.shape[0] / 2),
                    indices[2][0] * (256 / hist.shape[0]) + (256 / hist.shape[0] / 2)], dtype=np.uint8)
            bins.append([col, shist[s]])

        bins = np.array(bins)
        n_palette = n_col
        preview = np.zeros(shape=(100, 1500, 3))
        total = np.sum(bins[:, 1])
        last = 0
        for b in range(n_palette):
            preview[:, last: last + (int(bins[b][1] * 1500 / total))] = bins[b, 0]
            last += int(bins[b][1] * 1500 / total)

        return preview.astype(np.uint8)


def to_cluster_tree(Z, labels:List, colors, n_merge_steps = 1000, n_merge_per_lvl = 10):
    all_lbl = labels.copy()
    all_col = colors.copy()
    all_n = [1] * len(all_col)

    # print("Recreating Tree")
    for i in range(Z.shape[0]):
        a = int(Z[i][0])
        b = int(Z[i][1])
        all_lbl.append(len(all_lbl))
        all_col.append(np.divide((all_col[a] * all_n[a]) + (all_col[b] * all_n[b]), all_n[a] + all_n[b]))
        all_n.append(all_n[a] + all_n[b])

    result_lbl = [[len(all_lbl) - 1]]
    current_nodes = [len(all_lbl) - 1]
    i = 0

    merge_dists = []
    while(len(current_nodes) <= n_merge_steps and i < len(all_lbl)):
        try:
            curr_lbl = len(all_lbl) - 1 - i
            entry = Z[Z.shape[0] - 1 - i]
            a = int(entry[0])
            b = int(entry[1])
            idx = current_nodes.index(curr_lbl)
            current_nodes.remove(curr_lbl)
            current_nodes.insert(idx, a)
            current_nodes.insert(idx + 1, b)
            result_lbl.append(current_nodes.copy())
            merge_dists.append(entry[2])
            i += 1
        except Exception as e:
            print(e)
            break

    result = []
    cols = np.zeros(shape=(0, 3), dtype=np.uint8)
    ns = np.zeros(shape=(0), dtype=np.uint16)
    layers = np.zeros(shape=(0), dtype=np.uint16)
    cols = []
    ns = []
    layers = []

    all_col = np.array(all_col, dtype=np.uint8)
    all_n = np.array(all_n, dtype=np.uint16)

    i, j = 0, 0
    print("OK")
    for r in result_lbl:
        if i > 10 and i % n_merge_per_lvl != 0:
            i += 1
            continue
        # cols = np.concatenate((cols, all_col[r]))
        # ns = np.concatenate((ns, all_n[r]))
        # layers = np.concatenate((layers, np.array([i] * all_col[r].shape[0])))
        cols.extend(all_col[r])
        ns.extend(all_n[r])
        layers.extend([i] * all_col[r].shape[0])
        i += 1
        j += 1

    cols = np.array(cols,dtype=np.uint8)
    ns = np.array(ns, dtype=np.uint16)
    layers = np.array(layers, dtype=np.uint16)
    print("DONE")

    print((cols.nbytes + ns.nbytes + layers.nbytes)/1000, "Kb")
        # entry = []
        # for lbl in r:
        #     entry.append([
        #         all_col[lbl],
        #         all_n[lbl],
        #                   ])
        # result.append(entry)
    result = [layers, cols, ns]
    return result, merge_dists


def color_palette(frame, mask = None, mask_index = None, n_merge_steps = 100, image_size = 100.0, seeds_model = None,
                  n_pixels = 200, out_path = "", n_merge_per_lvl = 10, plot = False, mask_inverse = False):
    # if mask is not None and mask_index is not None:
    #     frame[np.where(mask!=mask_index)] = [0, 0, 0]

    # print("Seed")
    if seeds_model is None:
        seeds_model = PaletteExtractorModel(frame, n_pixels=n_pixels, num_levels=8)
    labels = seeds_model.forward(frame, 200).astype(np.uint8)
    if out_path != "":
        cv2.imwrite("../../results/seeds_"+out_path+str(n_pixels)+".jpg", cv2.cvtColor(seeds_model.labels_to_avg_color_mask(frame, labels), cv2.COLOR_LAB2BGR))

    # Resizing all to same dimension
    fx = image_size / frame.shape[0]
    frame = cv2.resize(frame, None, None, fx, fx, cv2.INTER_CUBIC)
    labels = cv2.resize(labels, None, None, fx, fx, cv2.INTER_CUBIC)
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_LAB2BGR)

    if mask is not None:
        mask = cv2.resize(mask, None, None, fx, fx, cv2.INTER_CUBIC)

        if mask_inverse:
            labels[np.where(mask != mask_index)] = 255
        else:
            labels[np.where(mask == mask_index)] = 255

        bins = np.unique(labels)
        bins = np.delete(bins, np.where(bins==255))
    else:
        bins = np.unique(labels)


    data = []

    #region SEEDS
    hist = np.histogram(labels, bins = bins)

    #Make sure the normalization factor is not too low
    normalization_f = np.amin(hist[0])
    if normalization_f < 100:
        normalization_f = 100.0
    labels_list = []
    colors_list = []

    all_cols = []
    all_labels = []

    # print("Normalization Factor: ", normalization_f)
    for i, bin in enumerate(hist[0]):
        if bin < normalization_f:
            continue
        lbl = hist[1][i]
        avg_color = np.mean(frame_bgr[np.where(labels == lbl)], axis=0)
        labels_list.append(lbl)
        colors_list.append(avg_color)

        data.extend([avg_color] * int(np.round(bin / normalization_f))*2)
        all_cols.extend([avg_color] * int(np.round(bin / normalization_f)) * 2)
        all_labels.extend([lbl] * int(np.round(bin / normalization_f)) * 2)

    # Uncomment to use the image directly
    # data = np.reshape(frame, newshape=(frame.shape[0] * frame.shape[1], 3))
    # all_cols = np.reshape(frame_bgr, newshape=(frame_bgr.shape[0] * frame_bgr.shape[1], 3)).tolist()
    # all_labels = list(range(data.shape[0]))
    # t = [np.array([a[0], a[1], a[2]]) for a in all_cols]
    # all_cols = t

    data = np.array(data)
    # print(data.shape)
    # print("Calculating Linkage")
    Z = linkage(data, 'ward')

    tree, merge_dists = to_cluster_tree(Z, all_labels, all_cols, n_merge_steps, n_merge_per_lvl)

    if plot:
        print("PLOTTING")
        result_tot = None
        c = -1
        for r in tree:
            c += 1
            if c % n_merge_per_lvl != 0:
                continue

            result_img = np.zeros(shape=(100, 100, 3))
            for itm in r:
                img = np.array([[itm[0]] * itm[1]] * 100)
                result_img = np.hstack((result_img, img))

            result_img = cv2.resize(result_img.astype(np.uint8), (1200, 25), interpolation=cv2.INTER_CUBIC)
            if result_tot is None:
                result_tot = result_img
            else:
                result_tot = np.vstack((result_tot, result_img))
                result_tot = np.vstack((result_tot, np.zeros(shape=(1, 1200, 3))))

        result_tot = cv2.resize(result_tot.astype(np.uint8), (2048, 2048), interpolation=cv2.INTER_CUBIC)
        cv2.imshow("", result_tot)
        cv2.waitKey()
        if out_path !="":
            cv2.imwrite(out_path + ".png", result_tot)
    return PaletteAsset(tree, merge_dists)



if __name__ == '__main__':

    img = cv2.imread("E:/Programming/Git/filmpalette/results/test_frame.png")
    # mask = cv2.imread("E:/Programming/Git/filmpalette/results/test_mask.png", 0)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    p = color_palette(img, n_pixels=100, out_path="mask_test_result",
                  n_merge_steps=200, n_merge_per_lvl=20, plot=False)

    with open("palette.pickle", "wb") as f:
        pickle.dump(p, f)
    # imgs = all_test_images()
    # for p in imgs:
    #     img = cv2.imread(p)
    #     img = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    #     color_palette(img, n_pixels=500, out_path=p.replace("\\", "/").split("/").pop().split(".")[0],
    #                   n_merge_steps=150, n_merge_per_lvl=5)
