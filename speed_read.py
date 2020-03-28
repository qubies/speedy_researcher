#!/usr/bin/python3
import sys, argparse, time, threading, signal, string
import textract as t
from pynput.keyboard import Key, Listener
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

## DEFAULTS
speed = 0.3
increment = 0.05
font_size = 60
show_punctuation = True
comma_pause = 1
period_pause = 2
max_speed = 1000 # words per minute
min_speed = 30 # words per minute

## state
line_position = 0
running_threads = []
space_state = False
pause_time = 0.3

class update(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

    def run(self):

        while not self.shutdown_flag.is_set():
            global text
            global mw
            global line_position
            global space_state

            while line_position < len(text):
                for word in text[line_position].split():
                    if self.shutdown_flag.is_set(): 
                        print('Thread #%s stopped' % self.ident)
                        return
                    if show_punctuation:
                        w = word.decode()
                    else:
                        w = word.decode().rstrip(string.punctuation)
                    mw.label.setText(w)
                    time.sleep(pause_time)

                    while space_state and not self.shutdown_flag.is_set():
                        mw.label.setText("PAUSED")
                        time.sleep(0.5)
                    
                    if b',' in word:
                        time.sleep(pause_time*comma_pause)
                    elif b'.' in word:
                        time.sleep(pause_time*period_pause)
                line_position+=1



class ServiceExit(Exception):
    def __init__(self, *args):
        for instance in args:
            print("Instance Closing", instance)
            instance.shutdown_flag.set()


def service_shutdown(signum, frame):
    raise ServiceExit(*running_threads)


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setStyleSheet("QLabel {font: "+str(font_size)+"pt}")
        self.layout = QVBoxLayout()
        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.label)
        self.setWindowTitle("Speed Reader")
        self.setLayout(self.layout)


def on_press(key):
    try:
        global speed
        global increment
        global line_position
        global space_state
        global pause_time

        if key == key.up:
            speed = min(max_speed, speed+increment)
        elif key == key.down:
            speed = max(speed-increment, min_speed)
        elif key == key.space:
            space_state = not space_state
        elif key == key.left:
            line_position -= 1
        pause_time = wpm_to_seconds(speed)
            
    except Exception as e:
        return

def wpm_to_seconds(x):
    return 1/(x/60)

def set_args():
    global speed # = 0.3
    global increment # = 0.05
    global font_size# = 60
    global file_name
    global show_punctuation# = True
    global comma_pause# = 1
    global period_pause # = 2
    global pause_time

    parser=argparse.ArgumentParser()
    parser.add_argument("file_name")

    ## options
    parser.add_argument('--speed', type=int, default=180, help='The base speed for the reader in words per minute -- default=180')
    parser.add_argument('--increment', type=int, default=2, help='The increment increase in words per minute -- default=2')
    parser.add_argument('--font_size', type=int, default=48, help='The font size -- default=48')
    parser.add_argument('--comma_pause', type=int, default=1, help='The amount of time to pause for a comma after a word -- default=1')
    parser.add_argument('--period_pause', type=int, default=2, help='The amount of time to pause for a period after a word -- default=2')
    parser.add_argument('--hide_punctuation', help="Remove trailing punctuation from words displayed", action='store_true')

    args = parser.parse_args()

    file_name = args.file_name
    speed = args.speed
    pause_time  = wpm_to_seconds(speed)
    increment = wpm_to_seconds(args.increment)
    font_size = args.font_size
    comma_pause = args.comma_pause
    period_pause = args.period_pause
    show_punctuation = not args.hide_punctuation

signal.signal(signal.SIGTERM, service_shutdown)
signal.signal(signal.SIGINT, service_shutdown)

set_args()
text = t.process(file_name).splitlines()
app = QApplication(list(sys.argv[0]))
mw = MainWindow()
mw.show()

with Listener(on_press=on_press) as listener:
    updater = update()
    running_threads = [updater]
    updater.start()

    exit_code = app.exec_()
    raise ServiceExit(*running_threads)
    listener.join()
updater.join()
sys.exit(exit_code)
