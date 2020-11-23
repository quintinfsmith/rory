# Rory
Learn Piano using MIDI files and a MIDI Keyboard

## Installation
```bash
sudo pip install rory
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

