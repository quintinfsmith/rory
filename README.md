Learn Piano using MIDI files and a MIDI Keyboard

Requirements:

      Unix like OS
      Python 3

      Some way of connecting your MIDI keyboard (or any MIDI instrument) to your computer


Usage: 1: ensure your console is at least 90 chacters wide
       2: $ ./main.py \<midifile\>

Controls:
    q - quit
    j - Next State
    k - Previous state
    [ - set loop start
    ] - set loop end
    / - break loop

    Register Commands ( type number, hit <cmd> )
    i - toggle channel visibility
    p - jump to state [number]

Notes:
    You may need to modify MIDIController.py to choose your midi device.

    The Midi Library I created is incomplete, so not every midi will be read perfectly, though any I've used have worked without issue.

    I've generated some scale excercises in scales/*.mid
