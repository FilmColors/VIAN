import numpy as np
import cv2

def neighborhood_mean_cv(img, wlen):
    img = img.astype(np.float32)
    wmean = cv2.boxFilter(img, -1, (wlen, wlen), borderType=cv2.BORDER_REFLECT)
    return wmean


def img_lab_to_lch(lab):
    oshape = lab.shape

    lab = np.reshape(lab, newshape=(lab.shape[0]*lab.shape[1], 3))
    lch = np.zeros_like(lab)
    lch[:, 0] = lab[:, 0]
    lch[:, 1] = np.linalg.norm(lab[ :, 1:3], axis=1)
    lch[:, 2] = np.arctan2(lab[:, 2], lab[:, 1])
    lch = np.reshape(lch, oshape)
    return lch


def neighborhood_var_cv(img, wlen, channels = None):
    if channels is not None:
        img = img[:,:,channels]
    img = img.astype(np.float32)
    wmean, wsqrmean = (cv2.filter2D(x, -1, cv2.getGaussianKernel(wlen, wlen) , borderType=cv2.BORDER_REFLECT) for x in (img, img * img)) # (wlen, wlen)
    if len(wmean.shape) == 2:
        wmean = np.reshape(wmean, newshape=wmean.shape + (1,))
    if len(wsqrmean.shape) == 2:
        wsqrmean = np.reshape(wsqrmean, newshape=wsqrmean.shape + (1,))
    result = np.sum(wsqrmean - wmean**2, axis=2) / 255**2
    return result


def get_heatmap_rgb(img, to_blend = None):
    result = np.zeros(shape=(img.shape[0], img.shape[1], 3), dtype=np.uint8)
    result[:, :, 2] = ((np.clip(img, 0.5, 1.0) - 0.5) / 0.5) * 255
    result[:, :, 1] = (0.25 - np.abs(np.clip(img, 0.25, 0.75) - 0.5)) / 0.25 * 255
    # result[:, :, 0] = ((0.5 - np.clip(img, 0, 0.5)) / 0.5) * 0

    if to_blend is not None:
        blended = (result * 0.5) + (0.5 * to_blend)
        return blended.astype(np.uint8), result
    else:
        return result


