'''Plays MIDILike Objects'''

from Box import Box
from Interactor import RegisteredInteractor
from MIDIInterface import MIDIInterface
from localfuncs import read_character

class Player(Box, RegisteredInteractor):
    '''Plays MIDILike Objects'''
    NEXT_STATE = 1 << 1
    PREV_STATE = 1 << 2
    RAISE_QUIT = 1 << 3
    RAISE_MIDI_INPUT_CHANGE = 1 << 4
    RAISE_JUMP = 1 << 5
    RAISE_RECORD = 1 << 6

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

    def toggle_recording(self):
        self.set_flag(self.RAISE_RECORD, 1)
        

    def set_settings(self, new_settings, do_save=False):
        '''Cache Settings in Interface'''
        self.parent.settings[self.active_midi.path] = new_settings
        if do_save:
            self.parent.save_settings()

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
        self.assign_sequence("p", self.jump)
        self.assign_sequence("P", self.point_jump)
        self.assign_sequence("q", self.quit)
        self.assign_sequence("s", self.set_jump_point)
        self.assign_sequence(chr(13), self.toggle_recording)
        self.assign_sequence("[", self.set_loop_start)
        self.assign_sequence("]", self.set_loop_end)
        self.assign_sequence("/", self.clear_loop)

        self.last_pressed = set()
        bottom_key = 21
        self.note_range = [bottom_key, bottom_key + 88]
        self.playing = False
        self.flags = {}
        self.previously_expected_set = set()

        self.ignore = []
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
        color_trans = [7,3,6,2,5,4,1,3]
        if channel > 7:
            note_list = note_list.lower()
            channel %= 8

        note %= 12
        display_character = note_list[note]
        if note in self.SHARPS:
            return "\033[7;3%dm%s\033[0m" % (color_trans[channel], display_character)
        else:
            return "\033[3%dm%s\033[0m" % (color_trans[channel], display_character)

    def update_pressed_line(self, pressed, matched=[]):
        '''Redraw Pressed Keys'''
        if pressed.symmetric_difference(self.last_pressed):
            self.active_key_boxes = []
            for index in pressed:
                #if index in matched:
                #    self.boxes[self.key_boxes[index - self.note_range[0]]].set(0,0, "\033[43m" + str(index) + "\033[m")
                #else:
                #    self.boxes[self.key_boxes[index - self.note_range[0]]].set(0,0, "\033[46m" + str(index) + "\033[m")
                self.active_key_boxes.append(self.boxes[self.key_boxes[index - self.note_range[0]]])
            self.refresh(self.active_boxes + self.active_key_boxes)
            self.last_pressed = pressed

    def play_along(self, midilike, controller):
        '''Display notes in console. Main function'''
        midi_interface = MIDIInterface(midilike, controller)
        self.active_midi = midilike

        num_of_keys = self.note_range[1] - self.note_range[0] + 1
        self.resize(num_of_keys + 2, self.parent.height())
        squash_factor = 8 / midilike.tpqn
        space_buffer = 8

        self.state_boxes = []
        for j, current_state in enumerate(midi_interface.event_map):
            new_bid = self.add_box(x=1, y=j, width=88, height=1)
            new_box = self.boxes[new_bid]
            for key, event in current_state.items():
                try:
                    new_box.set(key - self.note_range[0], 0, self._get_note_str(key, event.channel))
                except IndexError:
                    pass
            self.state_boxes.append(new_box)

        self.key_boxes = []
        self.active_key_boxes = []
        for x in range(88):
            k = self.add_box(x=x + 1, y=self.height() - space_buffer - 1, width=1, height=1)
            self.key_boxes.append(k)
            new_box = self.boxes[k]
            new_box.set(0, 0, "\033[44m%s\033[0m" % 'CCDDEFFGGAAB'[(x - 3) % 12])
            if x % 12 != 0:
                self.set(x + 1, self.height() - space_buffer - 1, " ")
            else:
                self.set(x + 1, self.height() - space_buffer - 1, chr(9474))

        for y in range(self.height()):
            self.set(0,y, chr(9474))
            self.set(self.width() - 1,y, chr(9474))

        self.song_position = 0
        self.playing = True
        first = True
        while self.playing:
            call_refresh = False
            if first: # Draw the initial state before waiting for any input
                first = False
                call_refresh = True
                result = 0

            elif self.loop[1] != 0 and (self.song_position == self.loop[1]) or (self.song_position == len(midi_interface)):
                self.song_position = self.loop[0]
                result = self.RAISE_JUMP
            elif len(midi_interface) > self.song_position:
                result = self._wait_for_input(midi_interface)
            else: # Can't Happen. will loop to start before this happens
                result = self.RAISE_QUIT

            if result == self.RAISE_QUIT:
                self.playing = False
            elif result == self.RAISE_MIDI_INPUT_CHANGE:
                call_refresh = True
            elif result == self.RAISE_RECORD:
                controller.toggle_recording("test.mid")
            elif result == self.NEXT_STATE:
                self.song_position = (self.song_position + 1) % len(midi_interface)
                while self.song_position < len(midi_interface) and midi_interface.is_state_empty(self.song_position):
                    self.song_position = (self.song_position + 1) % len(midi_interface)

                call_refresh = True
            elif result == self.PREV_STATE:
                first = True
                while (first or midi_interface.is_state_empty(self.song_position)) and self.song_position > 0:
                    first = False
                    self.song_position = max(0, self.song_position - 1)

                call_refresh = True
            elif result == self.RAISE_JUMP:
                call_refresh = True

            if call_refresh:
                strpos = "%9d/%d" % (self.song_position, len(midi_interface) - 1)
                for c, character in enumerate(strpos):
                    self.set(self.width() - len(strpos) - 1 + c, self.height() - 1, character)

                self.active_boxes = self.state_boxes[max(0, self.song_position - space_buffer): min(len(self.state_boxes), self.song_position - space_buffer + self.height())]

                y = len(self.active_boxes) - 1
                y += max(0, (self.song_position - space_buffer + self.height()) - len(self.state_boxes))
                for box in self.active_boxes:
                    self.move_box(box.id, 1, y)
                    y -= 1
                self.refresh(self.active_key_boxes + self.active_boxes)
        self.quit()

    def _wait_for_input(self, midi_interface):
        '''Waits for user to press correct key combination'''

        while not midi_interface.states_unmatch(self.song_position, midi_interface.get_pressed()):
            pass

        input_given = 0
        while input_given == 0:
            pressed = midi_interface.get_pressed()
            if midi_interface.states_match(self.song_position, pressed):
                input_given = self.NEXT_STATE
            elif self.flag_isset(self.RAISE_RECORD):
                self.flags[self.RAISE_RECORD] = 0
                input_given = self.RAISE_RECORD
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
            self.update_pressed_line(pressed, midi_interface)
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
