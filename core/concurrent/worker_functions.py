from core.data.computation import *
from core.data.containers import *
from core.data.interfaces import IConcurrentJob
from core.gui.main_window import *
from collections import namedtuple
from PyQt5 import QtGui
from PyQt5.QtCore import QRect, Qt
import json



def create_screenshot(args, sign_progress):

    drawing_overlay = args[0]
    frame = args[1]
    time = args[2]
    frame_pos = args[3]

    qimage, frame = drawing_overlay.render_annotation(frame)

    blend = None
    annotation = None

    if qimage is not None:
        annotation = convertQImageToMat(qimage)
        blend = blend_transparent(frame, annotation)

    shot = Screenshot("New Screenshot", frame, annotation, blend, time, 0, frame_pos)


    return shot


def store_project_concurrent(args, sign_progress):
    project = args[0]
    path = args[1]
    settings = args[2]
    global_settings = args[3]

    a_layer = []
    screenshots = []
    screenshots_img = []
    screenshots_ann = []
    segmentations = []
    analyzes = []
    screenshot_groups = []
    scripts = []

    vocabularies = []

    for v in project.vocabularies:
        vocabularies.append(v.serialize())

    for a in project.annotation_layers:
        a_layer.append(a.serialize())

    sign_progress(0.2)

    for b in project.screenshots:
        src, img = b.serialize()
        screenshots.append(src)
        # screenshots_img.append(img[0])
        # screenshots_ann.append(img[1])

    sign_progress(0.4)
    for c in project.segmentation:
        segmentations.append(c.serialize())

    for d in project.analysis:
        analyzes.append(d.serialize())

    for e in project.screenshot_groups:
        screenshot_groups.append(e.serialize())

    for f in project.node_scripts:
        scripts.append(f.serialize())

    data = dict(
        path=project.path,
        name=project.name,
        annotation_layers=a_layer,
        notes=project.notes,
        current_annotation_layer=None,
        main_segmentation_index=project.main_segmentation_index,
        screenshots=screenshots,
        segmentation=segmentations,
        analyzes=analyzes,
        movie_descriptor=project.movie_descriptor.serialize(),
        version=project.main_window.version,
        screenshot_groups=screenshot_groups,
        scripts = scripts,
        vocabularies=vocabularies

    )
    sign_progress(0.6)
    if path is None:
        path = project.path
    path = path.replace(settings.PROJECT_FILE_EXTENSION, "")

    numpy_path = path + "_scr"
    project_path = path + ".eext"


    if settings.SCREENSHOTS_STATIC_SAVE:
        np.savez(numpy_path, imgs=screenshots_img, annotations=screenshots_ann, empty=[True])

    global_settings.add_project(project)

    sign_progress(0.8)
    try:
        with open(project_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print e.message

    sign_progress(1.0)


class LoadScreenshotsJob(IConcurrentJob):

    def run_concurrent(self, args, sign_progress):
        movie_path = args[0]
        locations = args[1]
        annotation_dicts = args[2]

        video_capture = cv2.VideoCapture(movie_path)
        screenshots = []
        annotations = []
        for i,frame_pos in enumerate(locations):
            sign_progress(float(i)/len(locations))

            video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = video_capture.read()
            if len(annotation_dicts[i]) > 0:
                annotation = render_annotations(frame, annotation_dicts[i]).astype(np.uint8)
            else:
                annotation = None

            screenshots.append(frame)
            annotations.append(annotation)

        return [screenshots, annotations]

    def modify_project(self, project, result, sign_progress = None):
        images = result[0]
        annotations = result[1]

        for i, img in enumerate(images):
            # sign_progress(int(float(i) / len(images) * 100))
            if img is None:
                break

            project.screenshots[i].img_movie = img.astype(np.uint8)
            project.screenshots[i].img_blend = annotations[i]

            # project.screenshots[i].to_stream(project)

            project.dispatch_changed()

        # sign_progress(100)


class CreateScreenshotJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        frame_pos = args[0]
        movie_path = args[1]
        annotation_dicts = args[2]
        time = args[3]


        # Create Screenshot Image
        video_capture = cv2.VideoCapture(movie_path)
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = video_capture.read()

        if frame is None:
            raise IOError("Couldn't Read Frame")

        if len(annotation_dicts) > 0:
            frame_annotated = render_annotations(frame, annotation_dicts)
        else:
            frame_annotated = None

        annotation_ids = []
        for a in annotation_dicts:
            annotation_ids.append(a['unique_id'])

        return [frame, frame_annotated, frame_pos, time, annotation_ids]

    def modify_project(self, project, result, sign_progress = None):
        frame = result[0]
        frame_annotated = result[1]
        frame_pos = result[2]
        time = result[3]
        annotation_ids = result[4]

        shot = Screenshot(title="New Screenshot", image=frame, img_blend=frame_annotated, timestamp=time, frame_pos=frame_pos, annotation_item_ids=annotation_ids)
        project.add_screenshot(shot)
        try:
            if project.has_segmentation():
                segm = project.get_main_segmentation()
                if len(segm.segments) > 0:
                    shot.update_scene_id(project.get_main_segmentation())
        except RuntimeError as e:
            raise e


class ImportScreenshotsJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        shots_paths = args[0]
        movie_path = args[1]
        segments = args[2]

        video_capture = cv2.VideoCapture(movie_path)
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        length = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        shots_bgr = []
        shots_gray = []
        current_segment = 0
        shots_bgr_segment = []
        shots_gray_segment = []


        for i, p in enumerate(shots_paths):
            splitted = p.replace("\\", "/").split("/").pop().split("_")
            i_id = splitted.index("SCR") + 1
            new_index = int(splitted[i_id]) - 1

            if new_index == current_segment:
                shots_bgr.append(shots_bgr_segment)
                shots_gray.append(shots_gray_segment)
                shots_gray_segment = []
                shots_bgr_segment = []


            img_bgr = cv2.imread(p)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            resized_image = cv2.resize(img_gray, (width, height))
            shots_bgr_segment.append(img_bgr)
            shots_gray_segment.append([resized_image, 10**6, -1, p])

        # for i, s in enumerate(shots_gray_segment):
        #     for t in s:
        #         print t[3]

        for s in segments:

            result_time = []
            result = []
            for i in range(length):
                if i % 100 == 0:
                    sign_progress(float(i) / length)

                ret, frame = video_capture.read()

                if ret is None:
                    break

                image = frame
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                for j, s in enumerate(shots_gray):
                        x = mse(gray, s[0])
                        if x < s[1]:
                            s[1] = x
                            s[2] = i

            # x1 = mse(resized_image, shots_gray[current_shot_idx])
            # x2 = mse(resized_image, shots_gray[current_shot_idx + 1])

            # if x1 < x1_min:
            #     x1_min = x1
            #     x1_res = i
            #     print x1_res
            # if x2 < x2_min:
            #     x2_min = x1
            #     x2_res = i
            #
            # if x2 < x1_res:
            #     result_time.append(x1_res)
            #     x1_min = x2_min
            #     x1_res = x2_res
            #     cv2.imshow("Result", frame)
            #     cv2.imshow("Input", shots_bgr[current_shot_idx])
            #     cv2.waitKey()
            #     current_shot_idx += 1


        for s in result:
            result_time.append(s[2])


        return [result_time, shots_bgr]


def render_annotations(frame, annotation_dicts):
    qimage, qpixmap = numpy_to_qt_image(frame)
    qp = QtGui.QPainter(qimage)

    qp.setRenderHint(QtGui.QPainter.Antialiasing)
    qp.setRenderHint(QtGui.QPainter.TextAntialiasing)

    for a in annotation_dicts:
        position    = a['orig_position']  # orig position has been modified depending on the keys
        a_type      = AnnotationType(a['a_type'])
        size        = a['size']
        color       = a['color']
        color = QtGui.QColor(color[0], color[1], color[2])
        line_width  = a['line_w']
        text        = a['text']
        font_size   = a['font_size']
        resource    = a['resource_path']
        free_hand_paths = a['free_hand_paths']

        pen = QtGui.QPen()
        pen.setColor(color)
        pen.setWidth(line_width)
        qp.setPen(pen)

        x = position[0]
        y = position[1]
        w = size[0]
        h = size[1]

        local_rect = QtCore.QRect(x, y, w, h)
        s = local_rect
        l = line_width
        inner_rect_delta = 10
        inner_rect = QtCore.QRect(s.x() + l + inner_rect_delta,
                                       s.y() + l + inner_rect_delta,
                                       s.width() - 2 * l - 2 * inner_rect_delta,
                                       s.height() - 2 * l - 2 * inner_rect_delta)

        if a_type == AnnotationType.Ellipse:
            qp.drawEllipse(inner_rect)

        if a_type == AnnotationType.Rectangle:
            qp.drawRect(inner_rect)

        if a_type == AnnotationType.Text:
            font = QtGui.QFont()
            font.setPointSize(font_size)
            qp.setFont(font)
            qp.drawText(inner_rect, Qt.TextWordWrap, text)

        if a_type == AnnotationType.Image:
            img = cv2.imread(resource, -1)
            if img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            img, pix = numpy_to_qt_image(img, cv2.COLOR_BGRA2RGBA, with_alpha=True)
            qp.drawImage(inner_rect, img)

        if a_type == AnnotationType.FreeHand:
            dx = position[0]
            dy = position[1]
            for p in free_hand_paths:
                path = QtGui.QPainterPath()
                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(p[1][0], p[1][1], p[1][2]))
                pen.setWidth(p[2])
                qp.setPen(pen)

                if not len(p[0]) == 0:
                    path.moveTo(QtCore.QPointF(p[0][0][0] + dx, p[0][0][1] + dy))
                    for i in range(1, len(p[0]), 1):
                        path.lineTo(QtCore.QPointF(p[0][i][0] + dx, p[0][i][1] + dy))

                qp.drawPath(path)
    qp.end()

    img_numpy = convertQImageToMat(qimage)
    img_numpy = cv2.cvtColor(img_numpy, cv2.COLOR_BGRA2BGR)

    return img_numpy


class ScreenshotStreamingJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        screenshots = args[0]
        scale = args[1]

        for s in screenshots:
            s.resize(scale)


    def modify_project(self, project, result, sign_progress = None):
       pass