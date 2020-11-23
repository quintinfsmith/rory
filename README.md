#Rory
Learn Piano using MIDI files and a MIDI Keyboard

## Installation
```bash
pip install rory
```

## Usage
```bash
rory path/to/midi.mid
```
The song will only scroll upon hitting the correct key combinations.
red: 'wrong note'
green: 'correct note', but there are others needed
orange: 'correct note' but you need to release and press again.

### Controls
'q': Quit
'j': Next State
'k': Previous state
'[': set loop start
']': set loop end
'/': stop looping
<number> 'p': jump to state [number]

### Notes
-Terminal needs to be 90+ characters wide.
-I've generated some scale excercises in scales/*.mid

