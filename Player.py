import console
import time
import sys
from MidiInterpreter import *
from MIDIController import *
from Box import Box, log
from Interactor import Interactor

class Player(Box, Interactor):
    """Plays MIDILike Objects"""
    NEXT_STATE = 1
    PREV_STATE = 2
    RAISE_QUIT = 4
    RAISE_MIDI_INPUT_CHANGE = 8
    RAISE_JUMP = 16

    SHARPS = (1,3,6,8,10)

    sidebar = '|'

    def quit(self):
        self.set_flag(self.RAISE_QUIT)
        self.kill()

    def next_state(self):
        self.set_flag(self.NEXT_STATE)

    def prev_state(self):
        self.set_flag(self.PREV_STATE)

    def jump(self):
        self.set_flag(self.RAISE_JUMP)
        self.song_position = self.general_register
        self.clear_register()

    def __init__(self):
        Box.__init__(self)
        Interactor.__init__(self)
        self.toggle_border()

        self.loop = [0,0]

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
        self.post_buffer = 4

        self.ignore = []
        self.song_position = 0

        self.active_boxes = []

        self.key_boxes = []
        self.active_key_boxes = [] # for refresh call

    def _get_note_str(self, note, channel=10):
        """Convert Midi Note byte to Legible Character"""
        note_list = 'CCDDEFFGGAAB'
        channel += 1
        if channel > 7:
            note_list = note_list.lower()
            channel %= 8

        note %= 12
        s = note_list[note]
        if note in self.SHARPS:
            return "\033[7;3%dm%s\033[0m" % (channel, s)
        else:
            return "\033[3%dm%s\033[0m" % (channel, s)

    def update_pressed_line(self, pressed):
        """Redraw Pressed Keys"""
        if pressed.symmetric_difference(self.last_pressed):
            self.active_key_boxes = []
            for p in pressed:
                self.active_key_boxes.append(self.boxes[self.key_boxes[p - self.note_range[0]]])
            self.refresh(self.active_boxes + self.active_key_boxes)
            self.last_pressed = pressed

    def play_along(self, midilike, controller, hidden=[]):
        """Display notes in console. Main function"""
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
                    elif event.eid == event.NOTE_OFF and event.note in pressed_keys.keys() and event.channel != 10:
                        del pressed_keys[event.note]

            if len(pressed_keys.keys()):
                while len(state_list) <= tick * squash_factor:
                    state_list.append({})
                state_list[int(tick * squash_factor)] = pressed_keys.copy()

        for _ in range(self.post_buffer * 5):
            state_list.append({})
        for _ in range(self.height()):
            state_list.insert(0, {})

        box_list = []
        for j in range(len(state_list)):
            new_bid = self.add_box(x=1, y=j, width=88, height=1)
            newBox = self.boxes[new_bid]
            for key, event in state_list[j].items():
                if event.channel != 10:
                    try:
                        newBox.set(key - self.note_range[0], 0, self._get_note_str(key, event.channel))
                    except IndexError:
                        pass
            box_list.append(newBox)
        self.refresh()

        self.key_boxes = []
        self.active_key_boxes =[]
        y = self.height() - space_buffer - 1
        for x in range(88):
            k = self.add_box(x=x, y=self.height() - space_buffer - 1, width=1, height=1)
            self.key_boxes.append(k)
            b = self.boxes[k]
            b.set(0,0, "\033[44m%s\033[0m" % 'CCDDEFFGGAAB'[x % 12])
            if x % 12:
                self.set(x, self.height() - space_buffer - 1, ":")
            else:
                self.set(x, self.height() - space_buffer - 1, "=")

        self.song_position = 0
        self.playing = True
        self.refresh()
        while self.playing:
            call_refresh = False
            if self.loop[1] > 1 and self.song_position == self.loop[1]:
                self.song_position = self.loop[0]
                result = self.RAISE_JUMP
            elif len(state_list) > self.song_position + space_buffer:   
                result = self._wait_for_input(state_list[self.song_position + space_buffer], controller)
            else:
                result = self.RAISE_QUIT

            if result == self.RAISE_QUIT:
                self.playing = False
            elif result == self.RAISE_MIDI_INPUT_CHANGE:
                call_refresh = True
                
            elif result == self.NEXT_STATE:
                self.song_position = (self.song_position + 1) % len(state_list)
                while self.song_position < len(state_list) - space_buffer - 1 and not state_list[self.song_position + space_buffer]:
                    self.song_position = min(len(state_list) - 1, self.song_position + 1)

                strpos = "%9d" % self.song_position
                for c in range(len(strpos)):
                    self.set(self.width() - len(strpos) + c, self.height() - 1, strpos[c])
                call_refresh = True
            elif result == self.PREV_STATE:
                first = True
                while (first or not state_list[self.song_position + space_buffer]) and self.song_position > 0:
                    first = False
                    self.song_position = max(0, self.song_position - 1)

                strpos = "%9d" % self.song_position
                for c in range(len(strpos)):
                    self.set(self.width() - len(strpos) + c, self.height() - 1, strpos[c])
                call_refresh = True
            elif result == self.RAISE_JUMP:
                strpos = "%9d" % self.song_position
                for c in range(len(strpos)):
                    self.set(self.width() - len(strpos) + c, self.height() - 1, strpos[c])
                call_refresh = True

            if call_refresh:
                self.active_boxes = box_list[max(0, self.song_position): min(len(box_list), self.song_position + self.height())]
                y = self.height() - 1
                for box in self.active_boxes:
                    self.move_box(box.id, 0, y)
                    y -= 1
                self.refresh(self.active_boxes + self.active_key_boxes)
        self.quit()

    def _wait_for_input(self, expected, controller):
        """Waits for user to press correct key combination"""
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
                if not key in self.last_pressed:
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
        self.loop[0] = self.song_position
        self.clear_register()

    def set_loop_end(self):
        self.loop[1] = self.song_position
        self.clear_register()

    def clear_loop(self):
        self.loop = [0,0]

    def flag_isset(self, flag):
        return flag in self.flags.keys() and self.flags[flag]

    def set_flag(self, flag, state=1):
        self.flags[flag] = state

