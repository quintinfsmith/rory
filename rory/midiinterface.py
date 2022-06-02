'''Plays MIDILike Objects'''
from apres import NoteOn, NoteOff, TimeSignature, SetTempo
from rory.structures import Grouping

class MIDIInterface:
    '''Layer between Player and the MIDI input file'''
    notelist = 'CCDDEFFGGAAB'

    def __handle_kwargs(self, kwargs):
        self.transpose = kwargs.get('transpose', 0)

    def __calculate_beat_chunks(self):
        ''' Group the midi events into beats '''
        beats = []

        running_beat_count = (0, 0) # beat_count, last_tick_totalled

        current_numerator = 4
        beat_size = self.midi.ppqn
        active_notes = {}
        min_note = 128
        max_note = 0
        for tick, event in self.midi.get_all_events():
            tick_diff = tick - running_beat_count[1]

            current_beat = int(running_beat_count[0] + (tick_diff // beat_size))
            while len(beats) <= current_beat:
                beats.append([[], beat_size, None, current_numerator, None])

            if self.is_note_on(event):
                active_notes[(event.channel, event.note)] = (
                    current_beat,
                    len(beats[current_beat][0])
                )

                beats[current_beat][0].append((
                    tick_diff % beat_size,
                    event,
                    tick,
                    0
                ))
                min_note = min(min_note, event.note)
                max_note = max(max_note, event.note)

            elif self.is_note_off(event):
                try:
                    beat, index = active_notes[(event.channel, event.note)]
                    _a, _b, original_tick, _ = beats[beat][0][index]
                    beats[beat][0][index] = (
                        _a,
                        _b,
                        original_tick,
                        tick - original_tick
                    )
                except KeyError:
                    pass

            elif isinstance(event, TimeSignature):
                running_beat_count = (current_beat, tick)
                current_numerator = event.numerator
                beat_size = int(self.midi.ppqn // ((2 ** event.denominator) / 4))
                beats[current_beat][1] = beat_size
                beats[current_beat][3] = current_numerator

            elif isinstance(event, SetTempo):
                self.tempo_map.append((tick, event.get_bpm()))

        # Insert beat_in_measure and current measure
        beat_in_measure = 0
        current_measure = 0
        for i, (_a, _b, _, numerator, _) in enumerate(beats):
            beats[i] = [
                _a,
                _b,
                current_measure,
                numerator,
                beat_in_measure
            ]

            beat_in_measure += 1
            if beat_in_measure == numerator:
                beat_in_measure = 0
                current_measure += 1

        self.transpose = min(
            max(
                self.transpose,
                min_note * -1
            ),
            128 - max_note
        )

        return beats


    def __init__(self, midi, **kwargs):
        self.midi = midi

        # For quick access to which keys are pressed
        self.state_map = []
        self.active_notes_map = []
        self.beat_map = {}
        self.inv_beat_map = {}
        self.rhythm_map = {
            0: (0, 1)
        }
        self.measure_map = [] # { state_position: measure_number }
        self.timing_map = {
            0: 0
        }
        self.transpose = 0
        self.tempo_map = []

        self.__handle_kwargs(kwargs)

        beats = self.__calculate_beat_chunks()
        grouping = self.__beats_to_grouping(beats)
        self.tempo_map.sort()
        self.tempo_map = self.tempo_map[::-1]

        beat_count = 0
        for measure in list(grouping):
            self.measure_map.append(len(self.state_map))
            for _beat_index, beat in enumerate(list(measure)):
                if beat.is_open():
                    continue

  #              beat.reduce()
                beat.flatten()

                self.beat_map[len(self.state_map)] = beat_count
                self.inv_beat_map[beat_count] = len(self.state_map)

                i = len(self.state_map)
                for group in list(beat):
                    if not group.is_event():
                        continue

                    self.state_map.append(set())
                    self.active_notes_map.append({})

                    for event, realtick in list(group.events):
                        new_note = event.note + self.transpose
                        event.set_note(new_note)
                        self.state_map[i].add(event.note)
                        self.active_notes_map[i][event.note] = event
                        self.timing_map[i] = realtick
                    i += 1

                beat_count += 1

    def get_tempo_at_tick(self, tick):
        for i, tempo in self.tempo_map:
            if tick >= i:
                return tempo
        return 120

    def get_real_tick(self, song_position):
        ''' Get the tick from before the midi is processed for playing '''
        first_post = song_position
        last_post = song_position
        keys = self.timing_map.keys()
        max_tick = max(keys)
        min_tick = min(keys)

        divs = 0
        while first_post not in keys and first_post > min_tick:
            first_post -= 1
            divs += 1

        while last_post not in keys and last_post <= max_tick:
            last_post += 1
            divs += 1

        if last_post > max_tick:
            diff = len(self.midi) - self.timing_map[first_post]
        else:
            diff = self.timing_map[last_post] - self.timing_map[first_post]

        if divs:
            diff //= divs

        return diff + self.timing_map[first_post]

    def get_tick_wait(self, song_position, new_position):
        ''' Calculate how long, in midi ticks, between to song positions '''
        first_post = song_position
        last_post = new_position
        keys = self.timing_map.keys()
        max_tick = max(keys)
        min_tick = min(keys)

        divs = 0
        while first_post not in keys and first_post > min_tick:
            first_post -= 1
            divs += 1

        while last_post not in keys and last_post <= max_tick:
            last_post += 1
            divs += 1

        if last_post > max_tick:
            diff = len(self.midi) - self.timing_map[first_post]
        else:
            diff = self.timing_map[last_post] - self.timing_map[first_post]

        if divs:
            diff //= divs

        return diff


    def get_state(self, position, ignored_channels = None):
        '''Get a list of the notes currently 'On' at specified position'''
        if not ignored_channels:
            state = self.state_map[position].copy()
        else:
            state = set()
            for note, event in self.active_notes_map[position].items():
                if event.channel not in ignored_channels:
                    state.add(note)

        return state

    def get_active_channels(self, position):
        ''' Get set of channels present at a given position '''
        active = set()
        for _note, event in self.active_notes_map[position].items():
            active.add(event.channel)

        return active

    def get_chord_name(self, position, channel, nu_mode=False):
        if nu_mode:
            output = self.get_chord_name_nu(position, channel)
        else:
            output = self.get_chord_name_standard(position, channel)
        return output

    def get_chord_name_nu(self, position, channel):
        ''' Trying Something Different. Returns a Base8 representation of the pressed notes. '''

        pressed = []
        for note, event in self.active_notes_map[position].items():
            if event.channel == channel:
                pressed.append(note)

        tonic = min(pressed)
        for i, pressed_note in enumerate(pressed):
            pressed[i] = (pressed_note - tonic) % 12
        pressed = list(set(pressed))
        pressed.sort()

        pressed = tuple(pressed)
        chord_value = 0
        for p in pressed:
            chord_value += (2 ** p)

        return str(chord_value)

    def get_chord_name_standard(self, position, channel):
        ''' Attempt to detect the name of the chord being played at a given position '''
        chord_names = {
            (0, 3, 7): "m",
            (0, 4, 9): "m/1",
            (0, 5, 8): "m/2",

            (0, 4, 7): "", # Major
            (0, 3, 8): "/1",
            (0, 5, 9): "/2",

            (0, 3, 6): "dim",
            (0, 3, 9): "dim/1",
            (0, 6, 9): "dim/2",

            (0, 3, 6, 9): "dim7",

            (0, 4, 8): "aug", # Symmetrical
            (0, 4, 8, 10): "aug7",

            (0, 2, 7): "sus2",
            (0, 5, 10): "sus2/1", # sus4/2

            (0, 2, 7, 10): "7sus2",
            (0, 5, 7): "sus4", # sus2/2

            (0, 6, 7, 10): "7sus4",
            #(0, 12): "open",
            (0, 4): "3",
            (0, 3): "m3",
            (0, 9): "m3/1",

            (0, 7): "5",
            (0, 5): "5/1",
            (0, 8): "aug5", #3/1
            (0, 6): "dim5", #3/1

            (0, 4, 7, 9): "6",
            (0, 3, 7, 9): "m6",
            (0, 4, 7, 10): "7",
            (0, 3, 7, 10): "m7",
            (0, 3, 6, 10): "m7b5",
            (0, 4, 7, 11): "maj7",
            (0, 3, 7, 11): "mM7",
            (0, 4, 6, 10): "7-5",
            (0, 4, 8, 10): "7+5",
            (0, 4, 7, 10, 14): "9",
            (0, 3, 7, 10, 14): "m9",
            (0, 4, 7, 11, 14): "maj9",
            (0, 4, 7, 10, 14, 17): "11",
            (0, 3, 7, 10, 14, 17): "m11",
            (0, 2, 4, 7): "add2",
            (0, 4, 5, 7): "add4",
            (0, 4, 7, 14): "add9",
            (0, 4, 7, 17): "add11",
        }

        pressed = []
        for note, event in self.active_notes_map[position].items():
            if event.channel == channel:
                pressed.append(note)

        tonic = min(pressed)
        for i, pressed_note in enumerate(pressed):
            pressed[i] = (pressed_note - tonic) % 12
        pressed = list(set(pressed))
        pressed.sort()

        pressed = tuple(pressed)
        if pressed in chord_names:
            name = chord_names[pressed]

            if name[-2:] == "/1":
                slash = self.get_note_name(tonic)
                tonic += pressed[-1]
                name = f"{self.get_note_name(tonic)}{name[0:-1]}{slash}"
            elif name[-2:] == "/2":
                slash = self.get_note_name(tonic)
                tonic += pressed[-2]
                name = f"{self.get_note_name(tonic)}{name[0:-1]}{slash}"
            else:
                name = self.get_note_name(tonic) + name
        else:
            name = ""

        return name

    def __len__(self):
        return len(self.state_map)

    def get_first_position_in_measure(self, measure):
        ''' Returns the index of the first tick of the measure in the state map '''
        measure = min(
            measure,
            max(
                len(self.measure_map) - 1,
                0
            )
        )
        return self.measure_map[measure]


    def get_measure(self, test_position):
        ''' Given an index in the state map, returns the corresponding measure '''
        output = 0

        for (i, relative_position) in enumerate(self.measure_map):
            if test_position < relative_position:
                break
            output = i

        return output

    def get_beat(self, test_position):
        ''' Given an index in the state map, returns the corresponding beat '''
        return self.inv_beat_map[test_position]

    @staticmethod
    def get_note_name(midi_note):
        ''' Get note's letter name '''
        name = MIDIInterface.notelist[midi_note % len(MIDIInterface.notelist)]
        if midi_note % len(MIDIInterface.notelist) in (1, 3, 6, 8, 10):
            name += "#"

        return name

    @staticmethod
    def is_note_off(event):
        ''' checks if event is *effectively* a noteOff event '''
        # NoteOn with 0 velocity are treated as note off

        return (
            isinstance(event, NoteOn) and
            event.channel != 9 and
            event.velocity == 0
        ) or (
            isinstance(event, NoteOff) and
            event.channel != 9
        )

    @staticmethod
    def is_note_on(event):
        ''' checks if event is *effectively* a noteOn event '''
        return (
            isinstance(event, NoteOn) and
            event.channel != 9 and
            event.velocity > 0
        )

    @staticmethod
    def __beats_to_grouping(beats):
        ''' Convert the beats into 'Grouping' structure for ease of manipulation. '''
        grouping = Grouping()
        measures = []
        for (_, _, m_index, _, _) in beats:
            while len(measures) <= m_index:
                measures.append(m_index)

        grouping.set_size(len(measures))
        for _, _, m_index, numerator, _ in beats:
            grouping[m_index].set_size(numerator)

        for events, beat_size, m_index, _, bim in beats:
            beat = grouping[m_index][bim]
            for (pos, event, _real, _duration) in events:
                beat.set_size(beat_size)

            for (pos, event, real, _duration) in events:
                tick = beat[int(pos)]
                tick.add_event((event, real))

        return grouping
