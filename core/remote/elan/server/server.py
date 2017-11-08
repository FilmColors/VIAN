import socket
import threading

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal


from tcp_commands import TCPCommands


class ServerInfo:
    def __init__(self):
        self.isConnected = False
        self.messages = []

    def push_message(self, message):
        self.messages.append(message)

    def pop_message(self):
        if len(self.messages)>0:
            message = self.messages[0]
            self.messages.remove(message)
            return (True,message)
        else:
            return (False, None)

class Server(threading.Thread):
    def __init__(self,instance,vlc_player, player = None):
        threading.Thread.__init__(self)
        self.player = player
        self.instance = instance
        self.vlc_player = vlc_player
        self.TCP_IP = '127.0.0.1'
        self.TCP_PORT = 5005
        self.BUFFER_SIZE = 1024
        self.active = True
        self.is_connected = False

        # SIGNALS
        self.movieOpened = pyqtSignal()
        self.connectionChanged = pyqtSignal()



    def run(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.TCP_IP, self.TCP_PORT))
        while self.active:
            self.listen()


    def quit(self):
        self.active = False
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.TCP_IP, self.TCP_PORT))

    def listen(self):

        self.s.listen(1)

        conn, addr = self.s.accept()
        print 'Connection addres: ', addr
        self.is_connected = True
        while (self.active):
            try:
                data = conn.recv(self.BUFFER_SIZE)
                if not data: break
                ret = self.parse_msg(data)
                ret = self.parse_answer(ret)
                conn.send(ret)
            except IOError as e:
                print e.message

        conn.close()
        self.is_connected = False

    def parse_msg(self, msg = ""):

        sep = ';'
        msg_split = msg.split(sep)
        cmd = int(msg_split[0])
        args = msg_split[1:len(msg_split)]

        if cmd == TCPCommands.OPEN_MOVIE.value:
            self.player.open_movie(args[0], from_server = True)
            return 0

        if cmd == TCPCommands.PLAY.value:
            self.player.play()
            return 0

        if cmd == TCPCommands.PAUSE.value:
            self.player.pause()
            return 0

        if cmd == TCPCommands.STOP.value:
            self.player.stop()
            return 0

        if cmd == TCPCommands.IS_PLAYING.value:
            #
            return self.player.is_playing()

        if cmd == TCPCommands.PLAY_INTERVAL.value:
            self.player.play_interval(args[0], args[1])
            return 0

        if cmd == TCPCommands.SET_OFFSET.value:
            self.player.set_offset(args[0])
            return 0

        if cmd == TCPCommands.GET_OFFSET.value:
            #
            return self.player.get_offset()

        if cmd == TCPCommands.SET_STOP_TIME.value:
            self.player.set_stop_time(args[0])
            return 0

        if cmd == TCPCommands.NEXT_FRAME.value:
            self.player.next_frame()
            return 0

        if cmd == TCPCommands.PREVIOUS_FRAME.value:
            self.player.previous_frame()
            return 0

        if cmd == TCPCommands.SET_FRAME_STEPS_TO_FRAME_BEGIN.value:
            self.player.set_frame_steps_to_frame_begin(args[0])
            return 0

        if cmd == TCPCommands.SET_MEDIA_TIME.value:
            self.player.set_media_time(args[0])
            return 0

        if cmd == TCPCommands.SET_FRAME_STEPS_TO_FRAME_BEGIN.value:
            #
            return self.player.get_media_time()

        if cmd == TCPCommands.SET_RATE.value:
            self.player.set_rate(args[0])
            return 0

        if cmd == TCPCommands.GET_RATE.value:
            #
            return self.player.set_rate()

        if cmd == TCPCommands.IS_FRAME_AUTO_DETECTED.value:
            #
            return self.player.is_frame_rate_auto_detected()

        if cmd == TCPCommands.GET_MEDIA_DURATION.value:
            #
            return self.player.get_media_duration()

        if cmd == TCPCommands.SET_VOLUME.value:
            self.player.set_volume(args[0])
            return 0

        if cmd == TCPCommands.GET_VOLUME.value:
            #
            return self.player.get_volume()

        if cmd == TCPCommands.SET_SUB_VOLUME.value:
            self.player.set_sub_volume(args[0])
            return 0

        if cmd == TCPCommands.GET_SUB_VOLUME.value:
            #
            return self.player.get_sub_volume()

        if cmd == TCPCommands.SET_MUTE.value:
            self.player.set_mute(args[0])
            return 0

        if cmd == TCPCommands.GET_MUTE.value:
            #
            return self.player.get_mute()

        if cmd == TCPCommands.GET_SOURCE_WIDTH.value:
            #
            return self.player.get_source_width()

        if cmd == TCPCommands.GET_SOURCE_HEIGHT.value:
            #
            return self.player.get_source_height()

        if cmd == TCPCommands.GET_ASPECT_RATIO.value:
            #
            return self.player.get_aspect_ratio()

        if cmd == TCPCommands.SET_ASPECT_RATIO.value:
            self.player.set_aspect_ratio(args[0])
            return 0

        if cmd == TCPCommands.GET_MILLISECONDS_PER_SAMPLE.value:
            #
            return self.player.get_miliseconds_per_sample()

        if cmd == TCPCommands.SET_MILLISECONDS_PER_SAMPLE.value:
            self.player.set_miliseconds_per_sample(args[0])
            return 0


        ### OLD
        # if cmd == TCPCommands.SET_POSITION.value:
        #     self.setPosition(float(args[0]))
        #     return 0
        #
        # if cmd == TCPCommands.OPEN_MOVIE.value:
        #     self.OpenFile(args[0])
        #     return 0
        #
        # if cmd == TCPCommands.DIRECTORY.value:
        #     self.Ping(args[0])
        #     return 0
        #
        # if cmd == TCPCommands.GET_DURATION.value:
        #     print "Get Duration"
        #     duration = self.get_duration()
        #     return duration
        #
        # if cmd == TCPCommands.GET_ASPECT_RATIO.value:
        #     ratio = self.get_aspect_ratio()
        #     return ratio
        #
        # if cmd == TCPCommands.GET_TIME_PER_FRAME.value:
        #     fps = self.get_fps()
        #     return fps
        #
        # if cmd == TCPCommands.GET_TIME.value:
        #     time = self.get_time()
        #     return time
        #
        # if cmd == TCPCommands.SET_TIME.value:
        #     self.set_time(args[0])
        #     return 0

    def parse_answer(self, answer):
        return str(answer) + "\n"

        # def parse_msg(self, msg=""):
        #     sep = ';'
        #     msg_split = msg.split(sep)
        #     cmd = int(msg_split[0])
        #     args = msg_split[1:len(msg_split)]
        #
        #     print TCPCommands(cmd), args
        #     if cmd == TCPCommands.PLAY.value:
        #         self.Play()
        #         return 0
        #
        #     if cmd == TCPCommands.PAUSE.value:
        #         self.Pause()
        #         return 0
        #
        #     if cmd == TCPCommands.STOP.value:
        #         print "Stop"
        #         return 0
        #
        #     if cmd == TCPCommands.SET_POSITION.value:
        #         self.setPosition(float(args[0]))
        #         return 0
        #
        #     if cmd == TCPCommands.OPEN_MOVIE.value:
        #         self.OpenFile(args[0])
        #         return 0
        #
        #     if cmd == TCPCommands.DIRECTORY.value:
        #         self.Ping(args[0])
        #         return 0
        #
        #     if cmd == TCPCommands.GET_DURATION.value:
        #         print "Get Duration"
        #         duration = self.get_duration()
        #         return duration
        #
        #     if cmd == TCPCommands.GET_ASPECT_RATIO.value:
        #         ratio = self.get_aspect_ratio()
        #         return ratio
        #
        #     if cmd == TCPCommands.GET_TIME_PER_FRAME.value:
        #         fps = self.get_fps()
        #         return fps
        #
        #     if cmd == TCPCommands.GET_TIME.value:
        #         time = self.get_time()
        #         return time
        #
        #     if cmd == TCPCommands.SET_TIME.value:
        #         self.set_time(args[0])
        #         return 0
    # OLD CODE
    # def PlayPause(self):
    #     """Toggle play/pause status
    #     """
    #     if self.vlc_player.is_playing():
    #         self.vlc_player.pause()
    #     else:
    #         if self.vlc_player.play() == -1:
    #             self.OpenFile()
    #             return
    #         self.vlc_player.play()
    #
    # def Play(self):
    #     if not self.vlc_player.is_playing():
    #         self.vlc_player.play()
    #
    # def Pause(self):
    #     if self.vlc_player.is_playing():
    #         self.vlc_player.pause()
    #
    # def setVolume(self, Volume):
    #     """Set the volume
    #     """
    #     self.vlc_player.audio_set_volume(Volume)
    #
    # def get_position(self):
    #     return self.vlc_player.get_position()
    #
    # def setPosition(self, position):
    #     """Set the position
    #     """
    #     # setting the position to where the slider was dragged
    #     self.vlc_player.set_position(position)
    #     # the vlc MediaPlayer needs a float value between 0 and 1, Qt
    #     # uses integer variables, so you need a factor; the higher the
    #     # factor, the more precise are the results
    #     # (1000 should be enough)
    #
    # def OpenFile(self, filename=None):
    #     """Open a media file in a MediaPlayer
    #     """
    #     if filename is None:
    #         filename = QtGui.QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'))
    #     if not filename:
    #         return
    #
    #     # create the media
    #     if sys.version < '3':
    #         filename = unicode(filename)
    #     self.media = self.instance.media_new(filename)
    #     # put the media in the media player
    #     self.vlc_player.set_media(self.media)
    #     self.media.parse()
    #     self.Play()
    #     time.sleep(0.5)
    #     self.Pause()
    #
    # def Ping(self, t1):
    #     t2 = datetime.now().microsecond
    #     print "Ping", t2-int(t1), "ms", t1, t2
    #
    #     # the media player has to be 'connected' to the QFrame
    #     # (otherwise a video would be displayed in it's own window)
    #     # this is platform specific!
    #     # you have to give the id of the QFrame (or similar object) to
    #     # vlc, different platforms have different functions for this
    #     # if sys.platform.startswith('linux'): # for Linux using the X Server
    #     #     self.vlc_player.set_xwindow(self.videoframe.winId())
    #     # elif sys.platform == "win32": # for Windows
    #     #     self.vlc_player.set_hwnd(self.videoframe.winId())
    #     # elif sys.platform == "darwin": # for MacOS
    #     #     self.vlc_player.set_nsobject(self.videoframe.winId())
    #     # self.PlayPause()
    #
    # def get_duration(self):
    #     return self.vlc_player.get_length()
    #
    # def get_aspect_ratio(self):
    #     ratio = self.vlc_player.video_get_aspect_ratio()
    #     print ratio
    #     return ratio
    #
    # def get_fps(self):
    #     fps = self.vlc_player.get_fps()
    #     print fps
    #     return fps
    #
    # def get_time(self):
    #     return self.vlc_player.get_time()
    #
    # def set_time(self, time_ms):
    #     time_ms = int(time_ms)
    #     self.vlc_player.set_time(time_ms)


