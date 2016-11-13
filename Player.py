'''Plays MIDILike Objects'''

from Box import Box
from Interactor import RegisteredInteractor

class Player(Box, RegisteredInteractor):
    '''Plays MIDILike Objects'''
    NEXT_STATE = 1
    PREV_STATE = 2
    RAISE_QUIT = 4
    RAISE_MIDI_INPUT_CHANGE = 8
    RAISE_JUMP = 16

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

    def __init__(self):
        Box.__init__(self)
        RegisteredInteractor.__init__(self)

        self.loop = [0, -1]

        self.assign_sequence("j", self.next_state)
        self.assign_sequence("k", self.prev_state)
        self.assign_sequence("p", self.jump)
        self.assign_sequence("q", self.quit)
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

        self.active_boxes = []

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

    def update_pressed_line(self, pressed):
        '''Redraw Pressed Keys'''
        if pressed.symmetric_difference(self.last_pressed):
            self.active_key_boxes = []
            for index in pressed:
                self.active_key_boxes.append(self.boxes[self.key_boxes[index - self.note_range[0]]])
            self.refresh(self.active_boxes + self.active_key_boxes)
            self.last_pressed = pressed

    def play_along(self, midilike, controller, hidden=None):
        '''Display notes in console. Main function'''
        if not hidden:
            hidden = []
        if controller.connected:
            controller.listen()
        num_of_keys = self.note_range[1] - self.note_range[0] + 1
        self.resize(num_of_keys + 2, self.parent.height())
        squash_factor = 8 / midilike.tpqn
        space_buffer = 8

        state_list = []
        for tick in range(len(midilike)):
            pressed_keys = {}
            for track in midilike.tracks:
                for event in track.get_events(tick):
                    if event.eid == event.NOTE_ON and event.channel != 10 and not event.channel in hidden:
                        if event.velocity == 0 and event.note in pressed_keys.keys():
                            del pressed_keys[event.note]
                        else:
                            pressed_keys[event.note] = event
                    elif event.eid == event.NOTE_OFF and event.note in pressed_keys.keys():
                        del pressed_keys[event.note]

            if len(pressed_keys.keys()):
                while len(state_list) <= tick * squash_factor:
                    state_list.append({})
                state_list[int(tick * squash_factor)] = pressed_keys.copy()

        box_list = []
        for j, current_state in enumerate(state_list):
            new_bid = self.add_box(x=1, y=j, width=88, height=1)
            new_box = self.boxes[new_bid]
            for key, event in current_state.items():
                if event.channel != 10:
                    try:
                        new_box.set(key - self.note_range[0], 0, self._get_note_str(key, event.channel))
                    except IndexError:
                        pass
            box_list.append(new_box)

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

            elif self.loop[1] != 0 and (self.song_position == self.loop[1]) or (self.song_position == len(state_list)):
                self.song_position = self.loop[0]
                result = self.RAISE_JUMP
            elif len(state_list) > self.song_position:
                result = self._wait_for_input(state_list[self.song_position], controller)
            else: # Can't Happen. will loop to start before this happens
                result = self.RAISE_QUIT

            if result == self.RAISE_QUIT:
                self.playing = False
            elif result == self.RAISE_MIDI_INPUT_CHANGE:
                call_refresh = True

            elif result == self.NEXT_STATE:
                self.song_position = (self.song_position + 1) % len(state_list)
                while self.song_position < len(state_list) and not state_list[self.song_position]:
                    self.song_position = (self.song_position + 1) % len(state_list)

                call_refresh = True
            elif result == self.PREV_STATE:
                first = True
                while (first or not state_list[self.song_position]) and self.song_position > 0:
                    first = False
                    self.song_position = max(0, self.song_position - 1)

                call_refresh = True
            elif result == self.RAISE_JUMP:
                call_refresh = True

            if call_refresh:
                strpos = "%9d/%d" % (self.song_position, len(state_list) - 1)
                for c, character in enumerate(strpos):
                    self.set(self.width() - len(strpos) - 1 + c, self.height() - 1, character)

                self.active_boxes = box_list[max(0, self.song_position - space_buffer): min(len(box_list), self.song_position - space_buffer + self.height())]

                y = len(self.active_boxes) - 1
                y += max(0, (self.song_position - space_buffer + self.height()) - len(box_list))
                for box in self.active_boxes:
                    self.move_box(box.id, 1, y)
                    y -= 1
                self.refresh(self.active_key_boxes + self.active_boxes)
        self.quit()

    def _wait_for_input(self, expected, controller):
        '''Waits for user to press correct key combination'''
        # 'expected' is in the form of a dictionary because we want
        # to consider which channel (or hand) is playing the note
        # 'ignore' is the list of channel numbers which we don't need
        # to press to leave the function call
        # 'expected_unset' are the keys that need to be released before pressing again
        # 'actual_set' is the uncompromised set of pressed keys.
        #   it needs to be used when considering the next keys to be pressed
        expected_set = set()
        expected_unset = set()
        actual_set = set()
        for key, event in expected.items():
            channel = event.channel
            if not channel in self.ignore:
                expected_set.add(key)
                expected_unset.add(key)
                actual_set.add(key)

        # If the key was expected NOT to be pressed last state but was, the user needs to release and press again
        while expected_unset:
            expected_unset &= controller.get_pressed()

        input_given = 0
        while input_given == 0:
            pressed = controller.get_pressed()
            if not (expected_set - pressed):
                input_given = self.NEXT_STATE

            if self.flag_isset(self.PREV_STATE):
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
            self.update_pressed_line(pressed)
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
