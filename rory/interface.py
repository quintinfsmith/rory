'''Interface between user and player'''
from __future__ import annotations
import threading
import time
import wrecked
from wrecked import get_terminal_size, Rect
from apres import MIDI, InvalidMIDIFile
from rory.player import Player
from rory.interactor import Interactor
from typing import Final

class TerminalTooNarrow(Exception):
    '''Error thrown when the minimum width required isn't available'''

class RoryStage:
    '''Interface to Run the MidiPlayer'''
    CONTEXT_DEFAULT = 0
    CONTEXT_PLAYER = 1

    CONTROL_QUIT = 'q'
    CONTROL_NEXT_STATE = 'j'
    CONTROL_PREV_STATE = 'k'
    CONTROL_IGNORE_CHANNEL = 'i'
    CONTROL_UNIGNORE_CHANNELS ='u'
    CONTROL_TRANSPOSE = 't'
    CONTROL_LOOP_START = '['
    CONTROL_LOOP_END = ']'
    CONTROL_LOOP_KILL = '\\'
    CONTROL_CLEAR_REGISTER = '\x1b'
    CONTROL_TOGGLE_HELP = 'h'
    CONTROL_SET_POSITION = 'p'
    CONTROL_SET_MEASURE = 'P'
    CONTROL_SET_RANGE = 'r'

    def __init__(self):
        self.root = wrecked.init()
        self.scenes = {}
        self.active_scene = None

        if self.root.width < 106:
            self.kill()
            raise TerminalTooNarrow()

        self.interactor = Interactor()
        self.interactor.assign_context_sequence(
            self.CONTEXT_DEFAULT,
            self.CONTROL_QUIT,
            self.kill
        )

        self.delay = 1/64

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
                transpose=transpose
            )
            self.key_scene(self.CONTEXT_PLAYER, scene)
            thread = threading.Thread(target=self._input_daemon)
            thread.start()

        playerscene = self.scenes[self.CONTEXT_PLAYER]
        player = playerscene.player

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_NEXT_STATE,
            player.next_state
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_IGNORE_CHANNEL,
            playerscene.ignore_channel
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_UNIGNORE_CHANNELS,
            playerscene.unignore_channels
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_PREV_STATE,
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
            '-',
            player.set_register_digit,
            ord('-')
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_CLEAR_REGISTER,
            player.clear_register
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_TOGGLE_HELP,
            playerscene.toggle_help_menu
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_SET_POSITION,
            player.jump_to_register_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_SET_MEASURE,
            playerscene.jump_to_register_measure,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_LOOP_START,
            player.set_loop_start_to_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_LOOP_END,
            player.set_loop_end_to_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_LOOP_KILL,
            player.clear_loop,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_TRANSPOSE,
            playerscene.reset_transpose,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_QUIT,
            self.kill
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            self.CONTROL_SET_RANGE,
            playerscene.flag_new_range
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
    SHARPS: Final[tuple[int]] = (1, 3, 6, 8, 10)
    NOTELIST: Final[str] = 'CCDDEFFGGAAB'

    COLORORDER: Final[list[int]] = [
        wrecked.BLUE,
        wrecked.CYAN,
        wrecked.WHITE,
        wrecked.MAGENTA,
        wrecked.YELLOW,
        wrecked.BRIGHTBLUE,
        wrecked.BRIGHTCYAN,
        wrecked.BRIGHTWHITE,
        wrecked.BRIGHTMAGENTA,
        wrecked.BRIGHTYELLOW
    ]

    CHARS = {
        'measureline': chr(9590),
        'loopline': chr(9473),
        'activeline_measure': chr(9552),
        'activeline_beat': chr(9472),
        'activeline': chr(9548) ,
        'sidepane': chr(9475),
        'keyboard_sharp': chr(9608),
        'keyboard_natural': chr(9620),
        'keyboard_pressed': chr(9473),
        'a_line': chr(9550),
        'menu': {
            'top': chr(9552),
            'bottom': chr(9552),
            'left': chr(9553),
            'right': chr(9553),
            'top_left': chr(9556),
            'top_right': chr(9559),
            'bottom_left': chr(9562),
            'bottom_right': chr(9565)
        }
    }

    def __init__(self, rorystage: RoryStage, **kwargs):
        super().__init__(rorystage)

        self.active_midi = MIDI(kwargs['path'])

        self.rect_inner = self.root.new_rect()
        self.rect_background = self.rect_inner.new_rect()

        self.layer_visible_notes = self.rect_background.new_rect()
        self.rect_loop_start = self.layer_visible_notes.new_rect()
        self.rect_loop_end = self.layer_visible_notes.new_rect()

        self.layer_active_notes = self.rect_background.new_rect()

        self.visible_note_rects = {}
        self.visible_note_rects_lines = {}
        self.pressed_note_rects = {}

        self.rect_position_display = self.rect_background.new_rect()
        self.rect_position_display.bold()
        self.rect_position_display.underline()
        self.rect_position_display.set_bg_color(wrecked.BLACK)
        self.rect_position_display.set_fg_color(wrecked.WHITE)
        self.rect_chord_names = self.rect_background.new_rect()
        self.rect_chord_names.bold()
        self.rect_chord_names.underline()
        self.rect_chord_names.set_bg_color(wrecked.BLACK)
        self.rect_chord_names.set_fg_color(wrecked.WHITE)

        self.rect_background.set_bg_color(wrecked.BLACK)
        self.rect_background.set_fg_color(wrecked.BRIGHTBLACK)
        self.rect_loop_start.set_bg_color(wrecked.BLACK)
        self.rect_loop_end.set_bg_color(wrecked.BLACK)
        self.rect_loop_start.set_fg_color(wrecked.BRIGHTWHITE)
        self.rect_loop_end.set_fg_color(wrecked.BRIGHTWHITE)

        self.active_row_position = 8
        self.player = Player(**kwargs)

        self.FLAG_BACKGROUND = True
        self.last_rendered_pressed = None
        self.last_rendered_transpose = None
        self.last_rendered_position = -1
        self.last_rendered_loop = (0, 0)
        self.last_rendered_ignored_channels = None
        self.last_rendered_note_range = self.player.note_range
        self.rect_help_menu = None
        self.flag_show_menu = False

        self.mapped_colors = {}
        self.rechanneled = {}

    def flag_new_range(self):
        self.player.flag_new_range()

    def reset_transpose(self):
        register = self.player.get_register()
        self.player.reinit_midi_interface(
            transpose=register
        )

    def has_transpose_changed(self):
        current = self.player.get_transpose()
        output = current != self.last_rendered_transpose
        if (output):
            self.last_rendered_transpose = current

        return output

    def has_note_range_changed(self):
        return self.last_rendered_note_range != self.player.note_range

    def tick(self):
        was_flagged = False
        player = self.player
        note_range_changed = self.has_note_range_changed()
        transpose_changed = self.has_transpose_changed()
        if self.FLAG_BACKGROUND or note_range_changed or transpose_changed:
            self.__draw_background()
            self.FLAG_BACKGROUND = False
            was_flagged = True

        song_position = player.song_position
        if self.last_rendered_position != song_position or self.last_rendered_loop != player.loop or self.last_rendered_ignored_channels != self.player.ignored_channels or note_range_changed or transpose_changed:
            self.__draw_visible_notes()
            self.__draw_chord_name()
            self.last_rendered_position = song_position
            self.last_rendered_pressed = None
            self.last_rendered_ignored_channels = self.player.ignored_channels.copy()
            was_flagged = True

        if self.get_pressed_notes() != self.last_rendered_pressed:
            self.__draw_pressed_row()
            was_flagged = True

        if self.flag_show_menu and was_flagged:
            self.flag_show_menu = False

        if self.flag_show_menu:
            if not self.rect_help_menu:
                self.draw_help_menu()
                was_flagged = True
            if not self.rect_help_menu.enabled:
                self.rect_help_menu.enable()
                was_flagged = True
        elif not self.flag_show_menu:
            if self.rect_help_menu and self.rect_help_menu.enabled:
                was_flagged = True
                self.rect_help_menu.disable()

        return was_flagged

    def toggle_help_menu(self):
        self.flag_show_menu = not self.flag_show_menu

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
        self.rect_loop_start.disable()
        self.rect_loop_end.disable()

        song_position = self.player.song_position
        midi_interface = self.player.midi_interface
        state_map = midi_interface.state_map
        cache_keys_used = set()
        used_lines = set()
        for _y in range(self.layer_visible_notes.height):
            position = song_position - self.active_row_position + _y

            if position < 0 or position >= len(state_map):
                continue

            # Warp y-spacing based on if tick is active, upcoming or passed
            if _y == self.active_row_position:
                y = self.rect_background.height - _y
            elif _y < self.active_row_position:
                y = self.rect_background.height - _y + 1
            else:
                y = self.rect_background.height - ((_y * 2) - self.active_row_position)


            row = midi_interface.active_notes_map[position]
            blocked_xs = set()
            for _, message in row.items():
                if message.note < self.player.note_range[0] or message.note > self.player.note_range[1]:
                    continue
                color = self.get_channel_color(message.channel)
                # include color in cachekey for 'ignored'
                cachekey = (message.channel, color, message.note, position)
                cache_keys_used.add(cachekey)
                x = self.__get_displayed_key_position(message.note)
                blocked_xs.add(x)

                # Don't need to create and color a new rect if one already exists
                try:
                    note_rect = self.visible_note_rects[cachekey]
                except KeyError:
                    note_rect = self.layer_visible_notes.new_rect()
                    self.visible_note_rects[cachekey] = note_rect
                    note_rect.set_character(0, 0, self.NOTELIST[message.note % 12])
                    if message.note % 12 in self.SHARPS:
                        note_rect.set_bg_color(color)
                        note_rect.set_fg_color(wrecked.BLACK)
                    else:
                        note_rect.set_fg_color(color)
                        note_rect.set_bg_color(wrecked.BLACK)

                note_rect.move(x, y)

            # Draw Measure Lines
            if position in midi_interface.beat_map.keys() and _y != self.active_row_position:
                line_char = self.CHARS['measureline']
                if position in midi_interface.measure_map:
                    base = 1
                else:
                    base = 3
                for x in range(1, self.rect_background.width, base):
                    if x in blocked_xs:
                        continue
                    used_lines.add((position, x))

                    try:
                        line_rect = self.visible_note_rects_lines[(position, x)]
                    except KeyError:
                        line_rect = self.layer_visible_notes.new_rect()
                        line_rect.set_character(0, 0, line_char)
                        line_rect.set_fg_color(wrecked.BRIGHTBLACK)
                        line_rect.set_bg_color(wrecked.BLACK)
                        self.visible_note_rects_lines[(position, x)] = line_rect
                    line_rect.move(x, y)


            if position == self.player.loop[0]:
                self.rect_loop_start.enable()
                if _y != self.active_row_position:
                    self.rect_loop_start.move(0, y + 1)
                else:
                    self.rect_loop_start.move(0, y + 2)
                self.rect_loop_start.resize(self.rect_background.width, 1)
                string = self.CHARS['loopline'] * self.rect_loop_start.width
                self.rect_loop_start.set_string(0, 0, string)

            if position == self.player.loop[1]:
                self.rect_loop_end.enable()
                if _y != self.active_row_position:
                    self.rect_loop_end.move(0, y - 1)
                else:
                    self.rect_loop_end.move(0, y - 2)
                self.rect_loop_end.resize(self.rect_background.width, 1)
                string = self.CHARS['loopline'] * self.rect_loop_end.width
                self.rect_loop_end.set_string(0, 0, string)

        # Active Row Line
        active_y = self.rect_background.height - self.active_row_position
        if song_position in midi_interface.measure_map: # ═
            line_char = self.CHARS['activeline_measure']
        elif song_position in midi_interface.beat_map: # ─
            line_char = self.CHARS['activeline_beat']
        else:
            line_char = self.CHARS['activeline']

        for x in range(self.rect_background.width):
            self.rect_background.set_character(x, active_y, line_char)

        unused_cache_keys = set(self.visible_note_rects.keys()) - cache_keys_used
        for key in unused_cache_keys:
            self.visible_note_rects[key].remove()
            del self.visible_note_rects[key]

        unused_lines = set(self.visible_note_rects_lines.keys()) - used_lines
        for key in unused_lines:
            self.visible_note_rects_lines[key].remove()
            del self.visible_note_rects_lines[key]

        self.__draw_song_position()

    def __get_measure(self, song_position):
        return self.player.midi_interface.get_measure(song_position) + 1

    def __draw_song_position(self):
        song_position = self.player.song_position
        midi_interface = self.player.midi_interface
        state_map = midi_interface.state_map
        if self.player.loop != [0, len(state_map) - 1]:
            l = len(str(max(self.player.loop)))
            fmt_string = "[%%0%dd: %%0%dd :%%0%dd]" % (l, l, l)
            position_string = fmt_string % (self.player.loop[0], song_position, self.player.loop[1])

            min_measure = self.__get_measure(self.player.loop[0])
            max_measure = self.__get_measure(self.player.loop[1])
            l = len(str(max_measure))
            fmt_string = "[%%0%dd: %%0%dd :%%0%dd]" % (l, l, l)
            measure_string = fmt_string % (min_measure, self.__get_measure(song_position), max_measure)
        else:
            l = len(str(len(state_map)))
            fmt_string = "%%0%dd/%%0%dd" % (l, l)
            position_string = fmt_string % (song_position, len(state_map))

            max_measure = self.__get_measure(len(state_map))
            l = len(str(max_measure))
            fmt_string = "%%0%dd/%%0%dd" % (l, l)
            measure_string = fmt_string % (self.__get_measure(song_position), max_measure)

        self.rect_position_display.resize(len(position_string), 2)
        self.rect_position_display.move(max(0, self.rect_background.width - len(position_string)), self.rect_background.height - 2)
        self.rect_position_display.set_string(len(position_string) - len(measure_string), 0, measure_string)
        self.rect_position_display.set_string(0, 1, position_string)
        self.last_rendered_loop = self.player.loop.copy()

    def get_pressed_notes(self):
        notes = self.player.get_pressed_notes()
        return notes

    def __draw_pressed_row(self):
        player = self.player
        midi_interface = player.midi_interface
        song_position = player.song_position
        pressed_notes = self.get_pressed_notes()

        keys = list(self.pressed_note_rects.keys())
        for key in keys:
            self.pressed_note_rects[key].remove()
            del self.pressed_note_rects[key]

        active_state = midi_interface.get_state(song_position)

        y = self.rect_inner.height - self.active_row_position

        for note in pressed_notes:
            x = self.__get_displayed_key_position(note)

            note_rect = self.layer_active_notes.new_rect()
            note_rect.set_character(0, 0, self.CHARS['keyboard_pressed'])
            note_rect.set_bg_color(wrecked.BLACK)
            note_rect.move(x, 1)
            self.pressed_note_rects[note] = note_rect

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

        self.last_rendered_pressed = pressed_notes

    def __adjust_inner_rect_offset(self):
        self.root.clear_characters()

        player = self.player
        note_range = player.note_range
        width = self.__get_displayed_key_position(note_range[1]) + 1

        self.rect_inner.resize(
            height=self.root.height,
            width=width
        )

        inner_pos = max(0, (self.root.width - self.rect_inner.width) // 2)
        self.rect_inner.move(inner_pos, 0)

        for y in range(self.root.height):
            self.root.set_character(inner_pos - 1, y, self.CHARS['sidepane'])
            self.root.set_character(inner_pos + width, y, self.CHARS['sidepane'])

        self.last_rendered_note_range = note_range

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
                self.rect_background.set_character(x, y - 1, self.CHARS['keyboard_sharp'])
            else:
                self.rect_background.set_character(x, y + 1, self.CHARS['keyboard_natural'])

            if (i + 3) % 12 == 0:
                for j in range(0, y - 1):
                    self.rect_background.set_character(x, j, self.CHARS['a_line'])

                for j in range(y + 2, self.rect_background.height):
                    self.rect_background.set_character(x, j, self.CHARS['a_line'])

    def draw_help_menu(self):
        if not self.rect_help_menu:
            self.rect_help_menu = self.root.new_rect()

        menu = self.rect_help_menu

        descriptions = [
            (RoryStage.CONTROL_QUIT, "Close Rory"),
            (RoryStage.CONTROL_TOGGLE_HELP, "Toggle this pop up"),
            ("0-9", "Set register"),
            ("ESC", "Clear register"),
            (RoryStage.CONTROL_NEXT_STATE, "Next state"),
            (RoryStage.CONTROL_PREV_STATE, "Previous state"),
            (RoryStage.CONTROL_IGNORE_CHANNEL, "Ignore the channel in register"),
            (RoryStage.CONTROL_UNIGNORE_CHANNELS, "Unignore all channels"),
            (RoryStage.CONTROL_SET_POSITION, "Jump to state in register"),
            (RoryStage.CONTROL_SET_RANGE, "resize keyboard ( Then press lowest and highest keys )"),
            (RoryStage.CONTROL_TRANSPOSE, "transpose the entire song by the register"),
            (RoryStage.CONTROL_LOOP_START, "Set start of loop"),
            (RoryStage.CONTROL_LOOP_END, "Set end of loop"),
            (RoryStage.CONTROL_LOOP_KILL, "Clear start & end of loop")
        ]

        lines = [
            "Controls",
            "",
        ]
        for desc in descriptions:
            lines.append("%s    - %s" % desc)


        new_height = min(self.root.height - 2, len(lines) + 2)
        menu.resize(int(self.root.width / 1.5), new_height)
        menu.move((self.root.width - menu.width) // 2, (self.root.height - menu.height) // 2)
        menu_assets = self.CHARS['menu']
        # Draw border
        for y in range(1, menu.height - 1):
            menu.set_character(0, y, menu_assets['left'])
            menu.set_character(menu.width - 1, y, menu_assets['right'])

        for x in range(1, menu.width - 1):
            menu.set_character(x, 0, menu_assets['top'])
            menu.set_character(x, menu.height - 1, menu_assets['bottom'])

        menu.set_character(0,0, menu_assets['top_left'])
        menu.set_character(menu.width - 1, menu.height - 1, menu_assets['bottom_right'])
        menu.set_character(0,menu.height - 1, menu_assets['bottom_left'])
        menu.set_character(menu.width - 1, 0, menu_assets['top_right'])


        # Add the content
        for i, line in enumerate(lines):
            menu.set_string(2, 1 + i, line)

    def __get_displayed_key_position(self, midi_key):
        # TODO: Make me more effecient
        position = 0
        for i in range(self.player.note_range[0], midi_key):
            if i in (2, 7):
                position += 1
            position += 1
        return position

    def ignore_channel(self):
        try:
            channel = self.rechanneled[self.player.get_register()]
        except KeyError:
            return
        self.player.ignore_channel(channel)

    def unignore_channels(self):
        for channel in self.player.ignored_channels.copy():
            self.player.unignore_channel(channel)


    def get_channel_color(self, channel):
        if channel not in self.mapped_colors:
            self.rechanneled[len(self.mapped_colors) % len(self.COLORORDER)] = channel
            self.mapped_colors[channel] = self.COLORORDER[len(self.mapped_colors) % len(self.COLORORDER)]

        if channel in self.player.ignored_channels:
            color = wrecked.BRIGHTBLACK
        else:
            color = self.mapped_colors[channel]
        return color

    def kill(self):
        ''' Tear down the player backend '''
        if self.player:
            self.player.kill()

    def resize(self, new_width, new_height):
        super().resize(max(new_width, self.rect_inner.width + 2), new_height)
        self.FLAG_BACKGROUND = True
        self.last_rendered_position = -1

    def jump_to_register_measure(self):
        register = self.player.get_register()
        self.player.set_measure(register - 1)