class QServerHandler(QtCore.QThread):
    def __init__(self, player, connection, server):
        super(QServerHandler, self).__init__()
        self.player = player
        self.conn = connection
        self.server = server

    def run(self):
        while (self.server.active):
            try:
                data = self.conn.recv(self.server.BUFFER_SIZE)
                if not data: break
                ret = self.parse_msg(data)
                ret = self.parse_answer(ret)
                # print ret
                self.conn.send(ret)
            except IOError as e:
                self.conn.close()
                self.is_connected = False
                break

    def parse_msg(self, msg=""):
        try:
            sep = ';'
            msg_split = msg.split(sep)
            cmd = int(msg_split[0])
            args = msg_split[1:len(msg_split)]

            # print TCPCommands(cmd), args
            if cmd == TCPCommands.OPEN_MOVIE.value:
                self.player.open_movie(args[0], from_server =True)
                return 0

            if cmd == TCPCommands.PLAY.value:
                self.player.play()
                return 0

            if cmd == TCPCommands.PAUSE.value:
                self.player.pause()
                return 0

            if cmd == TCPCommands.STOP.value:
                self.player.stop()
                return 0

            if cmd == TCPCommands.IS_PLAYING.value:
                #
                return self.player.is_playing()

            if cmd == TCPCommands.PLAY_INTERVAL.value:
                self.player.play_interval(args[0], args[1])
                return 0

            if cmd == TCPCommands.SET_OFFSET.value:
                self.player.set_offset(args[0])
                return 0

            if cmd == TCPCommands.GET_OFFSET.value:
                #
                return self.player.get_offset()

            if cmd == TCPCommands.SET_STOP_TIME.value:
                self.player.set_stop_time(args[0])
                return 0

            if cmd == TCPCommands.NEXT_FRAME.value:
                self.player.next_frame()
                return 0

            if cmd == TCPCommands.PREVIOUS_FRAME.value:
                self.player.previous_frame()
                return 0

            if cmd == TCPCommands.SET_FRAME_STEPS_TO_FRAME_BEGIN.value:
                self.player.set_frame_steps_to_frame_begin(args[0])
                return 0

            if cmd == TCPCommands.SET_MEDIA_TIME.value:
                self.player.set_media_time(args[0])
                return 0

            if cmd == TCPCommands.GET_MEDIA_TIME.value:
                return self.player.get_media_time()

            if cmd == TCPCommands.SET_RATE.value:
                self.player.set_rate(args[0])
                return 0

            if cmd == TCPCommands.GET_RATE.value:
                return self.player.get_rate()

            if cmd == TCPCommands.IS_FRAME_AUTO_DETECTED.value:
                #
                return self.player.is_frame_rate_auto_detected()

            if cmd == TCPCommands.GET_MEDIA_DURATION.value:
                #
                return self.player.get_media_duration()

            if cmd == TCPCommands.SET_VOLUME.value:
                volume = int(self.to_float(args[0]) * 100)
                self.player.set_volume(volume)
                return 0

            if cmd == TCPCommands.GET_VOLUME.value:

                return float(self.player.get_volume())/100

            if cmd == TCPCommands.SET_SUB_VOLUME.value:
                volume = int(self.to_float(args[0]) * 100)
                self.player.set_sub_volume(volume)
                return 0

            if cmd == TCPCommands.GET_SUB_VOLUME.value:
                #
                return float(self.player.get_sub_volume())/100

            if cmd == TCPCommands.SET_MUTE.value:
                mute = self.to_bool(args[0])
                self.player.set_mute(mute)
                return 0

            if cmd == TCPCommands.GET_MUTE.value:
                #
                return self.player.get_mute()

            if cmd == TCPCommands.GET_SOURCE_WIDTH.value:
                #
                return self.player.get_source_width()

            if cmd == TCPCommands.GET_SOURCE_HEIGHT.value:
                #
                return self.player.get_source_height()

            if cmd == TCPCommands.GET_ASPECT_RATIO.value:
                #
                return self.player.get_aspect_ratio()

            if cmd == TCPCommands.SET_ASPECT_RATIO.value:
                self.player.set_aspect_ratio(args[0])
                return 0

            if cmd == TCPCommands.GET_MILLISECONDS_PER_SAMPLE.value:
                #
                return self.player.get_miliseconds_per_sample()

            if cmd == TCPCommands.SET_MILLISECONDS_PER_SAMPLE.value:
                self.player.set_miliseconds_per_sample(args[0])
                return 0

            if cmd == TCPCommands.CONNECT.value:
                return True
        except IOError:
            print "Command call Failed "

    def parse_answer(self, answer):
        return str(answer) + "\n"

    def to_float(self, string, default = 1.0):
        try:
            val = float(string)
        except ValueError:
            val = default
            print "ValueError, couldn't convert String to Float."
            print "Input: ", string
        return val

    def to_bool(self, string):
        if string == "false":
            return False
        else:
            return True


