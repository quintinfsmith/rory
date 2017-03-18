# misophonia
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
    p - jump to start
    C - stop rechanneling  (see "#rechannel")
    :w - save file to "editted-filename.mid"
    s - quickjump (see "#quickjump")

    Register Commands ( type number, hit <cmd> )
    i - toggle channel visibility
    P - jump to state [number]
    S - set quickjump position (see "#quickjump)
    c - start rechanneling (see "#rechannel") 

#quickjump
    The user can save positions in the song to come back to later.
    Start by inputting the quickjump command, then select a character to act as the key, 
    example:
        "S" -> "1" @ position 456 in a song
        "s" -> "1" will jump me back to 456

#rechannel
    The User can rewrite the channel of notes to define left and right hands in a piece.
    Example
       1 -> "c"
       hold the notes which you wish to rechannel and press "next state". the keys will now show up in the color of channel 1.
        to stop. press "C"
       save by typing ":w", will be saved into "editted-<filename>.mid"

Notes:

    You may need to modify MIDIController.py to choose your midi device.
  
    The Midi Library I created is incomplete, so not every midi will be read perfectly, though any I've used have worked without issue.
  
    I've generated some scale excercises in scales/*.mid
  
