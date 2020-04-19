'''Plays MIDILike Objects'''

from localfuncs import read_character
from Rect import RectScene, Rect
import threading
import math, time
import mido

def logg(msg):
    with open('logg', 'a') as fp:
        fp.write(str(msg) + "\n")

class Player(RectScene):
    '''Plays MIDILike Objects'''

    # Display constants
    SHARPS = (1, 3, 6, 8, 10)
    NOTELIST = 'CCDDEFFGGAAB'
    #NOTELIST = '3456789AB012'


    # Display Flags
    FLAG_BACKGROUND = 1
    FLAG_PRESSED = 1 << 2
    FLAG_POSITION = 1 << 3

    def kill(self):
        ''''shutdown the player Box'''
        self.is_active = False
        self.midi_controller.close()
        super().kill()

    def next_state(self):
        self.song_position += 1
        while self.song_position < self.loop[1] and not self.midi_interface.get_state(self.song_position):
            self.song_position += 1

        self.song_position = min(self.loop[1], self.song_position)

        if (self.song_position == self.loop[1]):
            self.song_position = self.loop[0]

        self.disp_flags[self.FLAG_POSITION] = True

    def prev_state(self):
        self.song_position -= 1
        while self.song_position > 0 and not self.midi_interface.get_state(self.song_position):
            self.song_position -= 1
        self.song_position = max(0, self.song_position)
        self.disp_flags[self.FLAG_POSITION] = True


    def set_state(self, song_position):
        '''set the song position as the value in the register'''
        self.song_position = max(0, self.register)

        while self.song_position < self.loop[1] and not self.midi_interface.get_state(self.song_position):
            self.song_position += 1

        self.song_position = min(self.loop[1], self.song_position)

        if (self.song_position == self.loop[1]):
            self.song_position = self.loop[0]

        self.disp_flags[self.FLAG_POSITION] = True

    def toggle_ignore_channel(self):
        pass

    def __init__(self, rect_id, rectmanager, **kwargs):
        super().__init__(rect_id, rectmanager, **kwargs)

        self.is_active = True

        self.register = 0
        self.loop = [0, 0]

        self.note_range = [21, 21 + 88]

        self.active_midi = mido.MidiFile(kwargs['path'])
        self.midi_controller = kwargs['controller']
        self.midi_interface = MIDIInterface(self.active_midi)
        self.clear_loop()

        self.pressed_notes = set()
        self.need_to_release = set()

        self.song_position = -1

        self.disp_flags = {
            self.FLAG_PRESSED: True, # Pressed notes have changed,
            self.FLAG_POSITION: True, # Song Position has changed,
            self.FLAG_BACKGROUND: True # Background needs redraw
        }

        self.active_row_position = 8
        self.rect_background = self.new_rect()
        #self.set_bg_color(Rect.BLUE)
        self.visible_note_rects = []
        self.pressed_note_rects = []

        self.rect_position_display = self.new_rect()

        self.midi_input_thread = threading.Thread(
            target=self.midi_input_daemon
        )

        self.midi_input_thread.start()
        self.next_state()

    def midi_input_daemon(self):
        while self.is_active and self.midi_controller.connected:
            message = self.midi_controller.read()
            if message:
                if message.type == 'note_on':
                    self.pressed_notes.add(message.note)
                    self.disp_flags[self.FLAG_PRESSED] = True
                elif message.type == 'note_off':
                    self.pressed_notes.remove(message.note)
                    try:
                        self.need_to_release.remove(message.note)
                    except KeyError:
                        pass
                    self.disp_flags[self.FLAG_PRESSED] = True
                song_state = self.midi_interface.get_state(self.song_position)

            if song_state.intersection(self.pressed_notes) == song_state and not self.need_to_release.intersection(song_state):
                self.need_to_release = self.need_to_release.union(song_state)
                self.next_state()

    def tick(self):
        was_flagged = False
        if self.disp_flags[self.FLAG_BACKGROUND]:
            self.draw_background()
            self.disp_flags[self.FLAG_BACKGROUND] = False
            was_flagged = True

        if self.disp_flags[self.FLAG_POSITION]:
            self.draw_visible_notes()
            self.disp_flags[self.FLAG_POSITION] = False
            self.disp_flags[self.FLAG_PRESSED] = True
            was_flagged = True

        if self.disp_flags[self.FLAG_PRESSED]:
            self.draw_pressed_row()
            self.disp_flags[self.FLAG_PRESSED] = False
            was_flagged = True

        if was_flagged:
            self.draw()


    def draw_visible_notes(self):
        while self.visible_note_rects:
            self.visible_note_rects.pop().detach()

        for _y in range(self.rect_background.height):
            tick = self.song_position - self.active_row_position + _y

            if tick < 0 or tick >= len(self.midi_interface.state_map):
                continue

            if (_y <= self.active_row_position):
                y = self.rect_background.height - _y
            else:
                y = self.rect_background.height - ((_y * 2) - self.active_row_position)

            row = self.midi_interface.active_notes_map[tick]
            for note, message in row.items():
                x = self.get_displayed_key_position(message.note)
                note_rect = self.rect_background.new_rect()
                note_rect.set_character(0, 0, self.NOTELIST[message.note % 12])
                note_rect.move(x, y)

                color = self.get_channel_color(message.channel)
                if message.note % 12 in self.SHARPS:
                    note_rect.set_bg_color(color)
                    note_rect.set_fg_color(Rect.BLACK)
                else:
                    note_rect.set_fg_color(color)

                self.visible_note_rects.append(note_rect)

        position_string = "%s / %s" % (self.song_position, len(self.midi_interface.state_map))
        self.rect_position_display.resize(len(position_string), 1)
        self.rect_position_display.move(self.width - len(position_string) - 1, self.height - 1)
        self.rect_position_display.set_string(0, 0, position_string)



    def draw_pressed_row(self):
        while self.pressed_note_rects:
            self.pressed_note_rects.pop().detach()

        active_state = self.midi_interface.get_state(self.song_position)
        y = self.rect_background.height - self.active_row_position

        for note in self.pressed_notes:
            x = self.get_displayed_key_position(note)

            note_rect = self.rect_background.new_rect()
            note_rect.set_character(0, 0, self.NOTELIST[note % 12])
            note_rect.move(x, y)

            if note in active_state:
                note_rect.set_bg_color(Rect.GREEN)
                note_rect.set_fg_color(Rect.BLACK)
            else:
                note_rect.set_bg_color(Rect.RED)
                note_rect.set_fg_color(Rect.BLACK)

            self.pressed_note_rects.append(note_rect)

    def draw_background(self):
        width = self.get_displayed_key_position(self.note_range[1] + 1)
        self.rect_background.set_fg_color(Rect.BRIGHTBLACK)

        self.rect_background.resize(
            height = self.height,
            width = width
        )

        background_pos = (self.width - width) // 2
        self.rect_background.move(background_pos, 0)

        y = self.height - self.active_row_position
        for i in range(self.note_range[0], self.note_range[1]):
            x = self.get_displayed_key_position(i)
            if i % 12 in self.SHARPS:
                self.rect_background.set_character(x, y - 1, chr(9608))
                self.rect_background.set_character(x, y, chr(9474))
            else:
                self.rect_background.set_character(x, y, chr(9601))

            if (i + 3) % 12 == 0:
                for j in range(0, y):
                    self.rect_background.set_character(x, j, chr(9550))
                for j in range(y + 1, self.rect_background.height):
                    self.rect_background.set_character(x, j, chr(9550))
        for y in range(self.height):
            self.set_character(background_pos - 1, y, chr(9475))
            self.set_character(background_pos + width, y, chr(9475))

        self.rect_background.draw()

    def get_width(self):
        return (self.note_range[1] - self.note_range[0]) + 2

    @staticmethod
    def get_channel_color(channel):
        colors = [
            Rect.BRIGHTYELLOW,
            Rect.WHITE,
            Rect.CYAN,
            Rect.GREEN,
            Rect.MAGENTA,
            Rect.BLUE,
            Rect.BRIGHTBLACK, # i *think* it's channel 7 that is drums... if so, this is just a placeholder
            Rect.RED
        ]
        color = colors[channel % 8]

        if channel > 8:
            color ^= Rect.BRIGHT

        return color

    def get_displayed_key_position(self, midi_key):
        piano_position = midi_key - self.note_range[0]
        octave = piano_position // 12
        piano_key = piano_position % 12
        position = (octave * 14) + piano_key

        if piano_key > 2: # B
            position += 1
        if piano_key > 7:
            position += 1

        return position

    def set_loop_start_to_position(self):
        self.set_loop_start(self.song_position)

    def set_loop_end_to_position(self):
        self.set_loop_end(self.song_position)

    def set_loop_start(self, position):
        '''set current positions as loop start'''
        self.loop[0] = min(max(0, position), len(self.midi_interface.state_map) - 1)

    def set_loop_end(self, position):
        '''set current positions as loop end'''
        self.loop[1] = min(max(0, position), len(self.midi_interface.state_map) - 1)

    def clear_loop(self):
        '''Stop Looping'''
        self.loop = [0, len(self.midi_interface.state_map) - 1]

    def set_register_digit(self, n):
        self.register *= 10
        self.register += n

    def clear_register(self):
        self.register = 0

    def jump_to_register_position(self):
        self.set_state(self.register)
        self.clear_register()




