import os

import cv2
import enum
import numpy as np
from core.paths import get_vian_data


# from bokeh import colors


class HilbertMode(enum.Enum):
    """
    Used to define the functionallity of the hilbert_walk() function
    Values_All:         Returns a list of all values from the input array, ordered according to the hilbert traversal.
    Values_Non_Zero:    Return a list of all values from the input array, that are not zero, 
                        ordered according to the hilbert traversal.
    Indices_All:        Returns a list of all indices from an input array, ordered according to the hilbert traversal.
    Indices_Non_Zero:   Return a list of all indices from the input array, that correspond to an element with a non-zero 
                        value, ordered according to the hilbert traversal.
    """
    Values_All = 1
    Values_Non_Zero = 2
    Indices_All = 3
    Indices_Non_Zero = 4


def hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier = 1, x=0, y=0, z=0, dx=1, dy=0, dz=0, dx2=0, dy2=1, dz2=0, dx3=0, dy3=0, dz3=1):
    """
    
    :param data: A three dimensional array with a shape of s^3
    :param mapped: 
    :param mode: As given from HilbertMode Enum
    :param s: cube side length where s is a power of 2
    :param rgb_multiplier: multiplies the output indices if the mode is Indices_All or Indices_Non_Zero
    :param x: 
    :param y: 
    :param z: 
    :param dx: 
    :param dy: 
    :param dz: 
    :param dx2: 
    :param dy2: 
    :param dz2: 
    :param dx3: 
    :param dy3: 
    :param dz3: 
    :return: 
    """
    if s == 1:
        x = int(x)
        y = int(y)
        z = int(z)

        if mode == HilbertMode.Values_Non_Zero:
            if data[int(x), int(y), int(z)] != 0:
                # Adding the Movie to the Aligned Array
                mapped.append((data[int(x), int(y), int(z)] - 1, x, y, z))

        if mode == HilbertMode.Values_All:
            mapped.append(data[int(x), int(y), int(z)])

        if mode == HilbertMode.Indices_All:
            mapped.append([int(x * rgb_multiplier + (rgb_multiplier / 2)), int(y * rgb_multiplier + (rgb_multiplier / 2)),
                                                                               int(z * rgb_multiplier + (rgb_multiplier / 2))])

        if mode == HilbertMode.Indices_Non_Zero:
            if data[int(x), int(y), int(z)] != 0:
                mapped.append([int(x * rgb_multiplier + (rgb_multiplier / 2)), int(y * rgb_multiplier + (rgb_multiplier / 2)),
                               int(z * rgb_multiplier + (rgb_multiplier / 2))])

    else:
        s /= 2
        if dx < 0: x -= s * dx
        if dy < 0: y -= s * dy
        if dz < 0: z -= s * dz
        if dx2 < 0: x -= s * dx2
        if dy2 < 0: y -= s * dy2
        if dz2 < 0: z -= s * dz2
        if dx3 < 0: x -= s * dx3
        if dy3 < 0: y -= s * dy3
        if dz3 < 0: z -= s * dz3


        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x, y, z,
                             dx2, dy2, dz2,
                             dx3, dy3, dz3,
                             dx, dy, dz)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx, y + s * dy, z + s * dz,
                             dx3, dy3, dz3,
                             dx, dy, dz,
                             dx2, dy2, dz2)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx + s * dx2, y + s * dy + s * dy2, z + s * dz + s * dz2,
                             dx3, dy3, dz3,
                             dx, dy, dz,
                             dx2, dy2, dz2)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx2, y + s * dy2, z + s * dz2,
                             -dx, -dy, -dz,
                             -dx2, -dy2, -dz2,
                             dx3, dy3, dz3)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx2 + s * dx3, y + s * dy2 + s * dy3, z + s * dz2 + s * dz3,
                             -dx, -dy, -dz,
                             -dx2, -dy2, -dz2,
                             dx3, dy3, dz3)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx + s * dx2 + s * dx3, y + s * dy + s * dy2 + s * dy3, z + s * dz + s * dz2 + s * dz3,
                             -dx3, -dy3, -dz3,
                             dx, dy, dz,
                             -dx2, -dy2, -dz2)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx + s * dx3, y + s * dy + s * dy3, z + s * dz + s * dz3,
                             -dx3, -dy3, -dz3,
                             dx, dy, dz, -dx2, -dy2, -dz2)
        hilbert_traversal_3d(data, mapped, mode, s, rgb_multiplier,
                             x + s * dx3, y + s * dy3, z + s * dz3,
                             dx2, dy2, dz2,
                             -dx3, -dy3, -dz3,
                             -dx, -dy, -dz)


