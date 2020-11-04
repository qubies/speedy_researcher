#!/usr/bin/python3
import sys
import argparse
import time
import threading
import signal
import string
import textract
import os
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
import requests
import json

## server
PORT = 4969
IP = "34.83.200.130"
IP = "localhost"
signal.signal(signal.SIGINT, signal.SIG_DFL)

# STATE
line_position = 0
pause_status = False
pause_time = 0.3

AI_Pause_Factor = pause_time

# LIMITS
max_speed = 20000  # words per minute
min_speed = 30  # words per minute

common_words = set()
mode = "txt"

USER = ""


def get_login():
    pass


class span:
    def __init__(self, line, start, end):
        self.line = line
        self.char_start = start
        self.char_end = end

    def inside(self, line, char):
        return line == line and char >= self.char_start and char < self.char_end


# read in the word frequency file
for line in open("client/data/english_word_frequencies.txt"):
    common_words.add(line.split()[0])


def is_common(words):
    for word in words:
        word = word.strip(string.punctuation).lower()
        if word not in common_words:
            return False
    return True


def get_text(number):
    PARAMS = {"user": USER, "storyNumber": number}
    return requests.get(url=f"http://{IP}:{PORT}/text", params=PARAMS).json()


print(get_text(1))


def wpm_calc(t, num_words):
    return num_words / (t / 60)


class Record:
    def __init__(self, text, timing_info, comp_correct, comp_total):
        self.text = text
        # This is bad but should be fine...
        self.num_words = len(" ".join(text).split())
        self.timing_info = timing_info
        self.wpm = wpm_calc(timing_info, self.num_words)
        self.comp_correct = comp_correct
        self.comp_total = comp_total
        self.comp_score = comp_correct / comp_total
        self.wpm_ci = self.comp_score * self.wpm

    def __str__(self):
        return (
            f"WPM_ci: {self.wpm_ci:.2f} WPM_net: {self.wpm:.2f} Words: {self.num_words}"
        )

        def __repr__(self):
            return self.__str__()


def get_weights(n):
    return [1 / (n - (i - 1)) ** 2 for i in range(1, n + 1)]


#  print(get_weights(5))


class Timing:
    def __init__(self, what):
        self.start = time.perf_counter()
        self.what = what
        self.records = []

    def done_reading(self):
        self.reading_time = time.perf_counter() - self.start

    def record_result(self, text_name, comp_correct, comp_total):
        self.records.append(
            Record(text_name, self.reading_time, comp_correct, comp_total)
        )
        weights = get_weights(len(self.records))
        wpm_w = 0

        for rec, weight in zip(self.records, weights):
            print(rec)
            wpm_w += rec.wpm_ci * weight
        self.wpm_w = wpm_w / sum(weights)
        print(f"wpm_w: {self.wpm_w:.2f}")

    def reset(self):
        self.start = time.perf_counter()


