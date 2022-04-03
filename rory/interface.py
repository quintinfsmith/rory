'''Interface between user and player'''
from __future__ import annotations
import threading
import time
import os
from typing import Final
import wrecked
from wrecked import get_terminal_size
from apres import MIDI
from rory.player import Player
from rory.interactor import Interactor

class TerminalTooNarrow(Exception):
    '''Error thrown when the minimum width required isn't available'''

class RoryStage:
    '''Interface to Run the MidiPlayer'''
    KILL = 1
    PAUSE = 2

    CONTEXT_DEFAULT = 0
    CONTEXT_PLAYER = 1
    CONTEXT_BROWSER = 2

    CONTROL_QUIT = 'q'


    def daemon_input(self):
        '''just handles computer keyboard input'''
        self.interactor_running = True
        while self.playing:
            self.interactor.get_input()
        self.interactor.restore_input_settings()
        self.interactor_running = False

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

        self.delay = 1/32
        self.playing = False

        self.scene_constructors = {
            self.CONTEXT_PLAYER: PlayerScene,
            self.CONTEXT_BROWSER: BrowserScene
        }

        self.history_stack = []
        self.interactor_running = False

    def set_fps(self, fps):
        ''' Set the delay between each tick, calculated from Frames Per Second '''
        self.delay = 1 / fps

    def key_scene(self, key, scene):
        ''' Assign a RoryScene to a key '''
        self.scenes[key] = scene

    def play_along(self, midi_path, **kwargs):
        '''Run the Player with the loaded MidiLike Object'''

        if self.CONTEXT_PLAYER not in self.scenes:
            transpose = kwargs.get('transpose', 0)

            scene = PlayerScene(
                self,
                path=midi_path,
                transpose=transpose
            )
            self.key_scene(self.CONTEXT_PLAYER, scene)

        self.interactor.set_context(self.CONTEXT_PLAYER)
        self.start_scene(self.CONTEXT_PLAYER)

    def kill(self):
        '''
            Detaches all scenes.
            Stops the input an player daemons.
            Then returns the terminal to its normal state.
        '''

        self.playing = False
        self.interactor.kill_flag = True

        for scene in self.scenes.values():
            scene.disable()
            scene.root.detach()
            del scene

        while self.interactor_running:
            time.sleep(.1)
        wrecked.kill()

    def resize(self, width, height):
        ''' Resize the wrecked screen and adjust the active scene's size '''
        self.root.resize(width, height)
        try:
            scene = self.scenes[self.active_scene]
        except KeyError:
            scene = None

        if scene:
            scene.resize(width, height)

    def _resize_check(self):
        ''' If the terminal has changed size, calls resize on the stage. '''
        if wrecked.fit_to_terminal():
            self.resize(*get_terminal_size())

    def play(self):
        ''' Start the play and input daemons. No scene *needs* to be active '''
        self.playing = True

        thread = threading.Thread(target=self.daemon_input)
        thread.start()

        play_thread = threading.Thread(target=self.daemon_play)
        play_thread.start()

    def daemon_play(self):
        '''
            Called by the play function as a thread.
            Will update the wrecked root as changes to the scenes occur.
        '''

        while not self.active_scene:
            time.sleep(self.delay)

        while self.playing:
            self._resize_check()

            try:
                scene = self.scenes[self.active_scene]
            except KeyError:
                scene = None

            if scene:
                try:
                    if scene.has_kill_message():
                        self.process_kill_message(scene.get_kill_message())
                    elif scene.tick():
                        scene.draw()
                except Exception as generic_exception:
                    self.kill()
                    raise generic_exception
            else:
                self.kill()

            time.sleep(self.delay)

    def remove_scene(self, key):
        ''' Remove the scene found @ 'key' '''
        if self.scenes[key]:
            self.scenes[key].disable()
            self.scenes[key].root.detach()
            del self.scenes[key]

    def process_kill_message(self, msg):
        ''' Process kill message that may have been set in a scene '''
        dokill, scene_context, kwargs = msg

        if dokill:
            self.remove_scene(self.active_scene)
            if self.history_stack:
                previous_scene_key = self.history_stack.pop()
                self.active_scene = None
                self.start_scene(previous_scene_key)

        elif scene_context:
            self.history_stack.append(self.active_scene)
            self.start_scene(scene_context, **kwargs)

    def start_scene(self, new_scene_key, **kwargs):
        ''' Stops the active scene, Creates a predefined scene and sets it as active '''
        if self.active_scene:
            self.scenes[self.active_scene].disable()

        if new_scene_key not in self.scenes:
            self.scenes[new_scene_key] = self.scene_constructors[new_scene_key](self, **kwargs)

        self.interactor.set_context(new_scene_key)
        self.scenes[new_scene_key].enable()
        self.scenes[new_scene_key].draw()
        self.active_scene = new_scene_key

    def new_rect(self):
        ''' Create a new wrecked Rect at wrecked Root '''
        rect = self.root.new_rect()
        rect.resize(self.root.width, self.root.height)
        return rect

