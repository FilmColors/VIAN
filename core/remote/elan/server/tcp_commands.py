from enum import Enum

class TCPCommands(Enum):
    # PLAY = 0
    # PAUSE = 1
    # STOP = 2
    # SET_POSITION = 3
    # OPEN_MOVIE = 4
    # DIRECTORY = 5
    # GET_DURATION = 6
    # GET_ASPECT_RATIO = 7
    # GET_TIME_PER_FRAME = 8
    # GET_TIME = 9
    # SET_TIME = 10

    OPEN_MOVIE = 0
    PLAY = 1
    PAUSE = 2
    STOP = 3
    IS_PLAYING = 4  # Boolean
    PLAY_INTERVAL = 5
    SET_OFFSET = 6
    GET_OFFSET = 7
    SET_STOP_TIME = 8
    NEXT_FRAME = 9
    PREVIOUS_FRAME = 10
    SET_FRAME_STEPS_TO_FRAME_BEGIN = 11
    SET_MEDIA_TIME = 12 # Long
    GET_MEDIA_TIME = 13 # Long
    SET_RATE = 14   # Float, bool
    GET_RATE = 15   # void, Float
    IS_FRAME_AUTO_DETECTED = 16 # void, bool
    GET_MEDIA_DURATION = 17     # void, long
    SET_VOLUME = 18         # float, void
    GET_VOLUME = 19         # void, float
    SET_SUB_VOLUME = 20     # float, void
    GET_SUB_VOLUME = 21     # void, float
    SET_MUTE = 22           # bool, void
    GET_MUTE = 23           # void, bool
    GET_SOURCE_WIDTH = 24   # void, int
    GET_SOURCE_HEIGHT = 25  # void, int
    GET_ASPECT_RATIO = 26   # void, float
    SET_ASPECT_RATIO = 27   # float, void
    GET_MILLISECONDS_PER_SAMPLE = 28    # void, double
    SET_MILLISECONDS_PER_SAMPLE = 29    # double, void
    CONNECT = 30




class QueueItem():
    def __init__(self,cmd,args):
        self.cmd = cmd
        self.args = args

