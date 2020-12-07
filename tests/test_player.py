import unittest
import time
import os
import apres

from rory.player import Player
from rory.midicontroller import MIDIController

class PlayerTest(unittest.TestCase):
    def setUp(self):
        self.original_devroot = MIDIController.DEVROOT
        MIDIController.DEVROOT = 'testdev/'
        try:
            os.mkdir('testdev')
        except: pass

        self.test_midi = apres.MIDI()
        for i in range(12):
            note_on = apres.NoteOn(note=64 + i, velocity=100, channel=0)
            note_off = apres.NoteOff(note=64 + i, velocity=100, channel=0)
            if i == 0:
                self.test_midi.add_event(note_on, wait=40)
            else:
                self.test_midi.add_event(note_on, wait=0)
            self.test_midi.add_event(note_off, wait=40)

        self.test_midi_path = 'testmidi.mid'
        self.test_midi.save(self.test_midi_path)

        self.controller = MIDIController()

        self.player = Player(
            path=self.test_midi_path,
            controller=self.controller
        )

    def tearDown(self):
        os.system("rm testdev -rf")
        MIDIController.DEVROOT = self.original_devroot
        if os.path.isfile(self.test_midi_path):
            os.remove(self.test_midi_path)
        self.player.kill()

    def test_first_state(self):
        assert self.player.song_position == 1, "incorrect initial state"

    def test_next_state(self):
        self.player.next_state()
        assert self.player.song_position == 2, "next_state() didn't go to the next state"

    def test_set_state(self):
        self.player.set_state(0)
        assert self.player.song_position == 1, "player didn't move song position to next active state in set_state()"

    def test_full_looping(self):
        self.player.set_state(0)
        for i in range(12):
            self.player.next_state()
        assert self.player.song_position == 0, "Song didn't loop around"

    def test_set_loop(self):
        self.player.set_state(0)
        self.player.set_loop_start(1)
        self.player.set_loop_end(3)

        for i in range(4):
            self.player.next_state()

        assert self.player.song_position == 1, "Song didn't loop"

    def test_clear_loop(self):
        self.player.set_state(0)
        self.player.set_loop_start(1)
        self.player.set_loop_end(3)
        self.player.clear_loop()
        for i in range(4):
            self.player.next_state()

        assert self.player.song_position != 1, "Loop didn't get cleared"

    def test_register(self):
        self.player.set_register_digit(9)
        assert self.player.register == 9, "Single digit wasn't correctly set"

        self.player.set_register_digit(5)
        assert self.player.register == 95, "2 digits weren't correctly set"

        for i in "345":
            self.player.set_register_digit(int(i))
        assert self.player.register == 95345, "Multiple Digits weren't correctly set"

        self.player.clear_register()
        assert self.player.register == 0, "Register couldn't be cleared"


    def test_jump_to_register(self):
        for d in "10":
            self.player.set_register_digit(int(d))
        self.player.jump_to_register_position()

        assert self.player.song_position == 10, "Didn't jump to register position"
        assert self.player.register == 0, "Register wasn't cleared after jump"
