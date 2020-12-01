import unittest
import time
import os
import apres
from midicontroller import MIDIController
from midiinterface import MIDIInterface

class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.original_devroot = MIDIController.DEVROOT
        MIDIController.DEVROOT = 'testdev/'
        try:
            os.mkdir('testdev')
        except: pass

    def tearDown(self):
        os.system("rm testdev -rf")
        MIDIController.DEVROOT = self.original_devroot

    def test_path_specified(self):
        """Check controller connects on initialization if path is specified"""
        os.system("touch testdev/midi_ut_0")
        controller = MIDIController("testdev/midi_ut_0")
        assert controller.is_connected() == True, "Controller isn't connecting to specified character device"

        controller.close()

        assert controller.is_connected() != True, "Controller didn't disconnect"
        os.remove("testdev/midi_ut_0")

    def test_auto_connect(self):
        controller = MIDIController()
        assert controller.is_connected() != True, "Controller connected to non-existent device"
        os.system("touch testdev/midi_ut_1")
        time.sleep(1)
        assert controller.is_connected() == True, "Controller didn't connect to newly created device"

        os.remove("testdev/midi_ut_1")
        time.sleep(1)
        assert controller.is_connected() == False, "Controller didn't disconnected from detached device"

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

if __name__ == "__main__":
    unittest.main()