class MIDIInterface(object):
    def __init__(self, midi):
        self.midi = midi
        self._calculated_beatmeasures = {}
        # For quick access to which keys are pressed
        self.state_map = []
        self.active_notes_map = []

        self.time_signature_map = {
            0: 4
        }
        current_time_signature = 4

        current_tempo = 0
        tick = 0
        tmp_states = []
        measure_sizes = []

        for i, event in enumerate(mido.merge_tracks(self.midi.tracks)):
            tick += event.time
            #tick += mido.tick2second(event.time, self.midi.ticks_per_beat, current_tempo)
            beat_in_measure, subbeat, abs_beat, measure = self.get_beat_and_measure(tick)

            if event.type == 'time_signature':
                self.time_signature_map[tick] = event.numerator
                current_time_signature = event.numerator

            elif event.type == 'note_on' and event.channel != 9:
                if event.velocity == 0:
                    pass
                else:
                    key = (measure, beat_in_measure, subbeat)
                    while len(tmp_states) <= measure:
                        tmp_states.append([])

                    while len(tmp_states[measure]) < current_time_signature:
                        tmp_states[measure].append([])

                    tmp_states[measure][beat_in_measure].append((subbeat, event))

                    while len(measure_sizes) <= measure:
                        measure_sizes.append((0, current_time_signature))

                    new_size = max(measure_sizes[measure][0], subbeat[1])
                    measure_sizes[measure] = (new_size, measure_sizes[measure][1])
            elif event.type == 'note_off':
                pass

        for m, measure in enumerate(tmp_states):
            pivot_a = len(self.state_map)

            prec, time_sig = measure_sizes[m]
            minimum_new_states = prec * time_sig
            for b, beat in enumerate(measure):
                pivot_b = b * prec
                for subbeat, event in beat:
                    offset = int(subbeat[0] * prec / subbeat[1]) + pivot_a + pivot_b
                    while len(self.state_map) <= offset:
                        self.state_map.append(set())
                        self.active_notes_map.append({})
                        minimum_new_states -= 1

                    self.state_map[offset].add(event.note)
                    self.active_notes_map[offset][event.note] = event

            for i in range(max(0, minimum_new_states)):
                self.state_map.append(set())
                self.active_notes_map.append({})


    def get_state(self, tick):
        return self.state_map[tick].copy()


    def get_beat_and_measure(self, tick):
        DIV = 4
        try:
            output = self._calculated_beatmeasures[tick]
        except KeyError:
            tpb = self.midi.ticks_per_beat
            current_tick = 0
            total_beats = 0
            prev_beats = 4
            measure_count = 0
            sorted_ticks = list(self.time_signature_map.keys())
            sorted_ticks.sort()
            for key_tick in sorted_ticks:
                beats = self.time_signature_map[key_tick]

                delta_ticks = key_tick - current_tick
                delta_beats = delta_ticks / tpb
                measure_count += delta_beats // beats
                total_beats += delta_beats

                prev_beats = beats

            delta_ticks = tick - current_tick
            delta_beats = delta_ticks / tpb
            total_beats = delta_beats
            measure_count += delta_beats // prev_beats

            beat_in_measure = delta_beats % prev_beats

            subbeat = (0, 1)
            # Calculate subbeat
            denominators = [2,4,3,8,5,6,7]
            closest = (1, (0, 1))
            test_beat = round(beat_in_measure % 1, 2)
            found = False
            if test_beat != 0:
                for denom in denominators:
                    for i in range(1, denom):
                        test_val = round(i / denom, 2)
                        if (test_beat == test_val):
                            subbeat = (i, denom)
                            found = True
                            break
                        elif closest[0] > abs(test_val - test_beat):
                            closest = (abs(test_val - test_beat), (i, denom))
                    if found:
                        break

                if not found:
                    subbeat = closest[1]


            output = (int(beat_in_measure), subbeat, int(total_beats), int(measure_count))
            self._calculated_beatmeasures[tick] = output

        return output

