# Rory
Learn Piano using MIDI files and a MIDI Keyboard<br/>
![Travis (.com)](https://img.shields.io/travis/com/quintinfsmith/rory?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dw/rory?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/rory?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/rory?style=flat-square)

## Installation
```bash
pip install rory
```

## Usage
```bash
rory path/to/midi.mid
```
The song will only scroll upon hitting the correct key combinations.
*indicators*
- red: 'wrong note'
- green: 'correct note', but there are others needed
- orange: 'correct note' but you need to release and press again.

### Controls
'q': Quit<br/>
'j': Next State<br/>
'k': Previous state<br/>
'[': set loop start<br/>
']': set loop end<br/>
'/': stop looping<br/>
[number] 'p': jump to state [number]<br/>

### Notes
- Terminal needs to be 90+ characters wide.
- I've generated some scale excercises in scales/*.mid

