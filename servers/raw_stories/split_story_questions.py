import re
import os
from spacy.lang.en import English


def divide(filename):
    with open(filename, 'r', encoding='ISO-8859-1') as f:
        txt = f.read()
    comments = re.search("----*\n", txt)
    questions = re.search("\n1\.(.*\n)*2\.", txt)
    reading = txt[comments.span()[1]:questions.span()[0]]
    comprehension = txt[questions.span()[0]:]
    filenameroot = re.search("(.*)\.txt", filename).group(1)

    make_lines(reading, filenameroot+".story")
    make_lines(comprehension, filenameroot+".questions")

def make_lines(text, filename):
    nlp = English()
    nlp.add_pipe(nlp.create_pipe('sentencizer'))
    doc = nlp(text)
    sentences = [sent.string.strip() for sent in doc.sents]
    print('saving {filename')
    with open(filename, 'w', encoding='ISO-8859-1') as f:
        for s in sentences:
            f.write(s+"\n")

directory = '.'
for filename in os.listdir(directory):
    if filename.endswith(".txt"):
        divide(filename)


