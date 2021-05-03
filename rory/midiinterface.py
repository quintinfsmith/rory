'''Plays MIDILike Objects'''
#from apres import NoteOn, NoteOff
from apres import NoteOn, SetTempo

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
    def __init__(self, midi, **kwargs):
        self.midi = midi
        self._calculated_beatmeasures = {}
        # For quick access to which keys are pressed
        self.state_map = []
        self.active_notes_map = []
        self.measure_map = {} # { state_position: measure_number }
        self.timing_map = {0: 0}
        self.tempo_map = {0: 120}

        self.transpose = 0
        if 'transpose' in kwargs:
            self.transpose = kwargs['transpose']

        beats = []
        for tick, event in self.midi.get_all_events():
            if event.__class__ == NoteOn and event.channel != 9 and event.velocity > 0:
                current_beat_tick = tick // self.midi.ppqn

                while len(beats) <= current_beat_tick:
                    beats.append([])

                beats[current_beat_tick].append((tick % self.midi.ppqn, event, tick))

            elif event.__class__ == SetTempo:
                self.tempo_map[tick] = event.get_bpm()

        tick_counter = 0
        for beat, events in enumerate(beats):
            beat_tick = beat * self.midi.ppqn
            diffs = set()

            prev = 0
            active_count = 0
            delta_pairs = []
            for pos, event, real_tick in events:
                delta = pos - prev
                diffs.add(delta)
                delta_pairs.append((delta, (event, real_tick)))
                prev = pos
                active_count += 1

            diffs.add(self.midi.ppqn - 1 - prev)

            diffs = list(diffs)
            diffs.sort()

            tmp_ticks = []
            tmp_ticks.append([])

            if delta_pairs:
                for delta, event in delta_pairs:
                    k = diffs.index(delta)
                    for _ in range(k):
                        tmp_ticks.append([])
                    tmp_ticks[-1].append(event)

                k = diffs.index(self.midi.ppqn - 1 - prev)
                for _ in range(k):
                    tmp_ticks.append([])
            else:
                for _ in range(3):
                    tmp_ticks.append([])


            self.measure_map[tick_counter] = beat
            for tick_events in tmp_ticks:
                for (event, real_tick) in tick_events:
                    event.set_note(event.note + self.transpose)
                    while len(self.state_map) <= tick_counter:
                        self.state_map.append(set())
                        self.active_notes_map.append({})
                    self.state_map[tick_counter].add(event.note)
                    self.active_notes_map[tick_counter][event.note] = event
                    self.timing_map[tick_counter] = real_tick
                tick_counter += 1

    def get_tempo(self, song_position):
        real_tick = self.get_real_tick(song_position)
        output = 120
        for tick, tempo in list(self.tempo_map.items())[::-1]:
            if real_tick > tick:
                output = tempo
                break
        return output

    def get_real_tick(self, song_position):
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


    def get_state(self, tick, ignored_channels=None):
        '''Get a list of the notes currently 'On' at specified position'''
        if not ignored_channels:
            state = self.state_map[tick].copy()
        else:
            state = set()
            for note, event in self.active_notes_map[tick].items():
                if event.channel not in ignored_channels:
                    state.add(note)

        return state

    def get_active_channels(self, tick):
        active = set()
        for note, event in self.active_notes_map[tick].items():
            active.add(event.channel)

        return active

    def get_chord_name(self, tick, channel):
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
        for note, event in self.active_notes_map[tick].items():
            if event.channel == channel:
                pressed.append(note)

        m = min(pressed)
        for i, n in enumerate(pressed):
            pressed[i] = (n - m) % 12
        pressed = list(set(pressed))

        pressed.sort()

        pressed = tuple(pressed)
        if pressed in chord_names:
            name = chord_names[pressed]

            if name[-2:] == "/1":
                slash = self._get_note_name(m)
                m += pressed[-1]
                name = "%s%s%s" % (self._get_note_name(m), name[0:-1], slash)
            elif name[-2:] == "/2":
                slash = self._get_note_name(m)
                m += pressed[-2]
                name = "%s%s%s" % (self._get_note_name(m), name[0:-1], slash)
            else:
                name = self._get_note_name(m) + name

        else:
            name = ""
        return name


    def _get_note_name(self, n):
        NOTELIST = 'CCDDEFFGGAAB'

        name = NOTELIST[n % len(NOTELIST)]
        if n % len(NOTELIST) in (1,3,6,8,10):
            name += "#"

        return name


    def __len__(self):
        return len(self.state_map)
