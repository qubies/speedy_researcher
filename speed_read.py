#!/usr/bin/python3
import sys
import argparse
import time
import threading
import signal
import string
import textract as t
from pynput.keyboard import Key, Listener
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

# STATE
running_threads = []
line_position = 0
space_state = False
pause_time = 0.3

# LIMITS
max_speed = 1000  # words per minute
min_speed = 30  # words per minute


class update(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.shutdown_flag = threading.Event()

    def highlight_string(self, current_text, pos):
        pre = " ".join(current_text[:pos])
        post = " ".join(current_text[pos+1:])
        current = current_text[pos]
        surround_style = "font-size:12pt; color:#666;"
        prior_style = "font-size:12pt; color:#DDD;"
        current_style = "font-size:15pt; color:#D00;"
        prior_lines = "<br>".join([line.decode('utf-8')
                                   for line in text[max(0,line_position-3):line_position]])
        return f"<span style='{prior_style}'>{prior_lines}<br></span><span style='{surround_style}'>{pre}</span><span style='{current_style}'> {current} </span><span style='{surround_style}'>{post}</span>"

    def run(self):
        while not self.shutdown_flag.is_set():
            global text
            global mw
            global line_position
            global space_state
            while line_position < len(text):
                lp = line_position
                words = text[line_position].decode('utf-8').split()
                for i, word in enumerate(words):
                    mw.upcomming.setText(self.highlight_string(words, i))
                    if lp != line_position:
                        break
                    if self.shutdown_flag.is_set():
                        print('Thread #%s stopped' % self.ident)
                        return
                    if not show_punctuation:
                        word = word.strip(string.punctuation)

                    mw.read.setText(word)

                    while space_state and not self.shutdown_flag.is_set():
                        mw.read.setText("PAUSED")
                        time.sleep(0.5)

                    sys.stdout.flush()
                    time.sleep(letter_boost*len(word))
                    if ',' in word:
                        time.sleep(pause_time*comma_pause)
                    elif '.' in word:
                        time.sleep(pause_time*period_pause)
                    else:
                        time.sleep(pause_time)
                else:
                    line_position += 1


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
        #  self.setStyleSheet("QLabel {font: "+str(font_size)+"pt}")
        upcomming_font = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
        read_font = QtGui.QFont("Times", font_size, QtGui.QFont.Bold)

        self.layout = QVBoxLayout()
        self.upcomming = QLabel("hat")
        self.upcomming.setFont(upcomming_font)
        self.upcomming.setTextFormat(Qt.RichText)
        self.upcomming.setWordWrap(True)
        self.upcomming.setText("")
        self.upcomming.setAlignment(Qt.AlignHCenter)

        self.read = QLabel("LINE")
        self.read.setAlignment(Qt.AlignHCenter)
        self.read.setFont(read_font)

        self.setWindowTitle("Speed Reader")
        self.layout.addWidget(self.upcomming)
        self.layout.addWidget(self.read)
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
        elif key == key.right:
            line_position += 1
        pause_time = wpm_to_seconds(speed)

    except Exception as e:
        return


def wpm_to_seconds(x):
    return 1/(x/60)


def set_args():
    global speed  # = 0.3
    global increment  # = 0.05
    global font_size  # = 60
    global file_name
    global show_punctuation  # = True
    global comma_pause  # = 1
    global period_pause  # = 2
    global pause_time
    global letter_boost

    parser = argparse.ArgumentParser()
    parser.add_argument("file_name")

    # options
    parser.add_argument('--speed', type=int, default=250,
                        help='The base speed for the reader in words per minute -- default=180')
    parser.add_argument('--increment', type=int, default=2,
                        help='The increment increase in words per minute -- default=2')
    parser.add_argument('--font_size', type=int, default=48,
                        help='The font size -- default=48')
    parser.add_argument('--comma_pause', type=int, default=1,
                        help='The amount of time to pause for a comma after a word -- default=1')
    parser.add_argument('--period_pause', type=int, default=2,
                        help='The amount of time to pause for a period after a word -- default=2')
    parser.add_argument('--letter_boost', type=float, default=0.02,
                        help='The amount of time to increase the pause for each letter in a word -- default=0.02')
    parser.add_argument(
        '--hide_punctuation', help="Remove trailing punctuation from words displayed", action='store_true')

    args = parser.parse_args()

    file_name = args.file_name
    speed = args.speed
    pause_time = wpm_to_seconds(speed)
    increment = wpm_to_seconds(args.increment)
    font_size = args.font_size
    comma_pause = args.comma_pause
    period_pause = args.period_pause
    show_punctuation = not args.hide_punctuation
    letter_boost = args.letter_boost


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
