'''Plays MIDILike Objects'''

from Box import Box
from Interactor import RegisteredInteractor
from localfuncs import read_character
from MIDIInterface import MIDIInterface
from MidiLib.MidiInterpreter import MIDIInterpreter as MI

class Player(Box, RegisteredInteractor):
    '''Plays MIDILike Objects'''
    NEXT_STATE = 1 << 1
    PREV_STATE = 1 << 2
    RAISE_QUIT = 1 << 3
    RAISE_MIDI_INPUT_CHANGE = 1 << 4
    RAISE_JUMP = 1 << 5
    RAISE_SAVE = 1 << 6
    RAISE_IGNORE_CHANNEL = 1 << 7

    rechannelling = -1

    SHARPS = (1, 3, 6, 8, 10)

    sidebar = '|'

    def quit(self):
        ''''shutdown the player Box'''
        self.set_flag(self.RAISE_QUIT)
        self.kill()

    def next_state(self):
        '''set Next state flag'''
        self.set_flag(self.NEXT_STATE)

    def prev_state(self):
        '''set previous state flag'''
        self.set_flag(self.PREV_STATE)

    def raise_save(self):
        '''set save flag'''
        self.set_flag(self.RAISE_SAVE)

    def save(self, midiinterface):
        '''save loaded midi file'''
        old_path = midiinterface.midilike.path
        if "/" in old_path:
            old_path = old_path[old_path.rfind("/") + 1:]
        path = "editted-" + old_path
        midiinterface.save_as(path)

    def jump(self):
        '''set the song position as the value in the register'''
        self.set_flag(self.RAISE_JUMP)
        self.song_position = self.general_register
        self.clear_register()

    def get_settings(self):
        '''Get cached settings from Interface'''
        try:
            return self.parent.settings[self.active_midi.path]
        except KeyError:
            return {}

    def set_rechannel(self):
        '''start rechanneling events'''
        if self.general_register:
            self.rechannelling = self.general_register
        self.clear_register()

    def unset_rechannel(self):
        '''stop rechanneling events'''
        self.rechannelling = -1
        self.clear_register()

    def set_settings(self, new_settings, do_save=False):
        '''Cache Settings in Interface'''
        self.parent.settings[self.active_midi.path] = new_settings
        if do_save:
            self.parent.save_settings()

    def raise_ignore_channel(self):
        self.set_flag(self.RAISE_IGNORE_CHANNEL)

    def toggle_ignore_channel(self):
        c = self.general_register
        self.general_register = 0
        dif = len(self.channels_used) - len(self.ignored_channels)
        if c in self.ignored_channels:
            self.ignored_channels.remove(c)
        # Don't removed the last channel
        elif dif > 1:
            self.ignored_channels.append(c)

    def point_jump(self):
        '''Jump to saved point'''
        jumpkey = read_character()
        settings = self.get_settings()
        if not "jump_points" in settings.keys():
            return None

        jump_points = settings["jump_points"]
        if jumpkey in jump_points.keys():
            self.set_flag(self.RAISE_JUMP)
            self.song_position = jump_points[jumpkey]

    def set_jump_point(self):
        '''Save a point to be jumped to'''
        jumpkey = read_character()
        settings = self.get_settings()
        if not "jump_points" in settings.keys():
            settings["jump_points"] = {}

        if self.general_register:
            settings["jump_points"][jumpkey] = self.general_register
            self.clear_register()
        else:
            settings["jump_points"][jumpkey] = self.song_position

        self.set_settings(settings, True)

    def __init__(self):
        Box.__init__(self)
        RegisteredInteractor.__init__(self)

        self.loop = [0, -1]

        self.assign_sequence("j", self.next_state)
        self.assign_sequence("k", self.prev_state)
        self.assign_sequence("i", self.raise_ignore_channel)
        self.assign_sequence("p", self.jump)
        self.assign_sequence("P", self.point_jump)
        self.assign_sequence("q", self.quit)
        self.assign_sequence(":w", self.raise_save)
        self.assign_sequence("s", self.set_jump_point)
        self.assign_sequence("c", self.set_rechannel)
        self.assign_sequence("C", self.unset_rechannel)
        self.assign_sequence("[", self.set_loop_start)
        self.assign_sequence("]", self.set_loop_end)
        self.assign_sequence("/", self.clear_loop)

        self.last_pressed = set()
        bottom_key = 21
        self.note_range = [bottom_key, bottom_key + 88]
        self.playing = False
        self.flags = {}
        self.previously_expected_set = set()

        self.channels_used = set()
        self.ignored_channels = []
        self.song_position = 0

        self.active_midi = None
        self.active_boxes = []
        self.state_boxes = []

        self.key_boxes = []
        self.active_key_boxes = [] # for refresh call

    def width(self):
        return (self.note_range[1] - self.note_range[0]) + 2

    def _get_note_str(self, note, channel=10):
        '''Convert Midi Note byte to Legible Character'''
        note_list = 'CCDDEFFGGAAB'
        color_trans = [7, 3, 6, 2, 5, 4, 1, 3]
        ignoring = False
        if channel in self.ignored_channels:
            ignoring = True
        elif channel > 7:
            note_list = note_list.lower()
            channel %= 8

        note %= 12
        display_character = note_list[note]

        if ignoring:
            if note in self.SHARPS:
                return "\033[1;30m%s\033[0m" % (display_character)
            else:
                return "\033[1;7;30m%s\033[0m" % (display_character)
        else:
            color = color_trans[channel]

            if note in self.SHARPS:
                return "\033[7;3%dm%s\033[0m" % (color, display_character)
            else:
                return "\033[3%dm%s\033[0m" % (color, display_character)

    def update_pressed_line(self, pressed, matched):
        '''Redraw Pressed Keys'''
        if not matched:
            matched = []
        if pressed.symmetric_difference(self.last_pressed):
            self.active_key_boxes = []
            note_list = 'CCDDEFFGGAAB'
            for index in pressed:
                rep = note_list[index % len(note_list)]
                if index in matched:
                    background = 42
                    if index % 12 in self.SHARPS:
                        foreground = 30
                    else:
                        foreground = 37
                else:
                    background = 41
                    if index % 12 in self.SHARPS:
                        foreground = 30
                    else:
                        foreground = 37
                to_set = self.boxes[self.key_boxes[index - self.note_range[0]]]
                to_set.set(0, 0, "\033[%d;%dm%s\033[m" % (background, foreground, rep))
                self.active_key_boxes.append(self.boxes[self.key_boxes[index - self.note_range[0]]])
            self.refresh(self.active_boxes + self.active_key_boxes + [self.position_display_box])
            self.last_pressed = pressed

    def redraw_row_box(self, midi_interface):
        '''force redrawing of active row'''
        current_state = midi_interface.event_map[self.song_position]
        current_box = self.state_boxes[self.song_position]
        for key, event in current_state.items():
            try:
                current_box.set(key - self.note_range[0], 0, self._get_note_str(key, event.channel))
            except IndexError:
                pass

    def insert_keychars(self, midi_interface):
        '''Repopulate all the boxes with key characters'''
        for j, current_state in enumerate(midi_interface.event_map):
            box = self.state_boxes[j]
            for key, event in current_state.items():
                try:
                    box.set(key - self.note_range[0], 0, self._get_note_str(key, event.channel))
                except IndexError:
                    pass

    def play_along(self, path, controller):
        '''Display notes in console. Main function'''
        midilike = MI.parse_midi(path)
        midi_interface = MIDIInterface(midilike, controller)
        self.active_midi = midilike
        self.channels_used = midi_interface.channels_used

        num_of_keys = self.note_range[1] - self.note_range[0] + 1
        self.resize(num_of_keys + 2, self.parent.height())
        space_buffer = 8

        self.state_boxes = []
        measure_count = 0
        measure_dict = {}

        for j, current_state in enumerate(midi_interface.event_map):
            new_bid = self.add_box(x=1, y=j, width=88, height=1)
            new_box = self.boxes[new_bid]
            self.state_boxes.append(new_box)

        self.insert_keychars(midi_interface)

        self.key_boxes = []
        self.active_key_boxes = []
        for x in range(88):
            k = self.add_box(x=x + 1, y=self.height() - space_buffer - 1, width=1, height=1)
            self.key_boxes.append(k)
            new_box = self.boxes[k]
            if x % 12 != 0:
                self.set(x + 1, self.height() - space_buffer - 1, " ")
            else:
                self.set(x + 1, self.height() - space_buffer - 1, "\033[1;30m%s\033[0m" % chr(9474))

        for y in range(self.height()):
            self.set(0, y, chr(9474))
            self.set(self.width() - 1, y, chr(9474))

        tmp_id = self.add_box(x=0, y=self.height() - 1, width=self.width(), height=1)
        self.position_display_box = self.boxes[tmp_id]

        self.song_position = 0
        self.playing = True
        first = True
        while self.playing:
            call_refresh = False
            if first: # Draw the initial state before waiting for any input
                first = False
                call_refresh = True
                result = 0

            elif self.loop[1] != 0 \
              and (self.song_position == self.loop[1]) \
              or (self.song_position == len(midi_interface)):
                self.song_position = self.loop[0]
                result = self.RAISE_JUMP
            elif len(midi_interface) > self.song_position:
                result = self._wait_for_input(midi_interface)
            else: # Can't Happen. will loop to start before this happens
                result = self.RAISE_QUIT

            if self.rechannelling > -1:
                for k in midi_interface.get_pressed():
                    if k in midi_interface.event_map[self.song_position].keys():
                        on_event = midi_interface.event_map[self.song_position][k]
                        midi_interface.rechannel_event(on_event, self.rechannelling)
                self.redraw_row_box(midi_interface)

            if self.flag_isset(self.RAISE_SAVE):
                self.save(midi_interface)

            if result == self.RAISE_QUIT:
                self.playing = False
            elif result == self.RAISE_MIDI_INPUT_CHANGE:
                call_refresh = True
            elif result == self.NEXT_STATE:
                self.song_position = (self.song_position + 1) % len(midi_interface)
                while self.song_position < len(midi_interface) \
                  and midi_interface.is_state_empty(self.song_position):
                    self.song_position = (self.song_position + 1) % len(midi_interface)

                call_refresh = True
            elif result == self.PREV_STATE:
                first = True
                while (first or midi_interface.is_state_empty(self.song_position)) \
                    and self.song_position > 0:
                    first = False
                    self.song_position = max(0, self.song_position - 1)

                call_refresh = True
            elif result == self.RAISE_JUMP:
                call_refresh = True

            if call_refresh:
                strpos = "%8d/%d" % (self.song_position, len(midi_interface) - 1)
                for c, character in enumerate(strpos):
                    self.position_display_box.set(self.width() - len(strpos) - 1 + c, 0, character)

                #str_m_pos = "Bar: %3d/%3d" % (measure_dict[self.song_position], measure_count)
                #for c, character in enumerate(str_m_pos):
                #    self.set(1 + c, self.height() - 1, character)
                sb_i = max(0, self.song_position - space_buffer)
                sb_f = min(len(self.state_boxes), self.song_position - space_buffer + self.height())

                self.active_boxes = self.state_boxes[sb_i: sb_f]


                y = len(self.active_boxes) - 1
                y += max(0, (self.song_position - space_buffer + self.height()) - len(self.state_boxes))
                for box in self.active_boxes:
                    self.move_box(box.id, 1, y)
                    y -= 1
                if len(self.active_boxes) >= self.height():
                    self.active_boxes.pop(0)
                self.refresh(self.active_key_boxes + self.active_boxes + [self.position_display_box])
        self.quit()

    def _wait_for_input(self, midi_interface):
        '''Waits for user to press correct key combination'''

        while not midi_interface.states_unmatch(self.song_position, midi_interface.get_pressed()):
            pass

        input_given = 0
        while input_given == 0:
            pressed = midi_interface.get_pressed()
            if midi_interface.states_match(self.song_position, pressed, self.ignored_channels):
                input_given = self.NEXT_STATE
            elif self.flag_isset(self.RAISE_IGNORE_CHANNEL):
                self.flags[self.RAISE_IGNORE_CHANNEL] = 0
                self.toggle_ignore_channel()
                self.insert_keychars(midi_interface)
                self.general_register = self.song_position
                input_given = self.RAISE_JUMP
                self.clear_register()
            elif self.flag_isset(self.PREV_STATE):
                self.flags[self.PREV_STATE] = 0
                input_given = self.PREV_STATE
            elif self.flag_isset(self.NEXT_STATE):
                self.flags[self.NEXT_STATE] = 0
                input_given = self.NEXT_STATE
            elif self.flag_isset(self.RAISE_QUIT):
                self.flags[self.RAISE_QUIT] = 0
                input_given = self.RAISE_QUIT
            elif self.flag_isset(self.RAISE_JUMP):
                self.flags[self.RAISE_JUMP] = 0
                input_given = self.RAISE_JUMP
            self.update_pressed_line(pressed, midi_interface.get_state(self.song_position))
        return input_given

    def set_loop_start(self):
        '''set current positions as loop start'''
        self.loop[0] = self.song_position
        self.clear_register()

    def set_loop_end(self):
        '''set current positions as loop end'''
        self.loop[1] = self.song_position
        self.clear_register()
        self.set_flag(self.RAISE_JUMP, 1)
        self.general_register = self.loop[0]

    def clear_loop(self):
        '''Stop Looping'''
        self.loop = [0, -1]

    def flag_isset(self, flag):
        '''Check if flag is set'''
        return flag in self.flags.keys() and self.flags[flag]

    def set_flag(self, flag, state=1):
        '''Set a Flag'''
        self.flags[flag] = state

