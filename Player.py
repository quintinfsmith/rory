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

    SHARPS = (1,3,6,8,10)

    def __init__(self):
        self.note_range = [0, 127]
        self.flags = {}
        self.previously_expected_set = set()
        self.post_buffer = 4
        self.screen_size = console.getTerminalSize()
        self.screen_size = (self.screen_size[0], self.screen_size[1] - 3)

    def _get_note_str(self, note, channel):
        """Convert Midi Note byte to Legible Character"""
        note_list = 'CCDDEFFGGAAB'
        note %= 12
        if note in self.SHARPS:
            return '\033[7;3' + str(channel) + 'm' + note_list[note] + '\033[0m'
        else:
            return '\033[3' + str(channel) + 'm' + note_list[note] + '\033[0m'

    def draw_input_line(self, user_input, expected):
        num_of_keys = self.note_range[1] - self.note_range[0]
        x_offset = int((self.screen_size[0] - num_of_keys - 2) / 2)
        y_offset = self.screen_size[1] - 1 - self.post_buffer

        expected_set = set(expected.keys())

        line = []
        for i in range(num_of_keys):
            note = i + self.note_range[0]
            if i in expected_set:
                char = self._get_note_str(i, expected[i].channel + 1)
            else:
                char = '-'
            if i in user_input:
                char = '\033[42m' + char + '\033[0m'
            line.append(char)
        sys.stdout.write('\033[' + str(y_offset) + ';' + str(x_offset) + 'H')
        sys.stdout.write('\033[0m' + ''.join(line) + '\n')


    def play_along(self, midilike, controller, ignore):
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
            sys.stdout.write('\033[%d;%dH%s\033[0m\n' % (y, x_offset, (' ' * num_of_keys)))

        while state_list:
            current_display = state_list[0:screen_height - self.post_buffer][::-1]
            current_display += states_matched[0:min(self.post_buffer, len(states_matched))]
            mark_pos = screen_height - int(screen_height * song_position / len(state_list))
            
            for y in range(len(current_display)):
                for x in to_clear[y]:
                    sys.stdout.write("\033[%d;%dH " % (y,x))
                line = current_display[y]
                to_clear[y] = []
                for key, event in line.items():
                    sys.stdout.write('\033[%d;%dH' % (y, x_offset + key - self.note_range[0]))
                    sys.stdout.write(self._get_note_str(key, event.channel + 1))
                    to_clear[y].append(x_offset + key - self.note_range[0])

            sys.stdout.write('\033[%d;%dH' % (screen_height, x_offset))
            sys.stdout.write('\n')

            current_state = state_list.pop(0)
            states_matched.insert(0, current_state)
            result = self._wait_for_input(current_state, controller, ignore)
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
        sys.stdout.write('\n' + (' ' * screen_width))

    def _wait_for_input(self, expected, controller, ignore=[]):
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
            if not channel in ignore:
                if not key in self.previously_expected_set:
                    expected_set.add(key)
                    expected_unset.add(key)
                actual_set.add(key)

        # If the key was expected NOT to be pressed last state but was, the user needs to release and press again
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

