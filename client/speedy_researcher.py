#!/usr/bin/python3
import sys
import argparse
import time
from threading import Lock
import signal
import string
import textract
import os
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
import requests
import json

sys.settrace

## server
PORT = 4969
IP = "34.83.200.130"
IP_fallback = "localhost"
signal.signal(signal.SIGINT, signal.SIG_DFL)

# independent functions


# read in the word frequency file


def wpm_calc(t, num_words):
    return num_words / (t / 60)


# weighting function for time decay
def get_weights(n):
    return [1 / (n - (i - 1)) ** 2 for i in range(1, n + 1)]


def wpm_to_seconds(x):
    return 1 / (x / 60)


def login(username, password):
    return True


# classes


class span:
    def __init__(self, line, start, end):
        self.line = line
        self.char_start = start
        self.char_end = end

    def inside(self, line, char):
        return line == self.line and char >= self.char_start and char < self.char_end

    def __str__(self):
        return f"line: {self.line}, char_start: {self.char_start}, char_end: {self.char_end}"

    def __repr__(self):
        return self.__str__()


# maintains the records of the user
class Record:
    def __init__(self, text_name, text, timing_info, comp_correct, comp_total):
        self.text = text
        self.text_name = text_name
        # This is bad but should be fine...
        self.num_words = len(" ".join(text).split())
        self.timing_info = timing_info
        self.wpm = wpm_calc(timing_info, self.num_words)
        self.comp_correct = comp_correct
        self.comp_total = comp_total
        self.comp_score = comp_correct / comp_total
        self.wpm_ci = self.comp_score * self.wpm

    def __str__(self):
        return f"For text '{self.text_name}' WPM_ci: {self.wpm_ci:.2f} WPM_net: {self.wpm:.2f} Words: {self.num_words}"

        def __repr__(self):
            return self.__str__()


# class determines the timing scores of the user
class Timing:
    def __init__(self, what):
        self.start = time.perf_counter()
        self.what = what
        self.records = []

    def done_reading(self):
        self.reading_time = time.perf_counter() - self.start

    def record_result(self, comp_correct, comp_total):
        self.records.append(
            Record(
                state.text_name, state.text, self.reading_time, comp_correct, comp_total
            )
        )
        weights = get_weights(len(self.records))
        wpm_w = 0

        for rec, weight in zip(self.records, weights):
            print(rec)
            wpm_w += rec.wpm_ci * weight
        self.wpm_w = wpm_w / sum(weights)

    def reset(self):
        self.start = time.perf_counter()


# the program flows through the state. Both the presenter and the main window thread use the state to determine their actions, and they both alter state.
class State:
    def __init__(
        self,
        speed=350,
        speed_increment=25,
        font_size=60,
        show_punctuation=True,
        comma_boost=1.5,
        period_boost=2.0,
        uncommon_boost=1.2,
        group_size=1,
        ai_boost=2.0,
        user="",
    ):
        self.line_position = 0
        self.killed = False
        self.present = False
        self.paused = False
        self.present_lock = Lock()
        self.present_lock.acquire()  # we start not presenting
        self.paused_lock = Lock()
        self.state_lock = Lock()
        self.speed = speed
        self.speed_increment = speed_increment
        self.base_pause_time = wpm_to_seconds(self.speed)
        self.font_size = font_size
        self.show_punctuation = True
        self.group_size = group_size
        self.comma_boost = comma_boost
        self.period_boost = period_boost
        self.uncommon_boost = uncommon_boost
        self.ai_boost = ai_boost
        self.max_speed = 20000  # words per minute
        self.min_speed = 30  # words per minute
        self.user = user
        self.text = None
        self.data = None
        self.common_words = set()
        for line in open("client/data/english_word_frequencies.txt"):
            self.common_words.add(line.split()[0])

    def are_any_uncommon(self, words):
        for word in words:
            word = word.strip(string.punctuation).lower()
            if word not in self.common_words:
                return True
        return False

    def get_next_data(self):
        with self.state_lock:
            self.story_number += 1
            PARAMS = {"user": self.user, "storyNumber": self.story_number}
            try:
                self.data = requests.get(
                    url=f"http://{IP}:{PORT}/text", params=PARAMS
                ).json()
            except:
                try:
                    self.data = requests.get(
                        url=f"http://{IP_fallback}:{PORT}/text", params=PARAMS
                    ).json()
                except:
                    print(
                        "Server cannot be contacted, please check to make sure its running"
                    )
                    exit(2)
            if self.data == "DONE":
                return False
            self.text = self.data["story"]
            self.AI_Spans = [span(x, y, z) for x, y, z in self.data["spans"]]
            self.text_name = self.data["story_name"]
            self.line_position = 0
            return True

    def set_user(self, user):
        with self.state_lock:
            self.user = user
            self.story_number = -1
        self.get_next_data()

    def incr_speed(self):
        with self.state_lock:
            p = self.speed
            self.speed += self.speed_increment
            self.speed = min(max(self.min_speed, self.speed), self.max_speed)
            self.base_pause_time = wpm_to_seconds(self.speed)

    def decr_speed(self):
        with self.state_lock:
            self.speed -= self.speed_increment
            self.speed = min(max(self.min_speed, self.speed), self.max_speed)
            self.base_pause_time = wpm_to_seconds(self.speed)

    def set_speed(self, n):
        with self.state_lock:
            self.speed = n
            self.base_pause_time = wpm_to_seconds(self.speed)

    def is_ai(self, char):
        for span in self.AI_Spans:
            if span.inside(self.line_position, char):
                return True
        return False

    def get_pause_time(self, words, char):
        word = "".join(words)
        with self.state_lock:
            base = self.base_pause_time
            if "," in word:
                base += self.comma_boost * self.base_pause_time
            if any(x in word for x in [".", "!", "?", "...", ":", ";"]):
                base += self.period_boost * self.base_pause_time
            if self.are_any_uncommon(words):
                base += self.uncommon_boost * self.base_pause_time
            if self.is_ai(char):
                base += self.ai_boost * self.base_pause_time
        return base

    def incr_line(self):
        with self.state_lock:
            self.line_position += 1

    def decr_line(self):
        with self.state_lock:
            self.line_position -= 1

    def set_line(self, n):
        with self.state_lock:
            self.line_position = max(0, n)

    def set_pause_time(self, n):
        with self.state_lock:
            self.pause_time = n

    def kill(self):
        self.killed = True

    def is_dead(self):
        with self.state_lock:
            return self.killed

    def pause(self):
        with self.state_lock:
            self.paused = True
            self.paused_lock.acquire()

    def unpause(self):
        with self.state_lock:
            self.paused = False
            self.paused_lock.release()

    def is_paused(self):
        with self.state_lock:
            return self.paused

    def should_present(self):
        with self.state_lock:
            return self.present

    def start_present(self):
        with self.state_lock:
            self.present_lock.release()
            self.present = True

    def stop_present(self):
        with self.state_lock:
            self.present_lock.acquire()
            self.present = False

    def is_running(self):
        return self.is_paused() and self.should_present()

    def force_run(self):
        self.start_present()
        self.unpause()

    def get_line(self):
        with self.state_lock:
            return self.text[self.line_position]


