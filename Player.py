import console
import time
import sys
from getCh import getCh
from MidiInterpreter import *
from MIDIController import *

class Player(object):
    """Plays MIDILike Objects"""
    NEXT_STATE = 1
    PREV_STATE = 2
    RAISE_QUIT = 4
    RAISE_CHANGE = 8

    SHARPS = (1, 3, 6, 8, 10)

    SIDEBAR = '|'

    def __init__(self):
        self.flags = {}
        self.ignore = []
        self.note_range = [0, 127]
        self.post_buffer = 4
        self.previously_expected_set = set()
        self.screen_size = console.getTerminalSize()
        self.screen_size = (self.screen_size[0], self.screen_size[1] - 3)

    def toggle_track0(self):
        self.toggle_trackn(0)

    def toggle_track1(self):
        self.toggle_trackn(1)

    def toggle_track2(self):
        self.toggle_trackn(2)

    def toggle_track3(self):
        self.toggle_trackn(3)

    def toggle_track4(self):
        self.toggle_trackn(4)

    def toggle_track5(self):
        self.toggle_trackn(5)

    def toggle_track6(self):
        self.toggle_trackn(6)

    def toggle_track7(self):
        self.toggle_trackn(7)

    def toggle_track8(self):
        self.toggle_trackn(8)

    def toggle_track9(self):
        self.toggle_trackn(9)

    def toggle_track10(self):
        self.toggle_trackn(10)

    def toggle_track11(self):
        self.toggle_trackn(11)

    def toggle_track12(self):
        self.toggle_trackn(12)

    def toggle_track13(self):
        self.toggle_trackn(13)

    def toggle_track14(self):
        self.toggle_trackn(14)

    def toggle_track15(self):
        self.toggle_trackn(15)

    def toggle_trackn(self, n):
        if n in self.ignore:
            self.ignore.remove(n)
        else:
            self.ignore.append(n)
        self.set_flag(self.RAISE_CHANGE)

    def _get_note_str(self, note, channel):
        """Convert Midi Note byte to Legible Character"""
        note_list = 'CCDDEFFGGAAB'
        note %= 12
        if note in self.SHARPS:
            return "\033[7;3%dm%s\033[0m" % (channel, note_list[note])
        return "\033[3%dm%s\033[0m" % (channel, note_list[note])

    def draw_input_line(self, user_input, expected):
        num_of_keys = self.note_range[1] - self.note_range[0]
        x_offset = int((self.screen_size[0] - num_of_keys - 2) / 2)
        y_offset = self.screen_size[1] - 1 - self.post_buffer

        expected_set = set(expected.keys())

        line = []
        line.append("\033[%d;%dH\033[0m%s" % (y_offset, x_offset, self.SIDEBAR))
        for i in range(num_of_keys):
            note = i + self.note_range[0]
            if i in expected_set:
                char = self._get_note_str(i, expected[i].channel + 1)
            else:
                char = '-'
            if i in user_input:
                char = "\033[42m%s\033[0m" % (char)
            line.append(char)
        line.append("%s\n" % (self.SIDEBAR))
        sys.stdout.write("".join(line))

    def play_along(self, midilike, controller):
        """Display notes in console. Main function"""
        if controller.connected:
            controller.listen()

        num_of_keys = self.note_range[1] - self.note_range[0]
        squash_factor = 4 / midilike.tpqn

        state_list = []
        pressed_keys = {}
        for tick in range(len(midilike)):
            for track in midilike.tracks:
                for event in track.get_events(tick):
                    if event.eid == event.NOTE_ON:
                        if event.velocity == 0 and event.note in pressed_keys.keys():
                            del pressed_keys[event.note]
                        else:
                            pressed_keys[event.note] = event
                    elif event.eid == event.NOTE_OFF and event.note in pressed_keys.keys():
                        del pressed_keys[event.note]
            state_list.append(pressed_keys.copy())

        # Shrink State_list length
        screen_width, screen_height = self.screen_size
        compressed_state_list = []
        for y in range(int(len(state_list) * squash_factor)):
            compressed_state_list.append(state_list[int(y / squash_factor)])
        state_list = compressed_state_list
        for _ in range(self.post_buffer * 5):
            state_list.insert(0, {})
        for _ in range(screen_height):
            state_list.append({})


        song_position = 0
        x_offset = int((console.getTerminalSize()[0] - num_of_keys - 2) / 2)
        states_matched = []
        displayed = []
        to_clear = [[]] * (screen_height + self.post_buffer)

        for y in range(screen_height):
            sys.stdout.write('\033[%d;%dH%s%s%s\033[0m\n' %
                             (y, x_offset, self.SIDEBAR, (' ' * num_of_keys), self.SIDEBAR))

        while state_list:
            current_display = state_list[0:screen_height - self.post_buffer][::-1]
            current_display += states_matched[0:min(self.post_buffer, len(states_matched))]
            mark_pos = screen_height - int(screen_height * song_position / len(state_list))

            for y in range(len(current_display)):
                for x in to_clear[y]:
                    sys.stdout.write("\033[%d;%dH " % (y, x))
                line = current_display[y]
                to_clear[y] = []
                for key, event in line.items():
                    sys.stdout.write('\033[%d;%dH' % (y, x_offset + key - self.note_range[0]))
                    sys.stdout.write(self._get_note_str(key, event.channel + 1))
                    to_clear[y].append(x_offset + key - self.note_range[0])

            sys.stdout.write('\033[%d;%dH\n' % (screen_height, x_offset))

            current_state = state_list.pop(0)
            states_matched.insert(0, current_state)
            result = self._wait_for_input(current_state, controller)
            if result == self.NEXT_STATE:
                song_position += 1
            elif result == self.PREV_STATE:
                # return current state to the queue
                # then return the state before that
                song_position -= 1
                state_list.insert(0, states_matched.pop(0))
                while len(states_matched) > 1 and not len(states_matched[0].keys()):
                    state_list.insert(0, states_matched.pop(0))

                if states_matched:
                    state_list.insert(0, states_matched.pop(0))

            elif result == self.RAISE_QUIT:
                break

        sys.stdout.write("\n".ljust(screen_width+1))

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

        # If the key was expected NOT to be pressed last state but was,
        # the user needs to release and press again
        while expected_unset:
            expected_unset &= controller.get_pressed()

        input_given = 0
        last_pressed = set()
        self.draw_input_line(last_pressed, expected)
        while input_given == 0:
            pressed = controller.get_pressed()
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
            elif self.flag_isset(self.RAISE_CHANGE):
                self.flags[self.RAISE_CHANGE] = 0
                return self._wait_for_input(expected, controller)
            else:
                time.sleep(.01)
                continue
            if pressed.symmetric_difference(last_pressed):
                self.draw_input_line(pressed, expected)
            last_pressed = pressed
        return input_given

    def flag_isset(self, flag):
        return flag in self.flags.keys() and self.flags[flag]

    def set_flag(self, flag, state=1):
        self.flags[flag] = state

    def quit(self):
        self.set_flag(self.RAISE_QUIT)

    def next_state(self):
        self.set_flag(self.NEXT_STATE)

    def prev_state(self):
        self.set_flag(self.PREV_STATE)

