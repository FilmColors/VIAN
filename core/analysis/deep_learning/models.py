from core.analysis.deep_learning.pspnet import *
import cv2
import keras.backend.tensorflow_backend as KTF
from core.analysis.import_tensortflow import tf
from core.analysis.deep_learning.labels import *

from core.data.log import log_info

DIR_WEIGHTS_BUILT_IN = "/data/models/"
KERAS_LIP_WEIGHTS = "data/models/semantic_segmentation/LIP_PSPNET50_Weights.hdf5"


class VIANKerasModel():
    """
    This is the base class of VIAN Models. 
    It should be treated as an interface to implement. 
    """

    def init_model(self):
        """
        This is where the model should be build
        :return: 
        """
        pass

    def forward(self, frame):
        """
        Compute the next frame
        :param frame: 
        :return: 
        """
        pass

    def load_weights(self, path):
        """
        :param path: The absolute path to the stored weights
        :return: 
        """
        pass

    def store_weights(self, path):
        """

        :param path: The absolute path to store the weights
        :return: 
        """
        pass

    def train(self, args):
        pass


class PSPNetModelVIAN(VIANKerasModel):
    def __init__(self, input_shape = (256, 256, 3), n_labels=20, kernel=3, pool_size = (2,2), output_mode="softmax"):
        self.input_shape = input_shape
        self.n_labels = n_labels
        self.model = PSPNet50(
                input_shape=input_shape,
                n_labels=n_labels,
                output_mode=output_mode,
                upsample_type="deconv")

    def load_weights(self, path):
        log_info("Loading Weights...")
        self.model.load_weights(path)
        log_info("Done")

    def forward(self, frame, threshold = -1.0):
        resized = cv2.resize(frame, (self.input_shape[0], self.input_shape[1]), interpolation=cv2.INTER_CUBIC)[:, :, ::-1]
        out = np.reshape(self.model.predict(np.array([resized]).astype(np.float32) / 255.0), (1, self.input_shape[0], self.input_shape[1], self.n_labels))[0]
        out = cv2.resize(out, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_CUBIC)
        # out = np.argmax(cv2.resize(out, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_CUBIC), axis = 2).astype(np.uint8)
        return out

    def train(self, args):
        pass


class RealTimeHumanExtractor:
    prototxt = "data/models/semantic_segmentation/MobileNetSSD_deploy.prototxt.txt"
    model = "data/models/semantic_segmentation/MobileNetSSD_deploy.caffemodel"

    def __init__(self, confidence = 0.5):
        self.confidence = confidence
        self.classes = ["background", "aeroplane", "bicycle", "bird", "boat",
                        "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                        "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
                        "sofa", "train", "tvmonitor"]
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
        self.net = cv2.dnn.readNetFromCaffe(self.prototxt, self.model)

    def forward(self, image, label_filter = 15):
        (h, w) = image.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 0.007843, (300, 300), 127.5)
        self.net.setInput(blob)
        detections = self.net.forward()

        result = []

        # loop over the detections
        for i in np.arange(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > self.confidence:
                if int(detections[0, 0, i, 1]) == label_filter:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    result.append(image[startY:endY, startX:endX])

        return result

        # show the output image


if __name__ == '__main__':
    import glob
    from core.analysis.deep_learning.labels import LIPLabels

    with tf.Graph().as_default():

        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True  # dynamically grow the memory used on the GPU
        # config.log_device_placement = True  # to log device placement (on which device the operation ran)

        session = tf.Session(config)
        KTF.set_session(session)

        files = glob.glob("test_images/*.jpg")
        model = PSPNetModelVIAN(input_shape=(512, 512, 3))
        for f in files:
            img = cv2.imread(f)
            result = model.forward(img)
            for r in range(result.shape[2]):
                mask = cv2.cvtColor(result[:,:,r].astype(np.float32), cv2.COLOR_GRAY2BGR)
                color = np.zeros_like(img)
                color[:] = [200,0,0]
                rimg = ((img * (1.0 - mask)) + (mask * color)).astype(np.uint8)

                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(rimg, LIPLabels(r).name, (10, 100), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

                cv2.imshow("Window", rimg)
                cv2.imshow("Mask", mask)
                cv2.waitKey()


