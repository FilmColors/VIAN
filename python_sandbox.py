import cv2
import numpy as np
from random import randint
from sys import stdout as console

path = "C:\\Users\\Gaudenz Halter\\Desktop\\matrix_2.mp4"

def find_closest(frame, segment):
    a = np.sum((segment - frame[np.newaxis, ...]) ** 2, axis=(1, 2, 3))
    match = np.argmin(a)
    rate = np.amin(a)
    return match, rate

if __name__ == '__main__':

    cap = cv2.VideoCapture(path)
    length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    # length = 3000

    segm_length = 1000
    resolution = 10
    quality = 0.3

    width = int(width * quality)
    height = int(height * quality)
    width = 200
    height = 200

    scrs = []
    for i in range(5):
        idx = randint(0, length)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        frame = cv2.resize(frame, None, None, 0.5, 0.5, interpolation=cv2.INTER_CUBIC)
        scrs.append(frame)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame_counter = -1
    n_segments = int(np.ceil(length/segm_length))


    match_table = np.zeros(shape=(n_segments, len(scrs), 2))

    new_scr = []
    for scr in scrs:
        new_scr.append(cv2.resize(scr, (int(width), int(height)), interpolation=cv2.INTER_CUBIC))
    scrs = np.array(new_scr, dtype=np.float32)


    for i in range(n_segments):
        frames = []
        frame_idxs = []
        for j in range(segm_length):
            if j % 20 == 0:
                console.write("\r" + str(round(((i * segm_length + j) / length * 100), 2)).rjust(6) + "%")
                console.flush()
            ret, frame = cap.read()
            frame_counter += 1
            if j % resolution != 0:
                continue


            if ret:
                frame = cv2.resize(frame, (int(width), int(height)), interpolation=cv2.INTER_CUBIC)
                frames.append(frame)
                frame_idxs.append(frame_counter)

            else:
                break


        frames = np.array(frames, dtype=np.float32)
        for j in range(scrs.shape[0]):
            match, rate = find_closest(scrs[j], frames)

            match2 = frame_idxs[match]
            match = (match * resolution) + (segm_length * i)

            match_table[i, j] = [match, rate]

    result = []
    for i in range(scrs.shape[0]):
        best_value = np.amin(match_table[:, i, 1])
        best_idx = np.argmin(match_table[:, i, 1])
        frame_idx = match_table[best_idx, i, 0]
        result.append([frame_idx, best_value])


    for i, r in enumerate(result):
        cap.set(cv2.CAP_PROP_POS_FRAMES, r[0])
        ret, frame = cap.read()
        print(r[1])
        cv2.imshow("Result", frame)
        cv2.imshow("Input", scrs[i].astype(np.uint8))
        cv2.waitKey()





