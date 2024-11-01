# Rory
Learn Piano using MIDI files and a MIDI Keyboard<br/>
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rory?style=flat-square)](https://pypi.org/project/rory/)
[![PyPI](https://img.shields.io/pypi/v/rory?style=flat-square)](https://pypi.org/project/rory/)
[![PyPI - License](https://img.shields.io/pypi/l/rory?style=flat-square)](https://burnsomni.net/project/rory/?branch=master&path=LICENSE)

<!--img src="https://raw.githubusercontent.com/quintinfsmith/rory/master/res/sample.svg" /-->

## Installation
```bash
pip install rory
```

## Usage
```bash
rory path/to/midi.mid [-t steps_to_transpose]
```

The song will only scroll upon hitting the correct key combinations.
*indicators*
- red: 'wrong note'
- green: 'correct note', but there are others needed
- orange: 'correct note' but you need to release and press again.

### Controls
'q': Quit<br/>
'h': Bring up help window<br/>
'j': Next State<br/>
'k': Previous state<br/>
'[': set loop start<br/>
']': set loop end<br/>
'/': stop looping<br/>
[number] 'i': ignore channel [number]<br/>
[number] 'p': jump to state [number]<br/>

### Notes
- Terminal needs to be 106+ characters wide.
- I've generated some scale excercises in scales/*.mid