class QTServer(QtCore.QThread):
    def __init__(self, player):
        super(QTServer, self).__init__()
        self.player = player

        self.TCP_IP = '127.0.0.1'
        self.TCP_PORT = 5005
        self.BUFFER_SIZE = 1024
        self.active = True
        self.is_connected = False

        #Signals
        self.movieOpened = pyqtSignal()
        self.connectionChanged = pyqtSignal()

        self.handle_thread = None

    def run(self):
        while(True):
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.bind((self.TCP_IP, self.TCP_PORT))
            while self.active:
                self.listen()


    def quit(self):
        self.active = False
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.TCP_IP, self.TCP_PORT))


    def listen(self):


        self.s.listen(2)
        conn, addr = self.s.accept()

        if self.is_connected is False:
            self.is_connected = True
            self.handle_thread = QServerHandler(self.player, conn, self)
            self.handle_thread.start()
            print "Server:\t Connection Established"
        else:
            print "Server:\t Connection Denied"


        # self.is_connected = True
        # print 'Connection addres: ', addr
        # while (self.active):
        #     try:
        #         data = conn.recv(self.BUFFER_SIZE)
        #         if not data: break
        #         ret = self.parse_msg(data)
        #         ret = self.parse_answer(ret)
        #         # print ret
        #         conn.send(ret)
        #     except IOError as e:
        #         conn.close()
        #         self.is_connected = False
        #         break
        #
        # conn.close()
        # self.is_connected = False

    def parse_msg(self, msg=""):
        try:
            sep = ';'
            msg_split = msg.split(sep)
            cmd = int(msg_split[0])
            args = msg_split[1:len(msg_split)]

            # print TCPCommands(cmd), args
            if cmd == TCPCommands.OPEN_MOVIE.value:
                self.player.open_movie(args[0], from_server =True)
                return 0

            if cmd == TCPCommands.PLAY.value:
                self.player.play()
                return 0

            if cmd == TCPCommands.PAUSE.value:
                self.player.pause()
                return 0

            if cmd == TCPCommands.STOP.value:
                self.player.stop()
                return 0

            if cmd == TCPCommands.IS_PLAYING.value:
                #
                return self.player.is_playing()

            if cmd == TCPCommands.PLAY_INTERVAL.value:
                self.player.play_interval(args[0], args[1])
                return 0

            if cmd == TCPCommands.SET_OFFSET.value:
                self.player.set_offset(args[0])
                return 0

            if cmd == TCPCommands.GET_OFFSET.value:
                #
                return self.player.get_offset()

            if cmd == TCPCommands.SET_STOP_TIME.value:
                self.player.set_stop_time(args[0])
                return 0

            if cmd == TCPCommands.NEXT_FRAME.value:
                self.player.next_frame()
                return 0

            if cmd == TCPCommands.PREVIOUS_FRAME.value:
                self.player.previous_frame()
                return 0

            if cmd == TCPCommands.SET_FRAME_STEPS_TO_FRAME_BEGIN.value:
                self.player.set_frame_steps_to_frame_begin(args[0])
                return 0

            if cmd == TCPCommands.SET_MEDIA_TIME.value:
                self.player.set_media_time(args[0])
                return 0

            if cmd == TCPCommands.GET_MEDIA_TIME.value:
                return self.player.get_media_time()

            if cmd == TCPCommands.SET_RATE.value:
                self.player.set_rate(args[0])
                return 0

            if cmd == TCPCommands.GET_RATE.value:
                return self.player.get_rate()

            if cmd == TCPCommands.IS_FRAME_AUTO_DETECTED.value:
                #
                return self.player.is_frame_rate_auto_detected()

            if cmd == TCPCommands.GET_MEDIA_DURATION.value:
                #
                return self.player.get_media_duration()

            if cmd == TCPCommands.SET_VOLUME.value:
                volume = int(self.to_float(args[0]) * 100)
                self.player.set_volume(volume)
                return 0

            if cmd == TCPCommands.GET_VOLUME.value:

                return float(self.player.get_volume())/100

            if cmd == TCPCommands.SET_SUB_VOLUME.value:
                volume = int(self.to_float(args[0]) * 100)
                self.player.set_sub_volume(volume)
                return 0

            if cmd == TCPCommands.GET_SUB_VOLUME.value:
                #
                return float(self.player.get_sub_volume())/100

            if cmd == TCPCommands.SET_MUTE.value:
                mute = self.to_bool(args[0])
                self.player.set_mute(mute)
                return 0

            if cmd == TCPCommands.GET_MUTE.value:
                #
                return self.player.get_mute()

            if cmd == TCPCommands.GET_SOURCE_WIDTH.value:
                #
                return self.player.get_source_width()

            if cmd == TCPCommands.GET_SOURCE_HEIGHT.value:
                #
                return self.player.get_source_height()

            if cmd == TCPCommands.GET_ASPECT_RATIO.value:
                #
                return self.player.get_aspect_ratio()

            if cmd == TCPCommands.SET_ASPECT_RATIO.value:
                self.player.set_aspect_ratio(args[0])
                return 0

            if cmd == TCPCommands.GET_MILLISECONDS_PER_SAMPLE.value:
                #
                return self.player.get_miliseconds_per_sample()

            if cmd == TCPCommands.SET_MILLISECONDS_PER_SAMPLE.value:
                self.player.set_miliseconds_per_sample(args[0])
                return 0

            if cmd == TCPCommands.CONNECT.value:
                return True
        except IOError:
            print "Command call Failed "

    def parse_answer(self, answer):
        return str(answer) + "\n"

    def to_float(self, string, default = 1.0):
        try:
            val = float(string)
        except ValueError:
            val = default
            print "ValueError, couldn't convert String to Float."
            print "Input: ", string
        return val

    def to_bool(self, string):
        if string == "false":
            return False
        else:
            return True