def hilbert_mapping_3d(s, v_data, hilbert_mode, multiplier = 1):
    v_mapped = []
    hilbert_traversal_3d(v_data, v_mapped, hilbert_mode, s, multiplier)#, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1)
    return v_mapped


def create_hilbert_color_map(s, rgb_multiplier, colorspace):
    grad_rgb = []
    grad_bokeh = []
    # Old Code
    # hilbert_walk_index(np.ones(shape=(s, s, s)), grad_rgb, s, rgb_multiplier)#, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1)
    hilbert_traversal_3d(np.ones(shape=(s, s, s)), grad_rgb, HilbertMode.Indices_All, s, rgb_multiplier)  # , 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1)
    cv2.cvtColor(grad_rgb, colorspace)

    # for bgr in grad_rgb:
    #     grad_bokeh.append(colors.RGB(bgr[2], bgr[1], bgr[0]))

    return grad_bokeh, grad_rgb


def create_hilbert_color_pattern(s = 16, multiplier = 16, color_space = cv2.COLOR_Lab2BGR, filename = "color_pattern", write_to_disc=False):
    grad_hilbert = []
    # OLD Code
    # hilbert_walk_index(np.ones(shape=(s, s, s)), grad_hilbert, s, multiplier)#, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1)
    hilbert_traversal_3d(np.ones(shape=(s, s, s)), grad_hilbert, HilbertMode.Indices_All, s, multiplier)

    grad_source = np.array([grad_hilbert] * 1).astype(dtype=np.uint8)
    grad_in_bgr = cv2.cvtColor(grad_source, color_space)

    # grad_bokeh = []
    # for i in range(grad_in_bgr.shape[1]):
    #     rgb = grad_in_bgr[0][i]
        # grad_bokeh.append(colors.RGB(rgb[2], rgb[1], rgb[0]))

    # Write Gradient to the Disc as Image
    if write_to_disc:
        grad_img = np.array([grad_hilbert] * 500).astype(dtype=np.uint8)
        grad_in_bgr = cv2.cvtColor(grad_img, color_space)
        cv2.imwrite("documents/color_gradient_2" + filename + str(s) + ".png", grad_in_bgr)
    return grad_in_bgr[0]


def create_hilbert_3d_to_2d_coordinates(n):
    mapping = []
    hilbert_traversal_2d(mapping, 0, 0, 1, 0, 0, 1, n)
    return mapping


def create_hilbert_conversion_tables(dir, n1=13, n2=256):
    if not os.path.exists(dir + str("hilbert_conversion.npz")):
        indices_hilbert_3d_list = []
        indices_hilbert_2d_list = []

        hilbert_traversal_2d(indices_hilbert_2d_list, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, n1)
        # OLD CODe
        # hilbert_walk_index(np.ones(shape=(n2, n2, n2)), indices_hilbert_3d_list, n2, 1)#, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        hilbert_traversal_3d(np.ones(shape=(n2, n2, n2)), indices_hilbert_3d_list, HilbertMode.Indices_All, n2, 1)
        indices_hilbert_3d = np.zeros(shape=(n2, n2, n2))
        for index, i in enumerate(indices_hilbert_3d_list):
            indices_hilbert_3d[i[0], i[1], i[2],] = index

        np.savez(dir + str("hilbert_conversion.npz"), hilbert_2d=indices_hilbert_2d_list, hilbert_3d=indices_hilbert_3d)

    loaded = np.load(dir + str("hilbert_conversion.npz"))
    return loaded['hilbert_2d'], loaded['hilbert_3d']


def create_hilbert_lookup_table(s):
    mapped = []
    hilbert_traversal_3d(None, mapped, HilbertMode.Indices_All, s)
    lookup = np.zeros(shape= (s, s, s), dtype=np.uint16)
    idx = 0
    for m in mapped:
        lookup[m[0], m[1], m[2]] = idx
        idx += 1
    return lookup


def create_hilbert_transform(s):
    lookup = create_hilbert_lookup_table(s)
    colors = []
    a, b, c = [], [], []
    for i in range(s**3):
        t = np.where(lookup == i)
        a.append(t[0])
        b.append(t[1])
        c.append(t[2])
        colors.append([t[0][0] * s, t[1][0] * s, t[2][0] * s])
    colors = np.array([colors, colors]).astype(np.uint8)
    colors = cv2.cvtColor(colors, cv2.COLOR_LAB2RGB)[0]
    return (a,b,c), colors


