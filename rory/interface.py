'''Interface between user and player'''
import threading
import time
import wrecked
from wrecked import get_terminal_size
from apres import MIDI, InvalidMIDIFile

from rory.midicontroller import MIDIController
from rory.player import Player
from rory.interactor import Interactor

class TerminalTooNarrow(Exception):
    '''Error thrown when the minimum width required isn't available'''

class RoryStage:
    '''Interface to Run the MidiPlayer'''
    CONTEXT_DEFAULT = 0
    CONTEXT_PLAYER = 1
    def __init__(self):
        self.root = wrecked.init()
        self.scenes = {}
        self.active_scene = None

        if self.root.width < 106:
            self.kill()
            raise TerminalTooNarrow()

        self.interactor = Interactor()
        self.midi_controller = MIDIController()
        self.interactor.assign_context_sequence(
            self.CONTEXT_DEFAULT,
            'q',
            self.kill
        )

        self.delay = 1/24

        self.playing = False

        self.playerscene = None

    def set_fps(self, fps):
        self.delay = 1 / fps

    def key_scene(self, key, scene):
        self.scenes[key] = scene

    def play_along(self, midi_path, **kwargs):
        '''Run the Player with the loaded MidiLike Object'''

        if not self.playerscene:
            if 'transpose' in kwargs:
                transpose = kwargs['transpose']
            else:
                transpose = 0
            scene = PlayerScene(
                self,
                path=midi_path,
                controller=self.midi_controller,
                transpose=transpose
            )
            self.key_scene(self.CONTEXT_PLAYER, scene)
            thread = threading.Thread(target=self._input_daemon)
            thread.start()

        playerscene = self.scenes[self.CONTEXT_PLAYER]
        player = playerscene.player

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'j',
            player.next_state
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'k',
            player.prev_state
        )

        for digit in range(10):
            self.interactor.assign_context_sequence(
                self.CONTEXT_PLAYER,
                str(digit),
                player.set_register_digit,
                digit
            )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'p',
            player.jump_to_register_position,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            '[',
            player.set_loop_start_to_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            ']',
            player.set_loop_end_to_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            '\\',
            player.clear_loop,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'q',
            self.kill
        )

        self.interactor.set_context(self.CONTEXT_PLAYER)
        self.start_scene(self.CONTEXT_PLAYER)


    def kill(self):
        self.playing = False

        for scene in self.scenes.values():
            scene.kill()
        wrecked.kill()


    def _input_daemon(self):
        '''Main loop, just handles computer keyboard input'''

        while self.playing:
            self.interactor.get_input()

    def resize(self, width, height):
        self.root.resize(width, height)
        try:
            scene = self.scenes[self.active_scene]
        except KeyError:
            scene = None

        if scene:
            scene.resize(width, height)

    def _resize_check(self):
        if wrecked.fit_to_terminal():
            w, h = get_terminal_size()
            self.resize(w, h)

    def play(self):
        self.playing = True

        #thread = threading.Thread(target=self._input_daemon)
        #thread.start()
        play_thread = threading.Thread(target=self._play)
        play_thread.start()


    def _play(self):
        while self.playing:
            self._resize_check()

            try:
                scene = self.scenes[self.active_scene]
            except KeyError:
                scene = None

            if scene:
                try:
                    if scene.tick():
                        scene.draw()
                except Exception as e:
                    self.kill()
                    raise e
            time.sleep(self.delay)

    def start_scene(self, new_scene_key):
        if self.active_scene:
            self.scenes[self.active_scene].disable()

        self.active_scene = new_scene_key
        self.scenes[self.active_scene].enable()
        self.root.draw()

    def new_rect(self):
        rect = self.root.new_rect()
        rect.resize(self.root.width, self.root.height)
        return rect

class RoryScene:
    def __init__(self, rorystage):
        self.root = rorystage.new_rect()

    def disable(self):
        self.root.disable()

    def enable(self):
        self.root.enable()

    def draw(self):
        self.root.draw()

    def tick(self):
        pass

    def kill(self):
        pass

    def resize(self, new_width, new_height):
        self.root.resize(new_width, new_height)

