'''Compare MIDI Device input to .mid'''

class MIDIInterface(object):
    def __init__(self, midilike, controller):
        self.controller = controller
        self.midilike = midilike

        if self.controller.connected:
            self.controller.listen()

        squeeze_in = {}

        self.state_map = [] # For quick access to which keys are pressed
        self.text_map = []
        self.event_map = [] # For access to extra information about the key press (velocity, channel)
        self.event_pair_map = {}
        self.active_notes_map = []

        self.real_tick_map = {0: 0}

        states_per_measure = (midilike.ppqn * 4)
    
        collective_pressed_keys = {}

        modded_tick = 0
        insert_space = False

        for tick in range(len(self.midilike)):
            pressed_keys = {}
            text_events = []
            for track in self.midilike.tracks:
                for event in track.get_events(tick):
                    if event.eid == event.NOTE_ON and event.channel != 10:
                        if event.velocity == 0 and event.note in collective_pressed_keys.keys():
                            self.event_pair_map[collective_pressed_keys[event.note].id] = event
                            del collective_pressed_keys[event.note]
                        else:
                            pressed_keys[event.note] = event
                            collective_pressed_keys[event.note] = event
                    elif event.eid == event.NOTE_OFF and event.note in collective_pressed_keys.keys():
                        self.event_pair_map[collective_pressed_keys[event.note].id] = event
                        del collective_pressed_keys[event.note]
                    elif event.eid == event.TEXT or event.eid == event.LYRIC:
                        text_events.append(event)
 
            if len(pressed_keys.keys()):
                squashed_tick = tick * squash_factor

                if squashed_tick % 1: 
                    squashed_tick = int(squashed_tick)
                    if not int(squashed_tick) in squeeze_in.keys():
                        squeeze_in[int(squashed_tick)]  = []
                    squeeze_in[int(squashed_tick)].append((
                        pressed_keys.copy(),
                        set(pressed_keys.keys()),
                        collective_pressed_keys.copy()
                    ))
                else:
                    squashed_tick = int(squashed_tick)

                    while len(self.state_map) <= squashed_tick:
                        self.state_map.append(set())
                    while len(self.event_map) <= squashed_tick:
                        self.event_map.append({})
                    while len(self.text_map) <= squashed_tick:
                        self.text_map.append([])

                    self.text_map[squashed_tick] = text_events
                    self.event_map[squashed_tick].update(pressed_keys.copy())
                    self.state_map[squashed_tick] |= set(pressed_keys.keys())
                    while len(self.active_notes_map) <= squashed_tick:
                        self.active_notes_map.append(collective_pressed_keys.copy())

        ticks = list(squeeze_in.keys())
        ticks.sort()
        for tick in ticks[::-1]:
            pairs = squeeze_in[tick]
            for pair in pairs[::-1]:
                self.event_map.insert(tick + 1, pair[0])
                self.state_map.insert(tick + 1, pair[1])
                self.active_notes_map.insert(tick + 1, pair[2])

    def rechannel_event(self, note_on_event, channel):
        '''Change the channel of a midi NOTE_ON event and its corresponding NOTE_OFF event'''
        if note_on_event.id in self.event_pair_map.keys():
            note_off_event = self.event_pair_map[note_on_event.id]
            note_on_event.channel = channel
            note_off_event.channel = channel

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

    def get_state(self, tick):
        return self.state_map[tick]

    def states_unmatch(self, tick, given_state):
        '''Check that the controller is not pressing any keys at the given state in the midi'''
        return not (self.state_map[tick].intersection(given_state))

    def get_pressed(self):
        return self.controller.get_pressed()

    def __len__(self):
        return len(self.state_map)

