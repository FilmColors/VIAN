
import numpy as np
from bokeh.plotting import figure


def image_plot(title, img, width, height, axis_visible=False):
    shape = np.array(img.shape)

    p = figure(x_range=[0, shape[0]], y_range=[0, shape[1]], plot_width=width, plot_height=height, tools = [])
    p.image_rgba([img], 0, 0, shape[0], shape[1] * float(shape[0])/shape[1]* width/height)

    if not title is None:
        p.title.text = title
        p.title.align = "center"
        p.title.text_font_size = "36px"

    p.axis.visible = axis_visible
    p.toolbar.logo = None
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None

    return p


def plot_segment_tsne(x, y, images, image_width = 20, title = "t-SNE Plot", title_size="36", hide_tools=False):
    ratio = float(images[0].shape[0]) / images[0].shape[1]
    x_size = image_width
    y_size = image_width * ratio

    tools = ["pan, wheel_zoom, reset, resize, save"]
    if hide_tools:
        tools = []
    p = figure(plot_width=2048, plot_height=2048,x_range=(-120, 120), y_range=(-120, 120), tools = tools)
    p.square(x, y, size = 2 ,alpha = 1)
    p.image_rgba(images, x, y, x_size, y_size, )
    p.title.text = title
    p.title.align = "center"
    p.title.text_font_size = title_size

    if hide_tools:
        p.toolbar.logo = None

    return p


def plot_hilbert_color_histogram(title, x, y, color_patter,alpha_bars=1, alpha_floor=1, width=1920, height=720, axis_visible=True,
                                 axis = "log", y_range_max = 10 ** 1, hide_tools = False, y_label = "Normalized Number of Pixels within Bin", label_size = "20px", title_size = "36px", lin_floor = -500):
    if axis == "log":
        y_range = [10 ** -10, y_range_max]
        bottom = 10**-9
        floor = 10**-10
    else:
        y_range = [lin_floor, y_range_max]
        bottom = 0
        floor = lin_floor

    tools = "resize,pan,wheel_zoom,box_zoom,reset,save"
    if hide_tools:
        tools =[]

    color_hist = figure(width=width, height=height, y_axis_type=axis, y_range=y_range, tools =tools)
    color_hist.vbar(x=x, width = 1, bottom = floor, top =bottom, color= color_patter, alpha=alpha_floor)
    color_hist.vbar(x=x, width=1, bottom=bottom, top=y, color=color_patter, alpha=alpha_bars)

    if not title is None:
        color_hist.title.text = title
        color_hist.title.align = "center"
        color_hist.title.text_font_size = title_size

    color_hist.xaxis.axis_label_text_font_size = label_size
    color_hist.yaxis.axis_label_text_font_size = label_size

    color_hist.axis.visible = axis_visible
    color_hist.xaxis.axis_label = "Histogram Bin"
    color_hist.yaxis.axis_label = y_label
    if hide_tools:
        color_hist.toolbar.logo = None
    return color_hist


def plot_palette_hist(title, y, color, width = 1000, height = 500, hide_tools = True, background = "white"):
    x = range(len(y))
    y_max = np.amax(y)

    p = figure(width=width, height=height, y_axis_type="log", y_range = [10**-2, y_max + 0.2], tools = [])
    p.background_fill_color = background
    p.vbar(x=x, width=1, bottom=10**-2, top=y, color=color)

    if not title is None:
        p.title.text = title
        p.title.align = "center"
        p.title.text_font_size = "36px"

    p.xaxis.axis_label_text_font_size = "20px"
    p.yaxis.axis_label_text_font_size = "20px"


    p.xaxis.axis_label = "Histogram Bin"
    p.yaxis.axis_label = "Normalized Histogram Value"

    if hide_tools:
        p.xgrid.grid_line_color = None
        p.ygrid.grid_line_color = None
        p.axis.visible = False
        p.toolbar.logo = None

    return p


def plot_palette_alpha(title, x, y, color, alpha, width = 1024, height = 1024, background = "white",  hide_tools = True):

    p = figure(plot_width=width, plot_height=height,
               tools=[], x_range = [1,65], y_range=[1,65])
    p.background_fill_color = background
    p.square(x, y, size=width / 66, color=color, alpha=alpha)
    p.square(x, y, size=width / 66, color=color, alpha=1.0)

    p.title.text = title
    p.title.align = "center"
    p.title.text_font_size = "48px"
    p.xaxis.axis_label_text_font_size = "30px"
    p.yaxis.axis_label_text_font_size = "30px"

    if hide_tools:
        p.xgrid.grid_line_color = None
        p.ygrid.grid_line_color = None
        p.axis.visible = False
        p.toolbar.logo = None

    return p


def plot_palette_resized(title, x, y, color,value, width = 1024, height = 1024, background ="white",  hide_tools = True):
    n_x = np.unique(x).shape[0]
    n_y = np.unique(y).shape[0]

    if n_y > n_x:
        s = float(height) / (n_y + 6)
        range_max = n_y + 2
    else:
        s = float(width) / (n_x + 6)
        range_max = n_x + 2

    value = np.multiply(value, s)

    p = figure(plot_width=width, plot_height=height, x_range = [-2, range_max], y_range=[-2, range_max], tools = [])
    p.background_fill_color = background
    p.square(x, y, size=value, color=color)

    p.title.text = title
    p.title.align = "center"
    p.title.text_font_size = "48px"
    p.xaxis.axis_label_text_font_size = "30px"
    p.yaxis.axis_label_text_font_size = "30px"

    if hide_tools:
        p.xgrid.grid_line_color = None
        p.ygrid.grid_line_color = None
        p.axis.visible = False
        p.toolbar.logo = None

    return p