# the main presenter class
class present_story(QRunnable):
    def __init__(self, main_window):
        super(present_story, self).__init__()
        self.main_window = main_window

    def highlight_string(self, current_text, pos):
        """
        presents the document text, highlighting the current word in red
        """
        pre = " ".join(current_text[:pos])
        post = " ".join(current_text[pos + state.group_size :])
        current = " ".join(current_text[pos : pos + state.group_size])

        surround_style = "font-size:12pt; color:#666;"
        prior_style = "font-size:12pt; color:#DDD;"
        current_style = "font-size:15pt; color:#D00;"
        prior_lines = "<br>".join(
            state.text[max(0, state.line_position - 3) : state.line_position]
        )

        return f"<span style='{prior_style}'>{prior_lines}<br></span><span style='{surround_style}'>{pre}</span><span style='{current_style}'> {current} </span><span style='{surround_style}'>{post}</span>"

    @pyqtSlot()
    def run(self):

        t = Timing("test")

        while True:
            t.reset()
            with state.present_lock:
                while state.line_position < len(state.text) and not state.is_dead():
                    raw_text = state.get_line()
                    words = raw_text.split()
                    for i in range(0, len(words), state.group_size):
                        with state.paused_lock:
                            if state.is_dead():
                                return
                            word_group = words[i : i + state.group_size]
                            word = " ".join(word_group)
                            self.main_window.upcomming.setText(
                                self.highlight_string(words, i)
                            )

                            if not state.show_punctuation:
                                word = word.strip(string.punctuation)

                            self.main_window.read.setText(word)
                            pause_time = state.get_pause_time(word_group, i)
                            time.sleep(pause_time)
                    state.incr_line()
            t.done_reading()
            # this is where we present the test
            t.record_result(5, 5)
            if not state.get_next_data():
                state.kill()
                self.main_window.close()
                return

        state.kill()
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
        if state.user == "":
            state.kill()
        event.accept()

    def check_password(self):
        if login(self.lineEdit_username.text, self.lineEdit_password.text):
            state.set_user("user")
            #  state.set_user(self.lineEdit_username.text())
            state.start_present()
            self.close()
        else:
            msg = QMessageBox()
            msg.setText("Incorrect Password")
            msg.exec_()


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.threadpool = QThreadPool()
        self.login()
        self.presenter = present_story(self)
        self.threadpool.start(self.presenter)

        upcomming_font = QtGui.QFont("Times", 14, QtGui.QFont.Bold)
        read_font = QtGui.QFont("Times", state.font_size, QtGui.QFont.Bold)

        self.layout = QVBoxLayout()
        self.upcomming = QLabel("inbound")
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
            if key == QtCore.Qt.Key_Up:
                state.incr_speed()
            elif key == QtCore.Qt.Key_Down:
                state.decr_speed()
            elif key == QtCore.Qt.Key_Space:
                if state.is_paused():
                    state.unpause()
                else:
                    state.pause()
            elif key == QtCore.Qt.Key_Left:
                state.decr_line()
            elif key == QtCore.Qt.Key_Right:
                state.incr_line()
            elif key == QtCore.Qt.Key_Escape:
                state.kill()
                self.close()
        except AttributeError:
            return


state = State()
app = QApplication(sys.argv)

main_window = MainWindow()
main_window.show()

exit_code = app.exec_()
sys.exit(exit_code)
