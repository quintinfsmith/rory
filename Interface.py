import json
import threading
import os
from MIDILike import *
from Player import Player
from MidiInterpreter import MIDIInterpreter
from MIDIController import *
from Box import BoxEnvironment, Box
from Interactor import Interactor

class Interface(BoxEnvironment, Interactor):
    def __init__(self, cache_path='.cache.json'):
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

    def show_player(self):
        player = Player()
        player.parent = self
        new_id = self.id_gen
        player.id = new_id
        self.id_gen += 1
        self.interactorstack.append(new_id)
        self.boxes[new_id] = player
        self.box_positions[new_id] = ((self.width() - 130) // 2,0)
        self.player = player

    def toggle_track(self):
        self.player.toggle_trackn(self.general_register)
        self.clear_register()

    def load_midi(self, midi_path):
        midilike = self.midi_interpreter(midi_path)
        return midilike

    def quit(self):
        self.listening = False
        self.destroy()

    def play_along(self, midilike, hidden=[]):
        thread = threading.Thread(target=self.player.play_along, args=[midilike, MIDIController(), hidden])
        thread.start()
        self.active_threads.append(thread)

    def input_loop(self):
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
            active.get_input()

import sys
import console
if __name__ == '__main__':
    sys.stdout.write("\033?25l")
    interface = Interface()
    midilike = interface.load_midi(sys.argv[1])
    note_range = midilike.get_note_range()
    interface.show_player()
    interface.play_along(midilike)
    interface.input_loop()