class PlayerScene(RoryScene):
    '''Handles visualization of the Player'''
    # Display constants
    SHARPS = (1, 3, 6, 8, 10)
    NOTELIST = 'CCDDEFFGGAAB'

    def __init__(self, rorystage, **kwargs):
        super().__init__(rorystage)

        self.active_midi = MIDI(kwargs['path'])
        self.midi_controller = kwargs['controller']

        self.rect_inner = self.root.new_rect()
        self.rect_background = self.rect_inner.new_rect()

        self.layer_visible_notes = self.rect_background.new_rect()
        self.rect_loop_start = self.layer_visible_notes.new_rect()
        self.rect_loop_end = self.layer_visible_notes.new_rect()

        self.layer_active_notes = self.rect_background.new_rect()

        self.visible_note_rects = []
        self.pressed_note_rects = {}

        self.rect_position_display = self.rect_background.new_rect()
        self.rect_position_display.bold()
        self.rect_position_display.underline()
        self.rect_chord_names = self.rect_background.new_rect()
        self.rect_chord_names.bold()
        self.rect_chord_names.underline()

        self.active_row_position = 8
        self.player = Player(**kwargs)

        self.FLAG_BACKGROUND = True
        self.last_rendered_pressed = None
        self.last_rendered_position = -1
        self.last_rendered_loop = (0, 0)

    def tick(self):
        was_flagged = False
        player = self.player
        if self.FLAG_BACKGROUND:
            self.__draw_background()
            self.FLAG_BACKGROUND = False
            was_flagged = True

        song_position = player.song_position
        if self.last_rendered_position != song_position or self.last_rendered_loop != player.loop:
            self.__draw_visible_notes()
            self.__draw_chord_name()
            self.last_rendered_position = song_position
            self.last_rendered_pressed = None
            was_flagged = True

        if player.pressed_notes != self.last_rendered_pressed:
            self.__draw_pressed_row()
            was_flagged = True

        return was_flagged

    def __draw_chord_name(self):
        midi_interface = self.player.midi_interface
        active_channels = midi_interface.get_active_channels(self.player.song_position)
        chord_names = []
        for channel in active_channels:
            chord_name = midi_interface.get_chord_name(self.player.song_position, channel)
            if chord_name:
                chord_names.append(chord_name)

        chord_string = " | ".join(chord_names)
        self.rect_chord_names.resize(len(chord_string), 1)
        self.rect_chord_names.move(0, self.rect_background.height - 1)
        self.rect_chord_names.set_string(0, 0, chord_string)

    def __draw_visible_notes(self):
        while self.visible_note_rects:
            self.visible_note_rects.pop().remove()

        self.rect_loop_start.disable()
        self.rect_loop_end.disable()

        song_position = self.player.song_position
        midi_interface = self.player.midi_interface
        state_map = midi_interface.state_map

        for _y in range(self.layer_visible_notes.height):
            tick = song_position - self.active_row_position + _y

            if tick < 0 or tick >= len(state_map):
                continue

            if _y == self.active_row_position:
                y = self.rect_background.height - _y
            elif _y < self.active_row_position:
                y = self.rect_background.height - _y + 1
            else:
                y = self.rect_background.height - ((_y * 2) - self.active_row_position)


            row = midi_interface.active_notes_map[tick]
            blocked_xs = set()
            for _, message in row.items():
                x = self.__get_displayed_key_position(message.note)
                blocked_xs.add(x)

                note_rect = self.layer_visible_notes.new_rect()
                note_rect.set_character(0, 0, self.NOTELIST[message.note % 12])
                note_rect.move(x, y)

                color = self.get_channel_color(message.channel)
                if message.note % 12 in self.SHARPS:
                    note_rect.set_bg_color(color)
                    note_rect.set_fg_color(wrecked.BLACK)
                else:
                    note_rect.set_fg_color(color)

                self.visible_note_rects.append(note_rect)

            # Draw Measure Lines
            if tick in midi_interface.measure_map.keys() and _y != self.active_row_position:
                for x in range(2, self.rect_background.width, 4):
                    if x in blocked_xs:
                        continue
                    if x % 14 == 0:
                        continue

                    line_rect = self.layer_visible_notes.new_rect()
                    line_rect.set_character(0, 0, '-')
                    line_rect.move(x, y)
                    line_rect.set_fg_color(wrecked.BRIGHTBLACK)

                    self.visible_note_rects.append(line_rect)

            if tick == self.player.loop[0]:
                self.rect_loop_start.enable()
                if _y != self.active_row_position:
                    self.rect_loop_start.move(0, y + 1)
                else:
                    self.rect_loop_start.move(0, y + 2)
                self.rect_loop_start.resize(self.rect_background.width, 1)
                string = chr(9473) * self.rect_loop_start.width
                self.rect_loop_start.set_string(0, 0, string)

            if tick == self.player.loop[1]:
                self.rect_loop_end.enable()
                if _y != self.active_row_position:
                    self.rect_loop_end.move(0, y - 1)
                else:
                    self.rect_loop_end.move(0, y - 2)
                self.rect_loop_end.resize(self.rect_background.width, 1)
                string = chr(9473) * self.rect_loop_end.width
                self.rect_loop_end.set_string(0, 0, string)


        # Active Row Line
        active_y = self.rect_background.height - self.active_row_position
        if song_position in midi_interface.measure_map.keys():
            line_char = chr(9552)
        else:
            line_char = chr(9472)

        for x in range(self.rect_background.width):
            self.rect_background.set_character(x, active_y, line_char)

        self.__draw_song_position()

    def __draw_song_position(self):
        song_position = self.player.song_position
        midi_interface = self.player.midi_interface
        state_map = midi_interface.state_map

        if self.player.loop != [0, len(state_map) - 1]:
            l = len(str(max(self.player.loop)))
            fmt_string = "[%%0%dd: %%0%dd :%%0%dd]" % (l, l, l)
            position_string = fmt_string % (self.player.loop[0], song_position, self.player.loop[1])
        else:
            l = len(str(len(state_map)))
            fmt_string = "%%0%dd/%%0%dd" % (l, l)
            position_string = fmt_string % (song_position, len(state_map))

        self.rect_position_display.resize(len(position_string), 1)
        self.rect_position_display.move(max(0, self.rect_background.width - len(position_string)), self.rect_background.height - 1)
        self.rect_position_display.set_string(0, 0, position_string)
        self.last_rendered_loop = self.player.loop.copy()

    def __draw_pressed_row(self):
        keys = list(self.pressed_note_rects.keys())
        for key in keys:
            self.pressed_note_rects[key].remove()
            del self.pressed_note_rects[key]

        player = self.player
        midi_interface = player.midi_interface
        song_position = player.song_position

        active_state = midi_interface.get_state(song_position)

        y = self.rect_inner.height - self.active_row_position

        pressed_notes = player.pressed_notes.copy()
        for note in pressed_notes:
            x = self.__get_displayed_key_position(note)

            note_rect = self.layer_active_notes.new_rect()
            note_rect.set_character(0, 0, chr(9473))
            note_rect.move(x, 1)

            if note in player.need_to_release:
                if note in active_state:
                    note_rect.set_fg_color(wrecked.YELLOW)
                else:
                    note_rect.set_fg_color(wrecked.RED)
            else:
                if note in active_state:
                    note_rect.set_fg_color(wrecked.GREEN)
                else:
                    note_rect.set_fg_color(wrecked.RED)

            self.pressed_note_rects[note] = note_rect

        self.last_rendered_pressed = pressed_notes

    def __adjust_inner_rect_offset(self):
        player = self.player
        note_range = player.note_range
        width = self.__get_displayed_key_position(note_range[1] + 1)

        self.rect_inner.resize(
            height=self.root.height,
            width=width
        )
        inner_pos = max(0, (self.root.width - self.rect_inner.width) // 2)
        self.rect_inner.move(inner_pos, 0)

        for y in range(self.root.height):
            self.root.set_character(inner_pos - 1, y, chr(9475))
            self.root.set_character(inner_pos + width, y, chr(9475))

    def __draw_background(self):
        player = self.player
        note_range = player.note_range
        self.__adjust_inner_rect_offset()

        self.rect_background.clear_characters()
        self.rect_background.set_fg_color(wrecked.BRIGHTBLACK)
        self.rect_background.resize(
            height=self.rect_inner.height,
            width=self.rect_inner.width
        )

        self.layer_visible_notes.resize(
            height=self.rect_background.height,
            width=self.rect_background.width
        )
        self.layer_visible_notes.set_transparency(True)


        y = max(0, self.root.height - self.active_row_position)
        self.layer_active_notes.resize(self.rect_background.width, 2)
        self.layer_active_notes.move(0, y)
        self.layer_active_notes.set_transparency(True)

        for i in range(note_range[0], note_range[1]):
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



    def __get_displayed_key_position(self, midi_key):
        piano_position = midi_key - self.player.note_range[0]
        octave = piano_position // 12
        piano_key = piano_position % 12
        position = (octave * 14) + piano_key

        if piano_key > 2: # B
            position += 1
        if piano_key > 7:
            position += 1

        return position

    @staticmethod
    def get_channel_color(channel):
        colors = [
            wrecked.BRIGHTYELLOW,
            wrecked.WHITE,
            wrecked.CYAN,
            wrecked.GREEN,
            wrecked.MAGENTA,
            wrecked.BLUE,
             # i *think* it's channel 7 that is drums... if so, this is just a placeholder
            wrecked.BRIGHTBLACK,
            wrecked.RED
        ]
        color = colors[channel % 8]

        if channel > 8:
            color ^= wrecked.BRIGHT

        return color

    def kill(self):
        ''' Tear down the player backend '''
        if self.player:
            self.player.kill()

    def resize(self, new_width, new_height):
        super().resize(max(new_width, self.rect_inner.width + 2), new_height)
        self.FLAG_BACKGROUND = True
        self.last_rendered_position = -1

    def draw(self):
        super().draw()
        #self.rect_inner.draw()

