import console
import time
import sys
from MidiInterpreter import *
from MIDIController import *
from Box import Box
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

        self.assign_sequence("l", self.next_state)
        self.assign_sequence("k", self.prev_state)
        self.assign_sequence("j", self.jump)
        self.assign_sequence("q", self.quit)

        self.note_range = [0, 127]
        self.playing = False
        self.flags = {}
        self.previously_expected_set = set()
        self.post_buffer = 4

        self.ignore = []
        self.song_position = 0

        self.key_boxes = []

    def _get_note_str(self, note, channel=10):
        """Convert Midi Note byte to Legible Character"""
        note_list = 'CCDDEFFGGAAB'
        if channel > 7:
            c = (channel + 1) % 8
            bolder = ""
        else:
            c = channel
            bolder = "1;"

        note %= 12
        if note in self.SHARPS:
            return "\033[%s7;3%dm%s\033[0m" % (bolder, c, note_list[note])
        else:
            return "\033[%s3%dm%s\033[0m" % (bolder, c, note_list[note])

    def play_along(self, midilike, controller, hidden=[]):
        """Display notes in console. Main function"""
        if controller.connected:
            controller.listen()
        #self.note_range = midilike.get_note_range()
        num_of_keys = self.note_range[1] - self.note_range[0] + 1
        self.resize(num_of_keys + 2, self.parent.height())
        self.refresh()
        squash_factor = 8 / midilike.tpqn

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
            state_list.insert(0, {})
        for _ in range(self.height()):
            state_list.append({})

        input_box_id = self.add_box(x=1, y=self.height()- 6, width=128, height=1)
        for x in range(128):
            self.boxes[input_box_id].set(x, 0, "-")

        for j in range(len(state_list)):
            new_bid = self.add_box(x=1, y=self.height() - 6 - j, width=128, height=1)
            newBox = self.boxes[new_bid]
            for key, event in state_list[j].items():
                if event.channel != 10:
                    newBox.set(key, 0, self._get_note_str(key, event.channel))

        self.key_boxes = []
        for x in range(128):
            k = self.add_box(x=x + 1, y =self.height() - 6, width=1, height=1)
            self.key_boxes.append(k)
            b = self.boxes[k]
            b.set(0,0,"\033[42mX\033[40m")
            b.hide()

        self.song_position = 0
        self.playing = True
        self.refresh()
        while self.playing:
            call_refresh = False
            result = self._wait_for_input(state_list[self.song_position], controller)
            if result == self.RAISE_QUIT:
                self.playing = False
            elif result == self.NEXT_STATE:
                self.song_position = (self.song_position + 1) % len(state_list)
                for b_id, pos in self.box_positions.items():
                    if b_id == input_box_id or b_id in self.key_boxes:
                        continue
                    x, y = pos
                    y = (y + 1) % len(state_list)
                    self.box_positions[b_id] = (x,y)
                    self.boxes[b_id].set_refresh_flag()
                strpos = "%9d" % self.song_position
                for c in range(len(strpos)):
                    self.set(self.width() - len(strpos) + c, self.height() - 1, strpos[c])
                call_refresh = True
            elif result == self.PREV_STATE:
                first = True
                while (first or not state_list[self.song_position]) and self.song_position > 0:
                    first = False
                    self.song_position = max(0, self.song_position - 1)
                    for b_id, pos in self.box_positions.items():
                        if b_id == input_box_id or b_id in self.key_boxes:
                            continue
                        x, y = pos
                        y = (y - 1) % len(state_list)
                        self.box_positions[b_id] = (x,y)
                strpos = "%9d" % self.song_position
                for c in range(len(strpos)):
                    self.set(self.width() - len(strpos) + c, self.height() - 1, strpos[c])
                call_refresh = True
            elif result == self.RAISE_JUMP:
                sorted_keys = list(self.boxes.keys())
                sorted_keys.sort()

                for i in range(len(sorted_keys)):
                    b_id = sorted_keys[i]
                    if b_id == input_box_id or b_id in self.key_boxes:
                        continue
                    y = ((self.height() - 5) - i) + self.song_position
                    x = 0
                    self.box_positions[b_id] = (x,y)
                strpos = "%9d" % self.song_position
                for c in range(len(strpos)):
                    self.set(self.width() - len(strpos) + c, self.height() - 1, strpos[c])
                call_refresh = True
            if call_refresh:
                self.refresh()
                

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
                if not key in self.previously_expected_set:
                    expected_set.add(key)
                    expected_unset.add(key)
                actual_set.add(key)

        # If the key was expected NOT to be pressed last state but was, the user needs to release and press again
        while expected_unset:
            expected_unset &= controller.get_pressed()
        input_given = 0
        last_pressed = set()
        while input_given == 0:
            pressed = controller.get_pressed()

            
            if pressed.symmetric_difference(last_pressed):
                #self.draw_input_line(pressed, expected)
                for k in range(128):
                    self.boxes[self.key_boxes[k]].hide()
                for k in pressed:
                    self.boxes[self.key_boxes[k]].show()
                self.refresh()

            if not (expected_set - pressed):
                input_given = self.NEXT_STATE
                self.previously_expected_set = actual_set
            elif self.flag_isset(self.PREV_STATE):
                self.flags[self.PREV_STATE] = 0
                input_given = self.PREV_STATE
                self.previously_expected_set = set()
            elif self.flag_isset(self.NEXT_STATE):
                self.flags[self.NEXT_STATE] = 0
                input_given = self.NEXT_STATE
                self.previously_expected_set = actual_set
            elif self.flag_isset(self.RAISE_QUIT):
                self.flags[self.RAISE_QUIT] = 0
                input_given = self.RAISE_QUIT
                
            elif self.flag_isset(self.RAISE_JUMP):
                self.flags[self.RAISE_JUMP] = 0
                input_given = self.RAISE_JUMP
            last_pressed = pressed
        return input_given


    def flag_isset(self, flag):
        return flag in self.flags.keys() and self.flags[flag]

    def set_flag(self, flag, state=1):
        self.flags[flag] = state