def get_hilbert_lookup():
    p = get_vian_data("hilbert_lookup.npy")
    if os.path.isfile(p):
        return np.load(p)
    else:
         return None


def hilbert_traversal_2d(data, mapped, mode, s, multiplier = 4096, x = 0.0, y = 0.0, dx1 = 1.0, dy1 = 0.0, dx2 = 0.0, dy2 = 1.0):
    """
    http://www.fundza.com/algorithmic/space_filling/hilbert/basics/
    :param mapped: 
    :param x: 
    :param y: 
    :param dx1: 
    :param dy1: 
    :param dx2: 
    :param dy2: 
    :param s: number of items = 4^s-1
    :param multiplier: 
    :return: 
    """
    if s <= 1:
        if mode == HilbertMode.Values_Non_Zero:
            if data[x, y] != 0:
                mapped.append(data[x, y])

        if mode == HilbertMode.Values_All:
            mapped.append(data[x, y])

        if mode == HilbertMode.Indices_All:
            mapped.append([(x + (dx1 + dx2) / 2) * multiplier, (y + (dy1 + dy2) / 2) * multiplier])

        if mode == HilbertMode.Indices_Non_Zero:
            if data[x, y] != 0:
                mapped.append([(x + (dx1 + dx2) / 2) * multiplier, (y + (dy1 + dy2) / 2) * multiplier])

    else:
        s -= 1
        hilbert_traversal_2d(data, mapped, mode, s, multiplier,
                             x, y,
                             dx2 / 2, dy2 / 2,
                             dx1 / 2, dy1 / 2)
        hilbert_traversal_2d(data, mapped, mode, s, multiplier,
                             x + dx1 / 2, y + dy1 / 2,
                             dx1 / 2, dy1 / 2, dx2 / 2, dy2 / 2)
        hilbert_traversal_2d(data, mapped, mode, s, multiplier,
                             x + dx1 / 2 + dx2 / 2, y + dy1 / 2 + dy2 / 2,
                             dx1 / 2, dy1 / 2, dx2 / 2, dy2 / 2)
        hilbert_traversal_2d(data, mapped, mode, s, multiplier,
                             x + dx1 / 2 + dx2, y + dy1 / 2 + dy2,
                             -dx2 / 2, -dy2 / 2, -dx1 / 2, -dy1 / 2)


def convert_hilbert_3d_to_2d(x, y, z, hilbert_conversion_table_2d, hilbert_conversion_table_3d):
    index = int(hilbert_conversion_table_3d[x, y, z])
    return hilbert_conversion_table_2d[index]


def create_1d_to_2d_projection_table():
    mapping = []
    hilbert_traversal_2d(mapping, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 7, multiplier=64)
    return mapping


def hilbert_2d(mapping, x0 = 0.0, y0 = 0.0, xi = 1.0, xj = 0.0, yi = 0.0, yj = 1.0, n = 7, multiplier = 64):
    """
    http://www.fundza.com/algorithmic/space_filling/hilbert/basics/
    :param mapping: 
    :param x0: 
    :param y0: 
    :param xi: 
    :param xj: 
    :param yi: 
    :param yj: 
    :param n: number of items = 4^n-1
    :param multiplier: 
    :return: 
    """
    if n <= 1:
        mapping.append([(x0 + (xi + yi) / 2) * multiplier, (y0 + (xj + yj) / 2) * multiplier])

    else:
        hilbert_2d(mapping, x0, y0, yi / 2, yj / 2, xi / 2, xj / 2, n - 1,multiplier)
        hilbert_2d(mapping, x0 + xi / 2, y0 + xj / 2, xi / 2, xj / 2, yi / 2, yj / 2, n - 1,multiplier)
        hilbert_2d(mapping, x0 + xi / 2 + yi / 2, y0 + xj / 2 + yj / 2, xi / 2, xj / 2, yi / 2, yj / 2, n - 1,multiplier)
        hilbert_2d(mapping, x0 + xi / 2 + yi, y0 + xj / 2 + yj, -yi / 2, -yj / 2, -xi / 2, -xj / 2, n - 1,multiplier)


if __name__ == '__main__':
    import datetime

    start = datetime.datetime.now()
    lookup = create_hilbert_lookup_table(256)
    np.save("hilbert_lookup.npy", lookup)
    print(((datetime.datetime.now() - start)).total_seconds())