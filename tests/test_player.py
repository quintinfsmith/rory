import unittest
import time
import os
import apres
from apres import MIDIController

from rory.player import Player, RoryController

class PlayerTest(unittest.TestCase):
    def setUp(self):
        try:
            os.mkdir('testdev')
        except: pass

        self.test_midi = apres.MIDI()
        self.test_midi.add_event(
            apres.NoteOn(
                note=0x40,
                velocity=100,
                channel=0
            ),
            wait=30
        )
        self.test_midi.add_event(
            apres.NoteOff(
                note=0x40,
                velocity=100,
                channel=0
            ),
            wait=40
        )

        for i in range(11):
            note_on = apres.NoteOn(note=0x40 + i, velocity=100, channel=0)
            note_off = apres.NoteOff(note=0x40 + i, velocity=100, channel=0)
            self.test_midi.add_event(note_on, wait=0)
            self.test_midi.add_event(note_off, wait=40)

        self.test_midi_path = 'testmidi.mid'
        self.test_midi.save(self.test_midi_path)

        self.midi_controller_path = "testdev/mididev"
        os.system("touch %s" % self.midi_controller_path)

        self.player = Player(
            path=self.test_midi_path,
            controller_path=self.midi_controller_path
        )

    def tearDown(self):
        os.system("rm testdev -rf")
        if os.path.isfile(self.test_midi_path):
            os.remove(self.test_midi_path)
        self.player.kill()

    def test_first_state(self):
        assert self.player.song_position == 1, "incorrect initial state"

    def test_next_state(self):
        self.player.set_state(0)
        self.player.next_state()
        assert self.player.song_position == 3, "next_state() didn't go to the next state"

    def test_prev_state(self):
        self.player.set_state(5)
        self.player.prev_state()
        assert self.player.song_position != 4, "prev_state() didn't skip the empty state"
        assert self.player.song_position == 3, "prev_state() didn't move to the correct previous state"

        self.player.set_state(1)
        self.player.prev_state()
        assert self.player.song_position == 1, "prev_state() didn't move to the next available state if 0 was empty"


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
        self.player.set_loop_start(3)
        self.player.set_loop_end(5)

        for i in range(5):
            self.player.next_state()

        assert self.player.song_position == 3, "Song didn't loop correctly"

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

        assert self.player.song_position == 11, "Didn't jump to register position"
        assert self.player.register == 0, "Register wasn't cleared after jump"


    def test_input_daemon(self):
        self.player.set_state(0)
        assert self.player.song_position == 1
        assert self.player.midi_controller.is_connected()

        # Midi note 64 ON (Correct Key)
        with open(self.midi_controller_path, "ab") as fp:
            fp.write(b'\x90\x40\x64')

        time.sleep(1)
        assert self.player.song_position == 3, "Didn't move to next state on correct midi input"

        # Midi note 62 ON (incorrect key)
        with open(self.midi_controller_path, "ab") as fp:
            fp.write(b'\x80\x3E\x64')
        time.sleep(.4)

        assert self.player.song_position == 3, "Didn't require key to be released to move to next state"

        # Midi note 64 Off
        with open(self.midi_controller_path, "ab") as fp:
            fp.write(b'\x80\x40\x64')
        time.sleep(.4)

        # Midi note 64 On
        with open(self.midi_controller_path, "ab") as fp:
            fp.write(b'\x90\x40\x64')
        time.sleep(.4)

        assert self.player.song_position == 5, "Didn't move to the next state with extra keys pressed."

    def test_set_loop_by_position(self):
        self.player.set_state(0)
        self.player.set_loop_start_to_position()
        self.player.next_state()
        self.player.next_state()
        self.player.set_loop_end_to_position()

        self.player.set_state(0)

        assert self.player.loop == [1, 5]