class update(QRunnable):
    def __init__(self, data, main_window):
        self.main_window = main_window
        super(update, self).__init__()
        self.text = data["text"]
        self.AI_Spans = [span(x, y, z) for x, y, z in data["spans"]]
        threading.Thread.__init__(self)
        self.run = False

    def is_ai(self, line, char):
        if line in self.AI_Spans:
            for span in self.AI_Spans[line]:
                if span.inside(line, char):
                    return True
        return False

    def highlight_string(self, current_text, pos):
        """
        presents the document text, highlighting the current word in red
        """
        pre = " ".join(current_text[:pos])
        post = " ".join(current_text[pos + group_size :])
        current = " ".join(current_text[pos : pos + group_size])

        surround_style = "font-size:12pt; color:#666;"
        prior_style = "font-size:12pt; color:#DDD;"
        current_style = "font-size:15pt; color:#D00;"
        if mode == "pdf":
            prior_lines = "<br>".join(
                [
                    line.decode("utf-8")
                    for line in text[max(0, line_position - 3) : line_position]
                ]
            )
        else:
            prior_lines = "<br>".join(text[max(0, line_position - 3) : line_position])
        return f"<span style='{prior_style}'>{prior_lines}<br></span><span style='{surround_style}'>{pre}</span><span style='{current_style}'> {current} </span><span style='{surround_style}'>{post}</span>"

    @pyqtSlot()
    def run(self):

        # because these mix with the other thread they are left global
        global line_position
        global pause_status

        t = Timing("test")
        global space_state
        global lock

        while (
            line_position < len(self.text) and not self.main_window.event_stop.is_set()
        ):
            if USER == "":
                time.sleep(0.2)
                continue
            line_position = max(0, line_position)
            lp = line_position
            words = self.text[line_position].split()
            for i in range(0, len(words), group_size):
                if self.main_window.event_stop.is_set():
                    return
                word = " ".join(words[i : i + group_size])
                self.main_window.upcomming.setText(self.highlight_string(words, i))
                if lp != line_position:
                    break
                if not show_punctuation:
                    word = word.strip(string.punctuation)

                self.main_window.read.setText(word)

                while pause_status and not self.main_window.event_stop.is_set():
                    self.main_window.read.setText("PAUSED")
                    lock.acquire()

                AI_pause = 1.0  # nothing
                if self.is_ai(lp, i):
                    AI_pause = AI_Pause_Factor

                time.sleep(letter_boost * len(word) * AI_pause)
                if "," in word:
                    time.sleep(pause_time * comma_pause * AI_pause)
                elif any(x in word for x in [".", "!", "?", "...", ":", ";"]):
                    time.sleep(pause_time * period_pause * AI_pause)
                else:
                    time.sleep(pause_time * AI_pause)
                if not is_common(words[i : i + group_size]):
                    #  print(f"Uncommon: '{word}'")
                    time.sleep(uncommon * AI_pause)
            print(line_position)
            line_position += 1
        t.done_reading()
        if USER != "":
            t.record_result("a", 5, 5)
        #  t.record_result(4, 5)
        #  t.record_result(3, 5)
        self.main_window.close()


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login Form")
        self.resize(500, 120)

        layout = QGridLayout()

        label_name = QLabel('<font size="4"> Username </font>')
        self.lineEdit_username = QLineEdit()
        self.lineEdit_username.setPlaceholderText("Please enter your username")
        layout.addWidget(label_name, 0, 0)
        layout.addWidget(self.lineEdit_username, 0, 1)

        label_password = QLabel('<font size="4"> Password </font>')
        self.lineEdit_password = QLineEdit()
        self.lineEdit_password.setPlaceholderText("Please enter your password")
        layout.addWidget(label_password, 1, 0)
        layout.addWidget(self.lineEdit_password, 1, 1)

        button_login = QPushButton("Login")
        button_login.clicked.connect(self.check_password)
        layout.addWidget(button_login, 2, 0, 1, 2)
        layout.setRowMinimumHeight(2, 75)

        self.setLayout(layout)

    def closeEvent(self, event):
        if USER == "":
            main_window.event_stop.set()
        event.accept()

    def check_password(self):
        global USER
        USER = "user"
        self.close()
        return
        msg = QMessageBox()

        if (
            self.lineEdit_username.text() == "user"
            and self.lineEdit_password.text() == "pwd"
        ):
            USER = self.lineEdit_username.text()
            self.close()
        else:
            msg.setText("Incorrect Password")
            msg.exec_()


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.threadpool = QThreadPool()
        self.event_stop = threading.Event()
        ## gui layout options

        self.login()
        updater = update(data, self)
        self.threadpool.start(updater)
        upcomming_font = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
        read_font = QtGui.QFont("Times", font_size, QtGui.QFont.Bold)

        self.layout = QVBoxLayout()
        self.upcomming = QLabel("hat")
        self.upcomming.setFont(upcomming_font)
        self.upcomming.setTextFormat(Qt.RichText)
        self.upcomming.setWordWrap(True)
        self.upcomming.setText("")
        self.upcomming.setAlignment(Qt.AlignHCenter)

        self.read = QLabel("Welcome!!")
        self.read.setAlignment(Qt.AlignHCenter)
        self.read.setFont(read_font)

        self.setWindowTitle("Speed Reader")
        self.layout.addWidget(self.upcomming)
        self.layout.addWidget(self.read)
        self.setLayout(self.layout)

    def login(self):
        self.login = LoginWindow()
        self.login.setWindowModality(QtCore.Qt.ApplicationModal)
        self.login.show()

    def keyPressEvent(self, event):
        """
        keypress handlers
        """
        key = event.key()
        try:
            global speed
            global increment
            global line_position
            global pause_status
            global pause_time
            global run
            global lock

            if key == QtCore.Qt.Key_Up:
                speed = min(max_speed, speed + increment)
            elif key == QtCore.Qt.Key_Down:
                speed = max(speed - increment, min_speed)
            elif key == QtCore.Qt.Key_Space:

                # grab lock to pause, or if already paused release
                if lock.acquire(False):
                    pass
                else:
                    lock.release()
                    pause_status = not pause_status
            elif key == QtCore.Qt.Key_Left:
                line_position -= 1
            elif key == QtCore.Qt.Key_Right:
                line_position += 1
            elif key == QtCore.Qt.Key_Escape:
                self.event_stop.set()
                self.close()
            pause_time = wpm_to_seconds(speed) * group_size

        except AttributeError:
            return


