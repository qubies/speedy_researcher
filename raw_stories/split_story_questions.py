import re
import os

def divide(filename):
    with open(filename, 'r', encoding='ISO-8859-1') as f:
        txt = f.read()
    comments = re.search("----*\n", txt)
    questions = re.search("\n1\.(.*\n)*2\.", txt)
    reading = txt[comments.span()[1]:questions.span()[0]]
    comprehension = txt[questions.span()[0]:]
    filenameroot = re.search("(.*)\.txt", filename).group(1)
    with open(filenameroot+".story", 'w', encoding='ISO-8859-1') as f:
        f.write(reading)

    with open(filenameroot+".questions", 'w', encoding='ISO-8859-1') as f:
        f.write(comprehension)
        
directory = '.'
for filename in os.listdir(directory):
    if filename.endswith(".txt"):
        print(filename)
        divide(filename)


