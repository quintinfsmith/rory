'''Interface between user and player'''
import os
import sys
import threading
import time
from Player import Player
from wrecked import RectStage
from Interactor import Interactor
from MIDIController import MIDIController


class Top(RectStage):
    '''Interface to Run the MidiPlayer'''
    CONTEXT_DEFAULT = 0
    CONTEXT_PLAYER = 1
    def __init__(self):
        super().__init__()
        self.interactor = Interactor()
        self.midi_controller_path = "/dev/midi1"
        self.midi_controller = MIDIController(self.midi_controller_path)
        self.interactor.assign_context_sequence(
            self.CONTEXT_DEFAULT,
            'q',
            self.kill
        )

        self.running = True
        self.player = None
        self.set_fps(24)

        thread = threading.Thread(target=self._input_daemon)
        thread.start()

    def play_along(self, midi_path):
        '''Run the Player with the loaded MidiLike Object'''

        if not self.player:
            self.player = self.create_scene(self.CONTEXT_PLAYER, Player,
                path=midi_path,
                controller=self.midi_controller
            )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'j',
            self.player.next_state
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'k',
            self.player.prev_state
        )

        for n in range(10):
            self.interactor.assign_context_sequence(
                self.CONTEXT_PLAYER,
                str(n),
                self.player.set_register_digit,
                n
            )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'p',
            self.player.jump_to_register_position,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            '[',
            self.player.set_loop_start_to_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            ']',
            self.player.set_loop_end_to_position,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'q',
            self.kill
        )

        self.interactor.set_context(self.CONTEXT_PLAYER)

        self.start_scene(self.CONTEXT_PLAYER)


    def _input_daemon(self):
        '''Main loop, just handles computer keyboard input'''
        while self.running:
            self.interactor.get_input()

    def kill(self):
        '''shut it all down'''
        self.running = False
        self.midi_controller.close()
        super().kill()

