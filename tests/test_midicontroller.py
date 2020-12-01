import unittest
import time
import os
from rory.midicontroller import MIDIController
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

