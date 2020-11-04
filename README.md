# Speedy Researcher

Displays one word at a time from a pdf, with text line positioning at the top
![gui_image](https://raw.githubusercontent.com/qubies/speedy_researcher/master/data/images/running_screen.png "Speedy Researcher In Action")

# Dependancies
* pyqt5 
* textract

# Installation
```
git clone https://github.com/qubies/speedy_researcher.git
cd speedy_researcher
pip install --user -r requirements.txt
```

## Controls
* Up Arrow -> increase speed
* Down Arrow -> decrease speed
* Left -> Go back to previous line
* Right -> Go to next line
* Space -> Toggle Pause

### CLI Options
```
usage: speedy_researcher.py [-h] [--speed SPEED] [--increment INCREMENT]
                     [--font_size FONT_SIZE] [--comma_pause COMMA_PAUSE]
                     [--period_pause PERIOD_PAUSE]
                     [--letter_boost LETTER_BOOST] [--uncommon UNCOMMON]
                     [--hide_punctuation]
                     file_name

positional arguments:
  file_name

optional arguments:
  -h, --help            show this help message and exit
  --speed SPEED         The base speed for the reader in words per minute --
                        default=180
  --increment INCREMENT
                        The increment increase in words per minute --
                        default=2
  --font_size FONT_SIZE
                        The font size -- default=48
  --comma_pause COMMA_PAUSE
                        The amount of time to pause for a comma after a word
                        -- default=1
  --period_pause PERIOD_PAUSE
                        The amount of time to pause for a period after a word
                        -- default=2
  --letter_boost LETTER_BOOST
                        The amount of time to increase the pause for each
                        letter in a word -- default=0.01
  --uncommon UNCOMMON   The amount of time to increase the pause for each
                        uncommon word -- default=0.2
  --hide_punctuation    Remove trailing punctuation from words displayed
```
