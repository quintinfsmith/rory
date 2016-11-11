''' Author: Quintin Smith '''
#!/usr/bin/python3
import sys
import threading
from Player import Player
from MidiInterpreter import MIDIInterpreter
from MIDIController import MIDIController
from Box import BoxEnvironment
from Interactor import Interactor

class Interface(BoxEnvironment, Interactor):
    '''Interface to Run the MidiPlayer'''
    def __init__(self):
        BoxEnvironment.__init__(self)
        Interactor.__init__(self)
        self.init_screen()
        self.midi_interpreter = MIDIInterpreter()
        self.active_threads = []
        self.interactorstack = []
        for y in range(self.height()):
            for x in range(self.width()):
                self.set(x, y, " ")

        self.listening = False
        self.assign_sequence("q", self.quit)
        self.player = None

    def show_player(self):
        '''Displays MidiPlayer Box'''
        player = Player()
        new_id = self.add_box(w=player.width(), h=player.height(), x=(self.width() - 90) // 2, y=0)
        self.boxes[new_id] = player
        player.parent = self
        player.id = new_id

        self.interactorstack.append(new_id)
        self.player = player

    def load_midi(self, midi_path):
        '''Load Midi Like Object from path'''
        return self.midi_interpreter(midi_path)

    def quit(self):
        '''shut it all down'''
        self.listening = False
        self.destroy()

    def play_along(self, selected_mlo, hidden=None):
        '''Run the Player with the loaded MidiLike Object'''
        if not hidden:
            hidden = list()
        thread = threading.Thread(target=self.player.play_along,\
          args=[selected_mlo, MIDIController(), hidden])
        thread.start()
        self.active_threads.append(thread)

    def input_loop(self):
        '''Main loop, just handles computer keyboard input'''
        self.listening = True
        while self.listening:
            while self.interactorstack:
                c = self.interactorstack.pop()
                if c in self.boxes.keys():
                    self.interactorstack.append(c)
                    active = self.boxes[c]
                    break

            if not self.interactorstack:
                active = self
                self.quit()
            active.get_input()

if __name__ == '__main__':
    sys.stdout.write("\033?25l")
    interface = Interface()
    midilike = interface.load_midi(sys.argv[1])
    note_range = midilike.get_note_range()
    interface.show_player()
    interface.play_along(midilike)
    interface.input_loop()
