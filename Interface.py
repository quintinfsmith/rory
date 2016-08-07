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

        self.listening = False

        self.assign_sequence("q", self.quit)


    def show_player(self):
        player = Player()
        player.parent = self
        new_id = self.id_gen
        self.id_gen += 1
        self.boxes[new_id] = player
        w = console.getTerminalSize()[0]
        self.box_positions[new_id] = ((w - 129) // 2,1)
        self.player = player


    def toggle_track(self):
        self.player.toggle_trackn(self.general_register)
        self.clear_register()

    def load_midi(self, midi_path):
        midilike = self.midi_interpreter(midi_path)
        return midilike

    def quit(self):
        self.listening = False
        self.player.quit()
        self.destroy()

    def play_along(self, midilike, hidden=[]):
        thread = threading.Thread(target=self.player.play_along, args=[midilike, MIDIController(), hidden])
        thread.start()
        self.active_threads.append(thread)

    def input_loop(self):
        self.listening = True
        while self.listening:
            if self.player and self.player.playing: #Kludge
                self.player.get_input()
            else:
                self.get_input()

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
