'''Compare MIDI Device input to .mid'''

class MIDIInterface(object):
    def __init__(self, midilike, controller):
        self.controller = controller
        self.midilike = midilike

        if self.controller.connected:
            self.controller.listen()

        self.state_map = [] # For quick access to which keys are pressed
        self.event_map = [] # For access to extra information about the key press (velocity, channel)
        squash_factor = 8 / self.midilike.tpqn
        for tick in range(len(self.midilike)):
            pressed_keys = {}
            for track in self.midilike.tracks:
                for event in track.get_events(tick):
                    if event.eid == event.NOTE_ON and event.channel != 10:
                        if event.velocity == 0 and event.note in pressed_keys.keys():
                            del pressed_keys[event.note]
                        else:
                            pressed_keys[event.note] = event
                    elif event.eid == event.NOTE_OFF and event.note in pressed_keys.keys():
                        del pressed_keys[event.note]

            if len(pressed_keys.keys()):
                while len(self.state_map) <= tick * squash_factor:
                    self.state_map.append(set())
                while len(self.event_map) <= tick * squash_factor:
                    self.event_map.append({})
                self.event_map[int(tick * squash_factor)].update(pressed_keys.copy())
                self.state_map[int(tick * squash_factor)] |= set(pressed_keys.keys())

    def is_state_empty(self, tick):
        return not bool(self.state_map[tick])

    def states_match(self, tick, given_state):
        '''Check that the controller is pressing the correct keys'''
        return len(given_state.intersection(self.state_map[tick])) == len(self.state_map[tick])

    def get_state(self, tick):
        return self.state_map[tick]

    def states_unmatch(self, tick, given_state):
        '''Check that the controller is not pressing any keys at the given state in the midi'''
        return not (self.state_map[tick].intersection(given_state))

    def get_pressed(self):
        return self.controller.get_pressed()

    def __len__(self):
        return len(self.state_map)

