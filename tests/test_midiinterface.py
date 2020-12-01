import apres
import unittest
from rory.midiinterface import MIDIInterface

class MIDIInterfaceTest(unittest.TestCase):
    def setUp(self):
        # Set up a test midi to use withthe interface
        test_midi = apres.MIDI()
        for i in range(12):
            note_on = apres.NoteOn(note=64 + i, velocity=100, channel=0)
            note_off = apres.NoteOff(note=64 + i, velocity=100, channel=0)
            test_midi.add_event(note_on, wait=0)
            test_midi.add_event(note_off, wait=40)

        self.test_interface = MIDIInterface(test_midi)

    def tearDown(self):
        pass

    def test_count_active_states(self):
        active_states_counted =0
        for state in self.test_interface.state_map:
            if state:
                active_states_counted += 1

        assert active_states_counted == 12, "Somehow found more notes than are in the midi"

