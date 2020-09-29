'''Compare MIDI Device input to .mid'''
import random, time

class MIDIInterface(object):
    def __init__(self, midi, controller):
        self.controller = controller
        self.midi = midi

        if self.controller and self.controller.connected:
            self.controller.listen()

        # For quick access to which keys are pressed
        self.state_map = []

        self.active_notes_map = []

        self.channels_used = set()

        time_signature_map = {
            0: (4,4)
        }


        current_tempo = 0
        pressed_keys = {}
        for i, (event,tick) in enumerate(self.midi.get_all_events()):

            if event.__class__ == SetTempoEvent:
                current_tempo = event.tempo

            elif event.__class__ == TimeSignatureEvent:
                time_signature_map[tick] = (event.numerator, event.denominator)

            elif event.__class__ == NoteOnEvent and event.channel != 9:
                self.channels_used.add(event.channel)
                if event.velocity == 0 and event.note in pressed_keys.keys():
                    del pressed_keys[event.note]
                else:
                    pressed_keys[event.note] = event

            elif event.__class__ == NoteOffEvent and event.note in pressed_keys.keys():
                del pressed_keys[event.note]


            if len(pressed_keys.keys()):
                while len(self.state_map) <= tick:
                    self.state_map.append(set())

                self.state_map[tick] |= set(pressed_keys.keys())
                while len(self.active_notes_map) <= tick:
                    self.active_notes_map.append(pressed_keys.copy())


    def get_state(self, tick):
        return self.state_map[tick]

    def save_as(self, path):
        self.midilike.save_as(path)

    def is_state_empty(self, tick):
        return not bool(self.state_map[tick])

    def states_match(self, tick, given_state, ignored_channels=[0]):
        '''Check that the controller is pressing the correct keys'''
        given_state = given_state.copy()
        for key, event in self.active_notes_map[tick].items():
            if event.channel in ignored_channels:
                given_state.add(key)

        return len(given_state.intersection(self.state_map[tick])) == len(self.state_map[tick])


    def states_unmatch(self, tick, given_state):
        '''Check that the controller is not pressing any keys at the given state in the midi'''
        return not (self.state_map[tick].intersection(given_state))


    def get_pressed(self):
        # Test
        options = list(range(40, 100))
        output = set()
        for i in range(random.randint(1, 6)):
            output.add(options.pop(random.randint(0, len(options) - 1)))
        time.sleep(.3)
        return output

        #if not self.controller.connected:
        #    time.sleep(.05)

        #return self.controller.get_pressed()

    def __len__(self):
        return len(self.state_map)

