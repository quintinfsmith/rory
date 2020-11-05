'''Plays MIDILike Objects'''

import threading
from wrecked import RectScene, RectColor
from apres import MIDI, NoteOn, NoteOff


def gcd(a, b):
    bigger_int = max(a, b)
    smaller_int = min(a, b)

    while smaller_int:
        tmp = smaller_int
        smaller_int = bigger_int % smaller_int
        bigger_int = tmp
    return int(bigger_int)

def logg(*msg):
    with open('logg', 'a') as fp:
        for m in msg:
            fp.write(str(m) + "\n")

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

    def next_state(self):
        self.song_position += 1
        while self.song_position <= self.loop[1] and not self.midi_interface.get_state(self.song_position):
            self.song_position += 1

        self.song_position = min(self.loop[1] + 1, self.song_position)

        if self.song_position > self.loop[1]:
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
        self.song_position = max(0, song_position)

        while self.song_position < self.loop[1] and not self.midi_interface.get_state(self.song_position):
            self.song_position += 1

        self.song_position = min(self.loop[1], self.song_position)

        if self.song_position == self.loop[1]:
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

        self.active_midi = MIDI(kwargs['path'])

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

        self.__last_tick_was_beat = False
        self.active_row_position = 8
        self.rect_background = self.new_rect()
        self.layer_visible_notes = self.rect_background.new_rect()
        self.layer_active_notes = self.rect_background.new_rect()

        self.visible_note_rects = []
        self.pressed_note_rects = {}

        self.rect_position_display = self.new_rect()

        self.midi_input_thread = threading.Thread(
            target=self.midi_input_daemon
        )

        self.midi_input_thread.start()
        self.next_state()

    def midi_input_daemon(self):
        song_state = set()
        while self.is_active and self.midi_controller.connected:
            message = self.midi_controller.read()
            if message:
                if type(message) == NoteOn:
                    self.pressed_notes.add(message.note)
                    self.disp_flags[self.FLAG_PRESSED] = True
                elif type(message) == NoteOff:
                    try:
                        self.pressed_notes.remove(message.note)
                    except KeyError:
                        pass
                    try:
                        self.need_to_release.remove(message.note)
                    except KeyError:
                        pass
                    self.disp_flags[self.FLAG_PRESSED] = True
                song_state = self.midi_interface.get_state(self.song_position)

            if song_state.intersection(self.pressed_notes) == song_state and not self.need_to_release.intersection(song_state):
                self.need_to_release = self.need_to_release.union(self.pressed_notes)
                self.next_state()

    def tick(self):
        was_flagged = False
        if self.disp_flags[self.FLAG_BACKGROUND]:
            self.__draw_background()
            self.disp_flags[self.FLAG_BACKGROUND] = False
            was_flagged = True

        if self.disp_flags[self.FLAG_POSITION]:
            self.__draw_visible_notes()
            self.disp_flags[self.FLAG_POSITION] = False
            self.disp_flags[self.FLAG_PRESSED] = True
            was_flagged = True

        if self.disp_flags[self.FLAG_PRESSED]:
            self.__draw_pressed_row()
            self.disp_flags[self.FLAG_PRESSED] = False
            was_flagged = True

        if was_flagged:
            self.draw()

    def __draw_visible_notes(self):
        while self.visible_note_rects:
            self.visible_note_rects.pop().detach()

        for _y in range(self.layer_visible_notes.height):
            tick = self.song_position - self.active_row_position + _y

            if tick < 0 or tick >= len(self.midi_interface.state_map):
                continue

            if _y == self.active_row_position:
                y = self.rect_background.height - _y
            elif _y < self.active_row_position:
                y = self.rect_background.height - _y + 1
            else:
                y = self.rect_background.height - ((_y * 2) - self.active_row_position)


            row = self.midi_interface.active_notes_map[tick]
            blocked_xs = set()
            for _note, message in row.items():
                x = self.__get_displayed_key_position(message.note)
                blocked_xs.add(x)

                note_rect = self.layer_visible_notes.new_rect()
                note_rect.set_character(0, 0, self.NOTELIST[message.note % 12])
                note_rect.move(x, y)

                color = self.get_channel_color(message.channel)
                if message.note % 12 in self.SHARPS:
                    note_rect.set_bg_color(color)
                    note_rect.set_fg_color(RectColor.BLACK)
                else:
                    note_rect.set_fg_color(color)

                self.visible_note_rects.append(note_rect)

            # Draw Measure Lines
            if tick in self.midi_interface.measure_map.keys() and _y != self.active_row_position:
                for x in range(2, self.rect_background.width, 4):
                    if x in blocked_xs:
                        continue
                    if x % 14 == 0:
                        continue

                    line_rect = self.layer_visible_notes.new_rect()
                    line_rect.set_character(0, 0, '-')
                    line_rect.move(x, y)
                    line_rect.set_fg_color(RectColor.BRIGHTBLACK)

                    self.visible_note_rects.append(line_rect)

        position_string = "%s / %s" % (self.song_position, len(self.midi_interface.state_map))
        self.rect_position_display.resize(len(position_string), 1)
        self.rect_position_display.move(self.width - len(position_string) - 1, self.height - 1)
        self.rect_position_display.set_string(0, 0, position_string)

    def __draw_pressed_row(self):
        keys = list(self.pressed_note_rects.keys())
        for key in keys:
            self.pressed_note_rects[key].remove()
            del self.pressed_note_rects[key]

        active_state = self.midi_interface.get_state(self.song_position)

        y = self.height - self.active_row_position
        width = self.__get_displayed_key_position(self.note_range[1] + 1)

        pressed_notes = self.pressed_notes.copy()
        for note in pressed_notes:
            x = self.__get_displayed_key_position(note)

            note_rect = self.layer_active_notes.new_rect()
            #note_rect.set_character(0, 0, chr(9620))
            note_rect.set_character(0, 0, chr(9473))
            note_rect.move(x, 1)

            if note in self.need_to_release:
                if note in active_state:
                    note_rect.set_fg_color(RectColor.YELLOW)
                else:
                    note_rect.set_fg_color(RectColor.RED)
            else:
                if note in active_state:
                    note_rect.set_fg_color(RectColor.GREEN)
                else:
                    note_rect.set_fg_color(RectColor.RED)

            self.pressed_note_rects[note] = note_rect

    def __draw_background(self):
        width = self.__get_displayed_key_position(self.note_range[1] + 1)
        self.rect_background.set_fg_color(RectColor.BRIGHTBLACK)

        self.rect_background.resize(
            height = self.height,
            width = width
        )
        self.layer_visible_notes.resize(
            height=self.height,
            width = width
        )
        self.layer_visible_notes.set_transparency(True)

        background_pos = (self.width - width) // 2
        self.rect_background.move(background_pos, 0)

        y = self.height - self.active_row_position

        self.layer_active_notes.resize(self.rect_background.width, 2)
        self.layer_active_notes.move(0, y)
        self.layer_active_notes.set_transparency(True)

        for x in range(width):
            self.rect_background.set_character(x, y, chr(9473))

        for i in range(self.note_range[0], self.note_range[1]):
            x = self.__get_displayed_key_position(i)

            if i % 12 in self.SHARPS:
                self.rect_background.set_character(x, y - 1, chr(9608))
            else:
                self.rect_background.set_character(x, y + 1, chr(9620))

            if (i + 3) % 12 == 0:
                for j in range(0, y - 1):
                    self.rect_background.set_character(x, j, chr(9550))

                for j in range(y + 2, self.rect_background.height):
                    self.rect_background.set_character(x, j, chr(9550))

        for y in range(self.height):
            self.set_character(background_pos - 1, y, chr(9475))
            self.set_character(background_pos + width, y, chr(9475))

    def get_width(self):
        return (self.note_range[1] - self.note_range[0]) + 2

    @staticmethod
    def get_channel_color(channel):
        colors = [
            RectColor.BRIGHTYELLOW,
            RectColor.WHITE,
            RectColor.CYAN,
            RectColor.GREEN,
            RectColor.MAGENTA,
            RectColor.BLUE,
            RectColor.BRIGHTBLACK, # i *think* it's channel 7 that is drums... if so, this is just a placeholder
            RectColor.RED
        ]
        color = colors[channel % 8]

        if channel > 8:
            color ^= RectColor.BRIGHT

        return color

    def __get_displayed_key_position(self, midi_key):
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

    def set_register_digit(self, digit):
        assert (digit < 10), "Digit can't be more than 9. set_register is being called from somewhere it shouldn't."

        self.register *= 10
        self.register += digit

    def clear_register(self):
        self.register = 0

    def jump_to_register_position(self):
        self.set_state(self.register)
        self.clear_register()


class MIDIInterface:
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
                t = tick //self.midi.ppqn

                while len(beats) <= t:
                    beats.append([])

                beats[t].append((tick % self.midi.ppqn, event))



        maximum_definition = 4
        minimum_definition = 1
        tick_counter = 0
        for beat, events in enumerate(beats):
            biggest = self.midi.ppqn // minimum_definition
            for pos, _ in events:
                if pos == 0:
                    pos = self.midi.ppqn
                biggest = gcd(biggest, pos)

            biggest = max(self.midi.ppqn // maximum_definition, biggest) # If biggest < MAXDEF, will lose precision
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
        return self.state_map[tick].copy()


