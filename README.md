# misophonia
Learn Piano using MIDI files

Requirements:
  Unix like OS
  Python 3
  
Usage: ./main.py <midifile>

Controls:
  q - quit
  j - Next State
  k - Previous state
  [ - set loop start
  ] - set loop end
  / - clear loop
  <n> p - jump to state <n>

Notes:
  You may need to modify MIDIController.py to choose your midi device.
  The Midi Library I created is incomplete, so not every midi will be read perfectly, though any I've used have worked without issue.
  