class RoryScene:
    ''' Abstract Class.
        Allows functionally different sections of the program
        to be displayed independently of eachother by the RoryStage
    '''

    def init_interactor(self, interactor):
        '''
            Abstract method.
            Used to assign command sequences to the interactor
        '''
        raise NotImplementedError

    def __init__(self, rorystage):
        self.stage = rorystage
        self.root = rorystage.new_rect()
        self.kill_message = None
        self.init_interactor(rorystage.interactor)

    def disable(self):
        ''' Disables the scene so it will not keep being drawn '''
        self.root.disable()

    def enable(self):
        ''' Enables the scene so i can be drawn '''
        self.root.enable()

    def draw(self):
        ''' Call the wrecked draw function '''
        self.root.draw()

    def tick(self):
        '''
            Abstract method.
            Called multiple times per second to update the visuals of the scene.
        '''
        raise NotImplementedError

    def has_kill_message(self):
        ''' Has a kill message been set? '''
        return bool(self.kill_message)

    def get_kill_message(self):
        ''' Get the kill message and unset it '''
        output = self.kill_message
        self.kill_message = None
        return output

    def takedown(self):
        ''' Optional Abstract method.
            Called on kill to allow for any changes that need
            to be done before the scene is destroyed.
        '''

    def end_scene(self, kill_status=True, next_context=None, message=None):
        ''' Sets the kill message '''
        self.kill_message = (kill_status, next_context, message)

    def resize(self, new_width, new_height):
        ''' Resize the scene's wrecked Rect '''
        self.root.resize(new_width, new_height)

