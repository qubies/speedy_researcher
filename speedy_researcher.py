#!/usr/bin/python3
import sys
import argparse
import time
import threading
import signal
import string
import textract
import os
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QMessageBox
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

should_run = True

signal.signal(signal.SIGINT, signal.SIG_DFL)

# STATE
running_threads = []
line_position = 0
pause_status = False
pause_time = 0.3

AI_Pause_Factor = pause_time

# LIMITS
max_speed = 20000  # words per minute
min_speed = 30  # words per minute

common_words = set()
mode = "txt"


class span:
    def __init__(self, line, start, end):
        self.line = line
        self.char_start = start
        self.char_end = end

    def inside(self, line, char):
        return line == line and char >= self.char_start and char < self.char_end


# read in the word frequency file
for line in open("data/english_word_frequencies.txt"):
    common_words.add(line.split()[0])


def is_common(words):
    for word in words:
        word = word.strip(string.punctuation).lower()
        if word not in common_words:
            return False
    return True


def extractive_spans(lines):
    return []


def QA_spans(lines):
    return [span(2, 7, 15), span(10, 1, 100)]


def get_spans(lines):
    AI_Spans = {}
    for span in QA_spans(text) + extractive_spans(text):
        if span.line not in AI_Spans:
            AI_Spans[span.line] = []
        AI_Spans[span.line].append(span)
    return AI_Spans


def wpm_calc(t, num_words):
    return num_words / (t / 60)


class Record:
    def __init__(self, text, timing_info):
        self.text = text
        # This is bad but should be fine...
        self.num_words = len(" ".join(text).split())
        self.timing_info = timing_info
        self.wpm = wpm_calc(timing_info, self.num_words)

    def __str__(self):
        return f"WPM_net: {self.wpm:.2f} Words: {self.num_words}"

    def __repr__(self):
        return self.__str__()


class Timing:
    def __init__(self, what):
        self.start = time.perf_counter()
        self.what = what
        self.records = []

    def report(self):
        elapsed_time = time.perf_counter() - self.start
        self.records.append(Record(text, elapsed_time))
        for rec in self.records:
            print(rec)

    def reset(self):
        self.start = time.perf_counter()


class update(threading.Thread):
    def __init__(self, text):
        self.text = text
        self.AI_Spans = get_spans(self.text)
        threading.Thread.__init__(self)

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

    def run(self):
        global main_window

        # because these mix with the other thread they are left global
        global line_position
        global pause_status

        t = Timing("test")

        while line_position < len(text):
            line_position = max(0, line_position)
            lp = line_position
            if mode == "pdf":
                words = self.text[line_position].decode("utf-8").split()
            else:
                words = self.text[line_position].split()
            for i in range(0, len(words), group_size):
                word = " ".join(words[i : i + group_size])
                main_window.upcomming.setText(self.highlight_string(words, i))
                if lp != line_position:
                    break
                if not should_run:
                    return
                if not show_punctuation:
                    word = word.strip(string.punctuation)

                main_window.read.setText(word)

                while pause_status and should_run:
                    main_window.read.setText("PAUSED")
                    time.sleep(0.5)

                AI_pause = 1.0  # nothing
                if self.is_ai(lp, i):
                    AI_pause = AI_Pause_Factor

                time.sleep(letter_boost * len(word) * AI_pause)
                if "," in word:
                    time.sleep(pause_time * comma_pause * AI_pause)
                elif "." in word:
                    time.sleep(pause_time * period_pause * AI_pause)
                else:
                    time.sleep(pause_time * AI_pause)
                if not is_common(words[i : i + group_size]):
                    print(f"Uncommon: '{word}'")
                    time.sleep(uncommon * AI_pause)
            else:
                line_position += 1
        t.report()
        main_window.close()


class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        ## gui layout options
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
            global should_run

            if key == QtCore.Qt.Key_Up:
                speed = min(max_speed, speed + increment)
            elif key == QtCore.Qt.Key_Down:
                speed = max(speed - increment, min_speed)
            elif key == QtCore.Qt.Key_Space:
                pause_status = not pause_status
            elif key == QtCore.Qt.Key_Left:
                line_position -= 1
            elif key == QtCore.Qt.Key_Right:
                line_position += 1
            elif key == QtCore.Qt.Key_Escape:
                should_run = False
                self.close()
            pause_time = wpm_to_seconds(speed) * group_size

        except AttributeError:
            return


def wpm_to_seconds(x):
    return 1 / (x / 60)


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
    global uncommon
    global group_size
    global AI_Pause_Factor

    parser = argparse.ArgumentParser()
    parser.add_argument("file_name")

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

    file_name = args.file_name
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


_, extension = os.path.splitext(file_name)
if extension[-3:] == "pdf":
    mode = "pdf"
    text = textract.process(file_name).splitlines()
else:
    with open(file_name) as f:
        text = f.readlines()

app = QApplication(list(sys.argv[0]))
main_window = MainWindow()
main_window.show()

## run on the text
updater = update(text)
updater.start()

exit_code = app.exec_()
updater.join()
sys.exit(exit_code)