def wpm_to_seconds(x):
    return 1 / (x / 60)


lock = threading.Semaphore(1)


def set_args():
    global lock
    global speed  # = 0.3
    global increment  # = 0.05
    global font_size  # = 60
    global file_name
    global show_punctuation  # = True
    global comma_pause  # = 1
    global period_pause  # = 2
    global pause_time
    global letter_boost
    global uncommon
    global group_size
    global AI_Pause_Factor

    parser = argparse.ArgumentParser()

    # options
    parser.add_argument(
        "--speed",
        type=int,
        default=250,
        help="The base speed for the reader in words per minute -- default=180",
    )
    parser.add_argument(
        "--increment",
        type=int,
        default=2,
        help="The increment increase in words per minute -- default=2",
    )
    parser.add_argument(
        "--font_size", type=int, default=48, help="The font size -- default=48"
    )
    parser.add_argument(
        "--comma_pause",
        type=int,
        default=1,
        help="The amount of time to pause for a comma after a word -- default=1",
    )
    parser.add_argument(
        "--period_pause",
        type=int,
        default=2,
        help="The amount of time to pause for a period after a word -- default=2",
    )
    parser.add_argument(
        "--letter_boost",
        type=float,
        default=0.001,
        help="The amount of time to increase the pause for each letter in a word -- default=0.01",
    )
    parser.add_argument(
        "--AI_pause",
        type=float,
        default=2.0,
        help="The amount of time to increase the pause for AI highlight spans -- default=2.0",
    )
    parser.add_argument(
        "--uncommon",
        type=float,
        default=0.2,
        help="The amount of time to increase the pause for each uncommon word -- default=0.2",
    )
    parser.add_argument(
        "--hide_punctuation",
        help="Remove trailing punctuation from words displayed",
        action="store_true",
    )
    parser.add_argument(
        "--group_size",
        type=int,
        default=1,
        help="The number of words displayed as a group",
    )

    args = parser.parse_args()

    speed = args.speed
    pause_time = wpm_to_seconds(speed)
    increment = wpm_to_seconds(args.increment)
    font_size = args.font_size
    comma_pause = args.comma_pause
    period_pause = args.period_pause
    show_punctuation = not args.hide_punctuation
    letter_boost = args.letter_boost
    uncommon = args.uncommon
    group_size = args.group_size
    AI_Pause_Factor = args.AI_pause


set_args()

story_number = 0
data = get_text(story_number)
text = data["text"]
print(data)

app = QApplication(sys.argv)

main_window = MainWindow()
main_window.show()

## run on the text

exit_code = app.exec_()
#  updater.join()
sys.exit(exit_code)
