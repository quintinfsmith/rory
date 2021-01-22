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

        maximum_definition = 4
        minimum_definition = 2
        tick_counter = 0
        for beat, events in enumerate(beats):
            biggest = self.midi.ppqn // minimum_definition
            for pos, _ in events:
                if pos == 0:
                    pos = self.midi.ppqn
                biggest = greatest_common_divisor(biggest, pos)

            # If biggest < MAXDEF, will lose precision
            biggest = max(self.midi.ppqn // maximum_definition, biggest)
            definition = self.midi.ppqn // biggest

            tmp_ticks = []
            for _ in range(definition):
                tmp_ticks.append([])

            for pos, event in events:
                tmp_ticks[pos // biggest].append(event)

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