def get_spacial_frequency_heatmap(input_img, blur = False, x2=20, x3=20, method = "edge-mean", normalize = True, norm_factor = None):
    # input_img = cv2.resize(input_img, None, None, 0.5,0.5, cv2.INTER_CUBIC)
    lab = cv2.cvtColor(input_img, cv2.COLOR_BGR2LAB)
    if method == "edge-mean":
        edges = cv2.Canny(lab, x2, x3).astype(np.float32)
        edges = np.clip(cv2.GaussianBlur(edges, (1, 1), 0), 0, 1.0)
        edge_mean = neighborhood_mean_cv(edges, 20)
        raw = edge_mean
        if normalize:
            if norm_factor is None:
                norm_factor = np.amax(edge_mean)
            result = edge_mean / norm_factor
        else:
            result = raw.copy()

        if blur:
            result *= 255
            result = cv2.fastNlMeansDenoising((result * 255).astype(np.uint8), h = 10)
            result = cv2.blur(result.astype(np.float32) / 255, (12, 12))
            result = np.clip(result, 0, 1.0)

        color_img, heatm = get_heatmap_rgb(result, input_img)
        result *= 255
        return color_img, result.astype(np.uint8), raw
    elif method == "color-var":
        col_var = neighborhood_var_cv(lab.astype(np.float32), 20, channels=(1, 2))
        raw = col_var.copy()
        if normalize:
            if norm_factor is None:
                norm_factor = np.amax(col_var)
            col_var = col_var / norm_factor
        hcut = np.percentile(col_var, 95)
        col_var[np.where(col_var > 0.95)] = np.mean(col_var)
        col_var = cv2.blur(col_var, (12, 12))
        col_var = col_var / hcut
        color_img, heatm = get_heatmap_rgb(col_var, input_img)
        return color_img, col_var, raw

    elif method == "hue-var":
        lab = cv2.cvtColor(input_img.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
        lch = img_lab_to_lch(lab)
        hue_var = neighborhood_var_cv(lch.astype(np.float32), 20, channels=(1))
        raw = hue_var.copy()
        if normalize:
            if norm_factor is None:
                norm_factor = np.amax(hue_var)
            hue_var = hue_var / norm_factor
        hue_var = hue_var / np.amax(hue_var)
        hcut = np.percentile(hue_var, 95)
        hue_var = hue_var / hcut
        hue_var[np.where(hue_var > 0.95)] = np.mean(hue_var)
        hue_var = cv2.blur(hue_var, (12, 12))
        color_img, heatm = get_heatmap_rgb(hue_var, input_img)
        return color_img, hue_var, raw

    elif method == "luminance-var":
        lum_var = neighborhood_var_cv(lab.astype(np.float32), 20, channels=(0))
        raw = lum_var.copy()
        if normalize:
            if norm_factor is None:
                norm_factor = np.amax(lum_var)
            lum_var = lum_var / norm_factor
        hcut = np.percentile(lum_var, 95)
        lum_var = lum_var / hcut
        lum_var[np.where(lum_var > 0.95)] = np.mean(lum_var)
        lum_var = cv2.blur(lum_var, (12, 12))
        color_img, heatm = get_heatmap_rgb(lum_var, input_img)
        return color_img, lum_var, raw
    else:
        return input_img, np.zeros_like(input_img), np.zeros_like(input_img)


def convolve_segmentation(values, segmentation):
    for t in np.unique(segmentation).tolist():
        indices = np.where(segmentation == t)
        values[indices] = np.mean(values[indices])
    return values


def get_spacial_frequency_heatmap2(input_img, blur = False, x2=20, x3=20, method = "edge-mean", normalize = True, norm_factor = 1.0, model=None):
    # input_img = cv2.resize(input_img, None, None, 1.0, 1.0, cv2.INTER_CUBIC)
    lab = cv2.cvtColor(input_img.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    # lab[:, :, 0] = lab[:, :, 0] - np.amin(lab[:, :, 0])
    # lab[:, :, 0] = lab[:, :, 0] / np.amax(lab[:, :, 0])
    # lab[:, :, 1] = lab[:, :, 1] - np.amin(lab[:, :, 1])
    # lab[:, :, 1] = lab[:, :, 1] / np.amax(lab[:, :, 1])
    # lab[:, :, 2] = lab[:, :, 2] - np.amin(lab[:, :, 2])
    # lab[:, :, 2] = lab[:, :, 2] / np.amax(lab[:, :, 2])

    model.iterate(lab)
    segmentation = model.getLabels()

    if method == "edge-mean":
        edges = cv2.Canny(cv2.cvtColor(input_img, cv2.COLOR_BGR2LAB), 20, 20).astype(np.float32)
        edges = np.clip(cv2.GaussianBlur(edges, (1, 1), 0), 0, 1.0)
        raw = edges.copy()
        edge_mean = neighborhood_mean_cv(edges, 20)
        edge_mean /= np.amax(edge_mean)
        # cv2.imshow("found edges", edge_mean)

        t = convolve_segmentation(edge_mean, segmentation)
        t = np.clip(cv2.GaussianBlur(t, (5, 5), 0), 0, 1.0)
        img, heatm = get_heatmap_rgb(t, input_img)
        return img, heatm, raw

    elif method == "color-var":
        col_var = neighborhood_var_cv(lab.astype(np.float32), 50, channels=(1, 2))
        raw = col_var.copy()
        hcut = np.percentile(col_var, 95)
        col_var /= norm_factor
        t = convolve_segmentation(col_var, segmentation)
        t = np.clip(cv2.GaussianBlur(t, (5, 5), 0), 0, 1.0)
        img, heatm = get_heatmap_rgb(t, input_img)
        return img, heatm, raw

    elif method == "luminance-var":
        lum_var = neighborhood_var_cv(lab.astype(np.float32), 20, channels=(0))
        raw = lum_var.copy()
        hcut = np.percentile(lum_var, 95)
        lum_var = lum_var / norm_factor
        t = convolve_segmentation(lum_var, segmentation)
        t = np.clip(cv2.GaussianBlur(t, (5, 5), 0), 0, 1.0)
        img, heatm = get_heatmap_rgb(t, input_img)
        return img, heatm, raw

    else:
        return input_img, None, None



