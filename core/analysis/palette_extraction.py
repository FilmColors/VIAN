"""
Author: Gaudenz Halter
University of Zurich
"""
from scipy.cluster.hierarchy import *
from fastcluster import linkage
import numpy as np
import cv2
from typing import List


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

    cols = np.zeros(shape=(0, 3), dtype=np.uint8)
    ns = np.zeros(shape=(0), dtype=np.uint16)
    layers = np.zeros(shape=(0), dtype=np.uint16)

    all_col = np.array(all_col, dtype=np.uint8)
    all_n = np.array(all_n, dtype=np.uint16)

    i = 0
    for r in result_lbl:
        if i > 10 and i % n_merge_per_lvl != 0:
            i += 1
            continue
        cols = np.concatenate((cols, all_col[r]))
        ns = np.concatenate((ns, all_n[r]))
        layers = np.concatenate((layers, np.array([i] * all_col[r].shape[0])))
        i += 1

    result = [layers, cols, ns]
    return result, merge_dists


def color_palette(frame, mask = None, mask_index = None, n_merge_steps = 100, image_size = 100.0, seeds_model = None,
                  n_pixels = 200, out_path = "", n_merge_per_lvl = 10, plot = False, mask_inverse = False, normalization_lower_bound = 100.0):
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
    if normalization_f < normalization_lower_bound:
        normalization_f = normalization_lower_bound
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

    data = np.array(data)
    Z = linkage(data, 'ward')
    tree, merge_dists = to_cluster_tree(Z, all_labels, all_cols, n_merge_steps, n_merge_per_lvl)

    return PaletteAsset(tree, merge_dists)


