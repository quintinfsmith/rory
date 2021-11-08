'''Plays MIDILike Objects'''
import math
from apres import NoteOn, SetTempo, TimeSignature, MIDIEvent

def greatest_common_divisor(number_a, number_b):
    '''Euclid's method'''
    bigger_int = max(number_a, number_b)
    smaller_int = min(number_a, number_b)

    while smaller_int:
        tmp = smaller_int
        smaller_int = bigger_int % smaller_int
        bigger_int = tmp
    return int(bigger_int)

class MIDIInterface:
    '''Layer between Player and the MIDI input file'''
    notelist = 'CCDDEFFGGAAB'

    def __handle_kwargs(self, kwargs):
        if 'transpose' in kwargs:
            self.transpose = kwargs['transpose']

    def __calculate_beat_chunks(self):
        beats = []

        last_tick = 0 # will be the final tick with a note on event
        running_beat_count = (0, 0) # beat_count, last_tick_totalled
        measure_map = [] # index: measure, value: midi tick
        beat_map = [] # index: beat, value: midi tick

        current_numerator = 4
        beat_size = self.midi.ppqn

        for tick, event in self.midi.get_all_events():
            final_tick = tick
            tick_diff = tick - running_beat_count[1]

            current_beat = int(running_beat_count[0] + (tick_diff // beat_size))
            while len(beats) <= current_beat:
                beats.append([[], beat_size, False])
                beat_map.append(tick)

            if isinstance(event, NoteOn) and event.channel != 9 and event.velocity > 0:
                beats[current_beat][0].append((tick_diff % beat_size, event, tick))

            elif isinstance(event, TimeSignature):
                for i in range(math.ceil(tick_diff // (beat_size * current_numerator))):
                    measure_map.append((i * (beat_size * current_numerator)) + running_beat_count[1])

                running_beat_count = (current_beat, tick)
                current_numerator = event.numerator
                beat_size = self.midi.ppqn // ((2 ** event.denominator) / 4)

        if final_tick != running_beat_count[1]:
            tick_diff = final_tick - running_beat_count[1]
            for i in range(math.ceil(tick_diff / (beat_size * current_numerator))):
                measure_map.append((i * (beat_size * current_numerator)) + running_beat_count[1])

        for b in range(len(beats)):
            beats[b][2] = (beat_map[b] in measure_map)

        return beats

    def __init__(self, midi, **kwargs):
        self.midi = midi

        # For quick access to which keys are pressed
        self.state_map = []
        self.active_notes_map = []
        self.beat_map = {}
        self.measure_map = [] # { state_position: measure_number }
        self.timing_map = {0: 0}
        self.transpose = 0

        self.__handle_kwargs(kwargs)

        beats = self.__calculate_beat_chunks()

        for beat, (events, beat_size, is_measure_start) in enumerate(beats):
            adjusted_states = [[]]
            if len(events):
                delta_pairs = []
                relative_distances = set()

                prev = 0
                for pos, event, real_tick in events:
                    delta = pos - prev
                    relative_distances.add(delta)
                    delta_pairs.append((delta, (event, real_tick)))
                    prev = pos
                final_tick_delta = beat_size - 1 - prev
                del prev


                relative_distances.add(final_tick_delta)
                relative_distances = list(relative_distances)
                relative_distances.sort()

                for delta, event in delta_pairs:
                    for _ in range(relative_distances.index(delta)):
                        adjusted_states.append([])
                    adjusted_states[-1].append(event)

                for _ in range(relative_distances.index(final_tick_delta) + 1):
                    adjusted_states.append([])
            else:
                for _ in range(4):
                    adjusted_states.append([])

            if is_measure_start:
                self.measure_map.append(len(self.state_map))

            self.beat_map[len(self.state_map)] = beat
            for _i, tick_events in enumerate(adjusted_states):
                self.state_map.append(set())
                self.active_notes_map.append({})
                for _j, (event, real_tick) in enumerate(tick_events):
                    event.set_note(event.note + self.transpose)

                    self.state_map[-1].add(event.note)
                    self.active_notes_map[-1][event.note] = event
                    self.timing_map[len(self.state_map)] = real_tick

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

    def get_chord_name(self, position, channel):
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
                name = "%s%s%s" % (self.get_note_name(tonic), name[0:-1], slash)
            elif name[-2:] == "/2":
                slash = self.get_note_name(tonic)
                tonic += pressed[-2]
                name = "%s%s%s" % (self.get_note_name(tonic), name[0:-1], slash)
            else:
                name = self.get_note_name(tonic) + name

        else:
            name = ""
        return name

    def __len__(self):
        return len(self.state_map)

    def get_first_position_in_measure(self, measure):
        measure = min(measure, max(len(self.measure_map) - 1, 0))
        return self.measure_map[measure]


    def get_measure(self, test_position):
        output = 0

        for (i, relative_position) in enumerate(self.measure_map):
            if test_position < relative_position:
                break
            output = i

        return output

    @staticmethod
    def get_note_name(midi_note):
        ''' Get note's letter name '''
        name = MIDIInterface.notelist[midi_note % len(MIDIInterface.notelist)]
        if midi_note % len(MIDIInterface.notelist) in (1,3,6,8,10):
            name += "#"

        return name
