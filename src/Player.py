'''Plays MIDILike Objects'''

from wrecked import RectScene, Rect
import threading
import math, time
from apres import MIDI, TimeSignatureEvent, NoteOnEvent, NoteOffEvent, SetTempoEvent


def gcd(a, b):
    while b:
        t = b
        b = a % b
        a = t
    return int(a)

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
        song_state = set()
        while self.is_active and self.midi_controller.connected:
            message = self.midi_controller.read()
            if message:
                if message.type == 'note_on':
                    self.pressed_notes.add(message.note)
                    self.disp_flags[self.FLAG_PRESSED] = True
                elif message.type == 'note_off':
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
            blocked_xs = set()
            for note, message in row.items():
                x = self.get_displayed_key_position(message.note)
                blocked_xs.add(x)
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

            # Draw Measure Lines
            if tick in self.midi_interface.measure_map.keys() and _y != self.active_row_position:
                for x in range(0, self.rect_background.width, 3):
                    if x in blocked_xs:
                        continue

                    line_rect = self.rect_background.new_rect()
                    line_rect.set_character(0, 0, '-')
                    line_rect.move(x, y)
                    line_rect.set_fg_color(Rect.BRIGHTBLACK)

                    self.visible_note_rects.append(line_rect)

        position_string = "%s / %s" % (self.song_position, len(self.midi_interface.state_map))
        self.rect_position_display.resize(len(position_string), 1)
        self.rect_position_display.move(self.width - len(position_string) - 1, self.height - 1)
        self.rect_position_display.set_string(0, 0, position_string)



    def draw_pressed_row(self):
        while self.pressed_note_rects:
            self.pressed_note_rects.pop().detach()

        active_state = self.midi_interface.get_state(self.song_position)
        y = self.rect_background.height - self.active_row_position

        pressed_notes = self.pressed_notes.copy()
        for note in pressed_notes:
            if note in self.need_to_release:
                continue

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
        for x in range(width):
            self.rect_background.set_character(x, y, chr(9473))

        for i in range(self.note_range[0], self.note_range[1]):
            x = self.get_displayed_key_position(i)
            if i % 12 in self.SHARPS:
                self.rect_background.set_character(x, y - 1, chr(9608))
                #self.rect_background.set_character(x, y, chr(9474))
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

        current_tempo = 0
        tmp_states = []
        measure_sizes = []
        self.measure_map = {} # { state_position: measure_number }


        beats = []
        for i, (tick, event) in enumerate(self.midi.get_all_events()):
            if event.__class__ == NoteOnEvent and event.channel != 9 and event.velocity > 0:
                t = tick //self.midi.ppqn

                while len(beats) <= t:
                    beats.append([])

                beats[t].append((tick % self.midi.ppqn, event))


        MAXDEF = 4
        MINDEF = 1
        tick_counter = 0
        for beat, events in enumerate(beats):
            biggest = self.midi.ppqn // MINDEF
            for pos, _ in events:
                if pos == 0:
                    pos = self.midi.ppqn
                a = max(pos, biggest)
                b = min(pos, biggest)
                biggest = gcd(a, b)


            biggest = max(self.midi.ppqn // MAXDEF, biggest) # If biggest < MAXDEF, will lose precision
            definition = self.midi.ppqn // biggest

            tmp_ticks = []
            for i in range(definition):
                tmp_ticks.append([])

            for pos, event in events:
                tmp_ticks[pos // biggest].append(event)

            self.measure_map[tick_counter] = beat
            for events in tmp_ticks:
                for event in events:
                    while len(self.state_map) <= tick_counter:
                        self.state_map.append(set())
                        self.active_notes_map.append({})
                    self.state_map[tick_counter].add(event.note)
                    self.active_notes_map[tick_counter][event.note] = event
                tick_counter += 1




    def get_state(self, tick):
        return self.state_map[tick].copy()