class BrowserScene(RoryScene):
    ''' File Browser. Shows only .mid files and directories '''
    CONTROL_QUIT = 'q'
    def init_interactor(self, interactor):
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_BROWSER,
            self.CONTROL_QUIT,
            self.end_scene
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_BROWSER,
            'j',
            self.next_row
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_BROWSER,
            'k',
            self.prev_row
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_BROWSER,
            'h',
            self.prev_col
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_BROWSER,
            'l',
            self.next_col
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_BROWSER,
            "\r",
            self.select
        )

    def __init__(self, rorystage: RoryStage, **kwargs):
        super().__init__(rorystage)
        self.path = kwargs.get('path', os.environ['HOME'])

        self.path_offsets = {}
        self._working_file_list = []

        self.set_working_path(self.path)

        self.rect_title = self.root.new_rect()
        self.rect_title_path = self.rect_title.new_rect()
        self.rect_offset = self.root.new_rect()
        self.rect_browser_main = self.root.new_rect()
        self.working_rect_columns = []
        self.working_rect_files = []

        self.rendered_path = None
        self.rendered_offset = None

    def get_offset(self):
        ''' Get the current position of the cursor '''
        return self.path_offsets[self.working_path]

    def select(self):
        ''' Either go into a selected directory or run a selected .mid '''
        isdir, path = self._working_file_list[self.get_offset()]

        if isdir:
            self.set_working_path(self.working_path + '/' + path)
        else:
            self.end_scene(
                False,
                RoryStage.CONTEXT_PLAYER,
                { 'path': self.working_path + '/' + path }
            )

    def set_working_path(self, new_path):
        ''' Set the path to browse '''
        self.working_path = os.path.realpath(new_path)
        if self.working_path not in self.path_offsets:
            self.path_offsets[self.working_path] = 0

        self._working_file_list = [(True, '..')]
        dirs = []
        files = []
        for filename in os.listdir(self.working_path):
            if os.path.isfile(self.working_path + '/' + filename):
                if filename[filename.rfind(".") + 1:].lower() == 'mid':
                    files.append(filename)
            elif os.path.isdir(self.working_path + '/' + filename):
                dirs.append(filename)

        dirs.sort()
        for directory in dirs:
            self._working_file_list.append((True, directory))
        files.sort()
        for filename in files:
            self._working_file_list.append((False, filename))
        self.rendered_offset = None

    def next_row(self):
        ''' Move the cursor down to the next row '''
        offset = self.path_offsets[self.working_path]
        offset += len(self.working_rect_columns)
        offset = min(len(self._working_file_list) - 1, offset)
        self.path_offsets[self.working_path] = offset

    def prev_row(self):
        ''' Move the cursor up to the previous row '''
        offset = self.path_offsets[self.working_path]
        offset -= len(self.working_rect_columns)
        offset = max(0, offset)
        self.path_offsets[self.working_path] = offset

    def next_col(self):
        ''' Move the cursor over to the next column '''
        offset = self.path_offsets[self.working_path]
        offset += 1
        offset = min(len(self._working_file_list) - 1, offset)
        self.path_offsets[self.working_path] = offset

    def prev_col(self):
        ''' Move the cursor over to the previous column '''
        offset = self.path_offsets[self.working_path]
        offset -= 1
        offset = max(0, offset)
        self.path_offsets[self.working_path] = offset

    def tick(self):
        ''' Update the display '''
        was_changed = False

        if self.working_path != self.rendered_path:
            self.rect_browser_main.resize(self.root.width, self.root.height - 1)
            self.rect_browser_main.move(0,1)

            min_column_width = 50
            columns = 1
            while True:
                if not (
                    len(self._working_file_list) / columns < self.rect_browser_main.height or
                    self.rect_browser_main.width / columns < min_column_width
                ):
                    columns += 1
                else:
                    break

            for path in self.working_rect_files:
                path.detach()
                del path
            self.working_rect_files = []

            column_width = (self.root.width - (columns * 2)) // columns
            for column in self.working_rect_columns:
                column.remove()
                del column
            self.working_rect_columns = []


            files_per_column = max(1, len(self._working_file_list) // columns)
            extra = len(self._working_file_list) % files_per_column
            for i in range(columns):
                column_height = files_per_column
                if extra:
                    column_height += 1
                    extra -= 1
                rect_col = self.rect_browser_main.new_rect(width=column_width, height=column_height)
                rect_col.move((i * (column_width + 1)), 0)
                self.working_rect_columns.append(rect_col)

            for i, (isdir, filename) in enumerate(self._working_file_list):
                rect_column = self.working_rect_columns[i % columns]
                rect_file = rect_column.new_rect()
                rect_file.resize(rect_column.width, 1)
                if isdir:
                    rect_file.set_fg_color(wrecked.BLUE)
                    f_text = "%02d) %s" % (i, filename)
                else:
                    f_text = "%02d) %s" % (i, filename[0:filename.rfind(".")])

                if len(f_text) > column_width:
                    f_text = f_text[0:column_width]
                y = i // columns
                rect_file.move(0, y)
                rect_file.set_string(0, 0, f_text)
                self.working_rect_files.append(rect_file)

            self.rendered_path = self.working_path

        offset = self.path_offsets[self.working_path]
        if offset != self.rendered_offset:
            denom = len(self._working_file_list) - 1
            numer = offset
            display_string = f"{numer}/{denom}"
            self.rect_offset.resize(len(display_string), 1)
            self.rect_offset.move(self.root.width - len(display_string), 0)
            self.rect_offset.set_string(0, 0, display_string)

            new_width = self.root.width - self.rect_offset.width

            prefix = "Files In: "
            self.rect_title.resize(new_width, 1)
            self.rect_title.move(0, 0)
            self.rect_title.set_string(0, 0, prefix)

            new_width -= len(prefix)
            title_string = self.working_path[self.working_path.rfind("/") + 1:]
            if new_width < len(title_string):
                title_string = title_string[0:new_width]
                if len(title_string) - new_width  > 3:
                    title_string = title_string[0:-3] + '...'
            else:
                new_width = len(title_string)

            self.rect_title_path.resize(new_width, 1)
            self.rect_title_path.move(len(prefix), 0)
            self.rect_title_path.underline()
            self.rect_title_path.set_string(0, 0, title_string)

            columns = len(self.working_rect_columns)
            column_width = (self.root.width - (columns * 2)) // columns
            isdir, fname = self._working_file_list[offset]
            fname = fname[0:min(len(fname), column_width)]
            if not isdir:
                fname = fname[0:fname.rfind(".")]
            f_text = "%02d) %s" % (offset, fname)

            if self.rendered_offset is not None:
                self.working_rect_files[self.rendered_offset].unset_invert()

            rect_cursor = self.working_rect_files[offset]
            rect_cursor.invert()

            # Shift Page
            column_page = (offset // len(self.working_rect_columns))
            column_page //= self.rect_browser_main.height
            for i, column in enumerate(self.working_rect_columns):
                column.move(
                    i * (column_width + 1),
                    0 - (column_page * self.rect_browser_main.height)
                )

            self.rendered_offset = offset
            was_changed = True

        return was_changed

class PlayerScene(RoryScene):
    '''Handles visualization of the Player'''
    # Display constants
    SHARPS: Final[tuple[int]] = (1, 3, 6, 8, 10)
    NOTELIST: Final[str] = 'CCDDEFFGGAAB'

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

    def init_interactor(self, interactor):
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_NEXT_STATE,
            self.player.next_state
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_IGNORE_CHANNEL,
            self.ignore_channel
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_UNIGNORE_CHANNELS,
            self.unignore_channels
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_PREV_STATE,
            self.player.prev_state
        )

        for digit in range(10):
            interactor.assign_context_sequence(
                RoryStage.CONTEXT_PLAYER,
                str(digit),
                self.player.set_register_digit,
                digit
            )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            '-',
            self.player.set_register_digit,
            ord('-')
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_CLEAR_REGISTER,
            self.player.clear_register
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_TOGGLE_HELP,
            self.toggle_help_menu
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_SET_POSITION,
            self.player.jump_to_register_position,
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_SET_MEASURE,
            self.jump_to_register_measure,
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_LOOP_START,
            self.player.set_loop_start_to_position,
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_LOOP_END,
            self.player.set_loop_end_to_position,
        )
        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_LOOP_KILL,
            self.player.clear_loop,
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_TRANSPOSE,
            self.reset_transpose,
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_QUIT,
            self.end_scene
        )

        interactor.assign_context_sequence(
            RoryStage.CONTEXT_PLAYER,
            self.CONTROL_SET_RANGE,
            self.flag_new_range
        )

    def __init__(self, rorystage: RoryStage, **kwargs):
        self.player = Player(**kwargs)
        self.nu_mode = kwargs.get('numode', False)

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
        ''' Let the player know that the user wants to change the range of playable notes '''
        self.player.flag_new_range()

    def reset_transpose(self):
        ''' Set the transposition back to 0 '''
        register = self.player.get_register()
        self.player.reinit_midi_interface(
            transpose=register
        )

    def has_transpose_changed(self):
        ''' Check if transposition has changed '''
        current = self.player.get_transpose()
        output = current != self.last_rendered_transpose
        if output:
            self.last_rendered_transpose = current

        return output

    def has_note_range_changed(self):
        ''' Check if the range of playable notes has changed '''
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
        if (
            self.last_rendered_position != song_position
            or self.last_rendered_loop != player.loop
            or self.last_rendered_ignored_channels != self.player.ignored_channels
            or note_range_changed
            or transpose_changed
        ):
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
        ''' Set the flag to draw the help menu in the tick function '''
        self.flag_show_menu = not self.flag_show_menu

    def __draw_chord_name(self):
        midi_interface = self.player.midi_interface
        active_channels = midi_interface.get_active_channels(self.player.song_position)
        chord_names = []
        for channel in active_channels:
            chord_name = midi_interface.get_chord_name(self.player.song_position, channel, self.nu_mode)
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
                    if self.nu_mode:
                        notename = '0123456789AB'[(message.note + 3) % 12]
                        note_rect.set_character(0, 0, notename)
                    else:
                        note_rect.set_character(0, 0, self.NOTELIST[message.note % 12])

                    if message.note % 12 in self.SHARPS:
                        note_rect.set_bg_color(color)
                        note_rect.set_fg_color(wrecked.BLACK)
                    else:
                        note_rect.set_fg_color(color)
                        note_rect.set_bg_color(wrecked.BLACK)

                note_rect.move(x, y)

            # Draw Measure Lines
            if position in midi_interface.beat_map and _y != self.active_row_position:
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
            order = len(str(max(self.player.loop)))
            fmt_string = f"[%0{order}d: %0{order}d :%0{order}d]"
            position_string = fmt_string % (self.player.loop[0], song_position, self.player.loop[1])

            min_measure = self.__get_measure(self.player.loop[0])
            max_measure = self.__get_measure(self.player.loop[1])
            order = len(str(max_measure))
            fmt_string = f"[%0{order}d: %0{order}d :%0{order}d]"
            measure_string = fmt_string % (
                min_measure,
                self.__get_measure(song_position),
                max_measure
            )
        else:
            order = len(str(len(state_map)))
            fmt_string = f"%0{order}d/%0{order}d"
            position_string = fmt_string % (song_position, len(state_map))

            max_measure = self.__get_measure(len(state_map))
            order = len(str(max_measure))
            fmt_string = f"%0{order}d/%0{order}d"
            measure_string = fmt_string % (self.__get_measure(song_position), max_measure)

        self.rect_position_display.resize(
            len(position_string),
            2
        )
        self.rect_position_display.move(
            max(
                0,
                self.rect_background.width - len(position_string)
            ),
            self.rect_background.height - 2
        )
        self.rect_position_display.set_string(
            len(position_string) - len(measure_string),
            0,
            measure_string
        )
        self.rect_position_display.set_string(
            0,
            1,
            position_string
        )
        self.last_rendered_loop = self.player.loop.copy()

    def get_pressed_notes(self):
        ''' Get a set of notes currently being held down '''
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
        ''' Draw the help menu '''
        if not self.rect_help_menu:
            self.rect_help_menu = self.root.new_rect()

        menu = self.rect_help_menu

        descriptions = [
            (PlayerScene.CONTROL_QUIT, "Close Rory"),
            (PlayerScene.CONTROL_TOGGLE_HELP, "Toggle this pop up"),
            ("0-9", "Set register"),
            ("ESC", "Clear register"),
            (PlayerScene.CONTROL_NEXT_STATE, "Next state"),
            (PlayerScene.CONTROL_PREV_STATE, "Previous state"),
            (PlayerScene.CONTROL_IGNORE_CHANNEL, "Ignore the channel in register"),
            (PlayerScene.CONTROL_UNIGNORE_CHANNELS, "Unignore all channels"),
            (PlayerScene.CONTROL_SET_POSITION, "Jump to state in register"),
            (
                PlayerScene.CONTROL_SET_RANGE,
                "resize keyboard ( Then press lowest and highest keys )"
            ),
            (PlayerScene.CONTROL_TRANSPOSE, "transpose the entire song by the register"),
            (PlayerScene.CONTROL_LOOP_START, "Set start of loop"),
            (PlayerScene.CONTROL_LOOP_END, "Set end of loop"),
            (PlayerScene.CONTROL_LOOP_KILL, "Clear start & end of loop")
        ]

        lines = [
            "Controls",
            "",
        ]
        for desc in descriptions:
            lines.append(f"{desc[0]}    - {desc[1]}")


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
        # TODO: Make me more efficient
        position = 0
        for i in range(self.player.note_range[0], midi_key):
            if i in (2, 7):
                position += 1
            position += 1
        return position

    def ignore_channel(self):
        '''
            Prevent user from having to press notes on the channel
            denoted by the value of the register
        '''
        try:
            channel = self.rechanneled[self.player.get_register()]
        except KeyError:
            return
        self.player.ignore_channel(channel)

    def unignore_channels(self):
        ''' Require user to hit notes on all channels '''
        for channel in self.player.ignored_channels.copy():
            self.player.unignore_channel(channel)

    def get_channel_color(self, channel):
        ''' Get the color value assigned to the given channel '''
        if channel not in self.mapped_colors:
            color = len(self.mapped_colors) % len(self.COLORORDER)
            self.rechanneled[color] = channel
            self.mapped_colors[channel] = self.COLORORDER[color]

        if channel in self.player.ignored_channels:
            color = wrecked.BRIGHTBLACK
        else:
            color = self.mapped_colors[channel]
        return color

    def end_scene(self):
        ''' Tear down the player backend '''
        if self.player:
            self.player.kill()
        super().end_scene()

    def resize(self, new_width, new_height):
        super().resize(max(new_width, self.rect_inner.width + 2), new_height)
        self.FLAG_BACKGROUND = True
        self.last_rendered_position = -1

    def jump_to_register_measure(self):
        '''
            Move the player's position to the beginning of the measure
            denoted by the value currently set in the register
        '''
        register = self.player.get_register()
        self.player.set_measure(register - 1)
