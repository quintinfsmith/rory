'''Interface between user and player'''

import os
import sys
import json
import threading
from Player import Player
from Box import BoxEnvironment
from AsciiBox.src.Bleeps import BleepsScreen, BleepsBox
from Interactor import RegisteredInteractor
from MidiLib.MIDIController import MIDIController
#from Recorder import Recorder

class Interface(BleepsScreen, RegisteredInteractor):
    '''Interface to Run the MidiPlayer'''
    def __init__(self):
        BleepsScreen.__init__(self)
        RegisteredInteractor.__init__(self)
        self.active_threads = []
        self.interactorstack = []


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
        player_box = self.new_box(self.width, self.height)
        player = Player(player_box)

        self.interactorstack.append(player)
        self.player = player

    def save_settings(self):
        '''Save settings...'''
        with open(self.settings_path, "w") as fp:
            fp.write(json.dumps(self.settings))

    def load_midi(self, midi_path):
        '''Load Midi Like Object from path'''
        return MIDIInterpreter.parse_midi(midi_path)

    def quit(self):
        '''shut it all down'''
        self.listening = False
        self.kill()

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
            if self.interactorstack:
                active = self.interactorstack[-1]
                if not active.is_active:
                    self.interactorstack.pop()

            if not self.interactorstack:
                self.quit()

            if active.is_active:
                active.get_input()

