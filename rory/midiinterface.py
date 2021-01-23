'''Plays MIDILike Objects'''
#from apres import NoteOn, NoteOff
from apres import NoteOn

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
    def __init__(self, midi):
        self.midi = midi
        self._calculated_beatmeasures = {}
        # For quick access to which keys are pressed
        self.state_map = []
        self.active_notes_map = []
        self.measure_map = {} # { state_position: measure_number }

        beats = []
        for tick, event in self.midi.get_all_events():
            if event.__class__ == NoteOn and event.channel != 9 and event.velocity > 0:
                current_beat_tick = tick // self.midi.ppqn

                while len(beats) <= current_beat_tick:
                    beats.append([])

                beats[current_beat_tick].append((tick % self.midi.ppqn, event))

        tick_counter = 0
        for beat, events in enumerate(beats):
            diffs = set()

            prev = 0
            active_count = 0
            delta_pairs = []
            for pos, event in events:
                delta = pos - prev
                diffs.add(delta)
                delta_pairs.append((delta, event))
                prev = pos
                active_count += 1

            diffs.add(self.midi.ppqn - 1 - prev)

            diffs = list(diffs)
            diffs.sort()

            tmp_ticks = []
            if active_count:
                tmp_ticks.append([])

            for delta, event in delta_pairs:
                k = diffs.index(delta)
                for _ in range(k):
                    tmp_ticks.append([])
                tmp_ticks[-1].append(event)

            if active_count:
                k = diffs.index(self.midi.ppqn - 1 - prev)
                for _ in range(k):
                    tmp_ticks.append([])


            self.measure_map[tick_counter] = beat
            for tick_events in tmp_ticks:
                for event in tick_events:
                    while len(self.state_map) <= tick_counter:
                        self.state_map.append(set())
                        self.active_notes_map.append({})
                    self.state_map[tick_counter].add(event.note)
                    self.active_notes_map[tick_counter][event.note] = event
                tick_counter += 1

    def get_state(self, tick):
        '''Get a list of the notes currently 'On' at specified position'''
        return self.state_map[tick].copy()

    def __len__(self):
        return len(self.state_map)
