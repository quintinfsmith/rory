'''Interface between user and player'''

import os
import sys
import json
import threading
from Player import Player
from Box import BoxEnvironment
from Interactor import RegisteredInteractor
from MidiLib.MidiInterpreter import MIDIInterpreter
from MidiLib.MIDIController import MIDIController
#from Recorder import Recorder

class Interface(BoxEnvironment, RegisteredInteractor):
    '''Interface to Run the MidiPlayer'''
    def __init__(self):
        BoxEnvironment.__init__(self)
        RegisteredInteractor.__init__(self)
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

    def load_midi(self, midi_path):
        '''Load Midi Like Object from path'''
        return self.midi_interpreter(midi_path)

    def quit(self):
        '''shut it all down'''
        self.listening = False
        self.destroy()

    def play_along(self, midi_path, hidden=None):
        '''Run the Player with the loaded MidiLike Object'''
        if not hidden:
            hidden = list()

        selected_mlo = self.load_midi(midi_path)

        thread = threading.Thread(target=self.player.play_along,\
          args=[selected_mlo, MIDIController(self.midi_controller_path)])
        thread.start()
        self.active_threads.append(thread)

    # Record doesn't exist yet
    #def record(self):
    #    recorder = Recorder()
    #    new_id = self.add_box(w=recorder.width(), h=player.height(), x = (self.width() - 90) // 2, y = 0)
    #    self.boxes[new_id] = recorder
    #    recorder.parent = self
    #    recorder.id = new_id

    #    self.interactorstack.append(new_id)
    #    self.recorder = recorder

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
