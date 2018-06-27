'''Interface between user and player'''

import os
import sys
import json
import threading
from Player import Player
from Box import BoxEnvironment
from Interactor import RegisteredInteractor
from MidiLib.MIDIController import MIDIController
#from Recorder import Recorder

class Interface(BoxEnvironment, RegisteredInteractor):
    '''Interface to Run the MidiPlayer'''
    def __init__(self):
        BoxEnvironment.__init__(self)
        RegisteredInteractor.__init__(self)
        self.init_screen()
        self.active_threads = []
        self.interactorstack = []
        x_a = (self.width() - 90) // 2
        x_b = (self.width() + 90) // 2
        for y in range(self.height()):
            for x in range(self.width()):
                if x < x_a or x >= x_b:
                    self.set(x, y, "\033[47m \033[40m")
                else:
                    self.set(x, y, " ")

        self.listening = False
        self.assign_sequence("q", self.quit)
        self.player = None
        self.midi_controller_path = "/dev/midi1"
        self.settings_path = "./settings.json"
        if os.path.isfile(self.settings_path):
            with open(self.settings_path, "r") as fp:
                self.settings = json.loads(fp.read())
        else:
            self.settings = {}

    def set_midicontroller_path(self, path):
        '''Use a different Midi Input Device'''
        self.midi_controller_path = path

    def show_player(self):
        '''Displays MidiPlayer Box'''
        player = Player()
        new_id = self.add_box(w=player.width(), h=player.height(), x=(self.width() - 90) // 2, y=0)
        self.boxes[new_id] = player
        player.parent = self
        player.id = new_id

        self.interactorstack.append(new_id)
        self.player = player

    def save_settings(self):
        '''Save settings...'''
        with open(self.settings_path, "w") as fp:
            fp.write(json.dumps(self.settings))

    def quit(self):
        '''shut it all down'''
        self.listening = False
        self.destroy()

    def play_along(self, midi_path, hidden=None):
        '''Run the Player with the loaded MidiLike Object'''
        if not hidden:
            hidden = list()

        thread = threading.Thread(target=self.player.play_along,\
          args=[midi_path, MIDIController(self.midi_controller_path)])
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
                #active = self
                self.quit()
            active.get_input()
