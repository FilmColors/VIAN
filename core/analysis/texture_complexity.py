import numpy as np
import cv2

def neighborhood_mean_cv(img, wlen):
    img = img.astype(np.float32)
    wmean = cv2.boxFilter(img, -1, (wlen, wlen), borderType=cv2.BORDER_REFLECT)
    return wmean


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

def get_texture_complexity_heatmap(input_img, blur = False, x2=20, x3=20):
    # input_img = cv2.resize(input_img, None, None, 0.5,0.5, cv2.INTER_CUBIC)
    lab = cv2.cvtColor(input_img, cv2.COLOR_BGR2LAB)
    edges = cv2.Canny(lab, x2, x3).astype(np.float32)
    edges = np.clip(cv2.GaussianBlur(edges, (1, 1), 0), 0, 1.0)
    edge_mean = neighborhood_mean_cv(edges, 20)
    result = edge_mean / np.amax(edge_mean)
    if blur:
        result *= 255
        result = cv2.fastNlMeansDenoising((result * 255).astype(np.uint8), h = 10)
        result = cv2.blur(result.astype(np.float32) / 255, (12, 12))
        result = np.clip(result, 0, 1.0)

    color_img, heatm = get_heatmap_rgb(result, input_img)
    result *= 255
    return color_img, result.astype(np.uint8)