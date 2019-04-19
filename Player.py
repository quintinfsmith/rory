'''Plays MIDILike Objects'''

from Interactor import RegisteredInteractor
from localfuncs import read_character
from MIDIInterface import MIDIInterface
from MidiLib.MidiInterpreter import MIDIInterpreter as MI
from AsciiBox.src.Bleeps import BleepsBox
import threading
import math

class Player(RegisteredInteractor):
    '''Plays MIDILike Objects'''
    NEXT_STATE = 1 << 1
    PREV_STATE = 1 << 2
    RAISE_QUIT = 1 << 3
    RAISE_MIDI_INPUT_CHANGE = 1 << 4 # TODO: Possibly does nothing?
    RAISE_JUMP = 1 << 5
    RAISE_SAVE = 1 << 6
    RAISE_IGNORE_CHANNEL = 1 << 7

    rechannelling = -1

    SHARPS = (1, 3, 6, 8, 10)

    sidebar = '|'
    NOTELIST = 'CCDDEFFGGAAB'
    #NOTELIST = '3456789AB012'

    def quit(self):
        ''''shutdown the player Box'''
        self.set_flag(self.RAISE_QUIT)
        self.is_active = False

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

    def set_rechannel(self):
        '''start rechanneling events'''
        if self.general_register:
            self.rechannelling = self.general_register
        self.clear_register()

    def unset_rechannel(self):
        '''stop rechanneling events'''
        self.rechannelling = -1
        self.clear_register()

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


    def __init__(self, bleepsbox):
        super().__init__()
        self.bleepsbox = bleepsbox
        self.redrawing = False
        self.redraw_queue = []

        self.is_active = True

        self.loop = [0, -1]
        self.assign_sequence("j", self.next_state)
        self.assign_sequence("k", self.prev_state)
        self.assign_sequence("i", self.raise_ignore_channel)
        self.assign_sequence("p", self.jump)
        self.assign_sequence("q", self.quit)
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
        self.active_box = None # Bleepsbox, Row where keypresses are displayed

        self.displayed_box_box = None
        self.state_boxes = None
        self.active_boxes = None
        self.position_display_box = None

    def width(self):
        return (self.note_range[1] - self.note_range[0]) + 2

    def get_channel_color(self, channel):
        colors = [
            BleepsBox.BRIGHTYELLOW,
            BleepsBox.WHITE,
            BleepsBox.CYAN,
            BleepsBox.GREEN,
            BleepsBox.MAGENTA,
            BleepsBox.BLUE,
            BleepsBox.BRIGHTBLACK, # i *think* it's channel 7 that is drums... if so, this is just a placeholder
            BleepsBox.RED
        ]
        color = colors[channel % 8]

        if channel > 8:
            color ^= BleepsBox.BRIGHT

        return color

    def get_displayed_key_position(self, midi_key):
        piano_position = midi_key - self.note_range[0]
        octave = piano_position // 12
        piano_key = piano_position % 12
        position = (octave * 14) + piano_key

        if piano_key > 2: # B
            position += 1
        if piano_key > 7:
            position += 1

        return position


    def update_pressed_line(self, pressed, matched):
        '''Redraw Pressed Keys'''
        if not matched:
            matched = []

        # No Longer Pressed
        for midi_index in self.last_pressed.difference(pressed):
            piano_index = midi_index - self.note_range[0]
            keybox = self.active_boxes[piano_index]
            keybox.unset_color()
            keybox.unsetc(0, 0)

        # Newly Pressed
        for midi_index in pressed.difference(self.last_pressed):
            piano_index = midi_index - self.note_range[0]
            keybox = self.active_boxes[piano_index]
            #character = self.NOTELIST[midi_index % len(self.NOTELIST)]
            keybox.setc(0, 0, chr(0x1F831))
            keybox.set_fg_color(BleepsBox.BRIGHTWHITE)


        self.last_pressed = pressed

        self.refresh()

    def play_along(self, path, controller):
        '''Display notes in console. Main function'''
        midilike = MI.parse_midi(path)
        midi_interface = MIDIInterface(midilike, controller)
        space_buffer = 8

        self.active_midi = midilike
        self.channels_used = midi_interface.channels_used

        num_of_keys = self.note_range[1] - self.note_range[0] + 1

        self.displayed_box_box = self.bleepsbox.new_box(self.get_displayed_key_position(self.note_range[1]), self.bleepsbox.height)
        ssb_offset = (self.bleepsbox.width - self.displayed_box_box.width) // 2
        self.displayed_box_box.move(ssb_offset, 0)
        self.state_boxes = {}

        self.bleepsbox.fill(' ')


        # Populate state_boxes
        for j, current_state in enumerate(midi_interface.event_map):
            if current_state.values():
                new_box = self.displayed_box_box.new_box(self.displayed_box_box.width, 1)
                new_box.detach()
                self.state_boxes[j] = new_box
                for event in current_state.values():
                    n = event.note - self.note_range[0]
                    xposition = self.get_displayed_key_position(event.note)

                    key_box = new_box.new_box(1, 1)
                    key_box.move(xposition, 0)
                    key_box.setc(0, 0, self.NOTELIST[event.note % 12])
                    if event.note % 12 in self.SHARPS:
                        key_box.set_bg_color(self.get_channel_color(event.channel))
                        key_box.set_fg_color(BleepsBox.BLACK)
                    else:
                        key_box.set_fg_color(self.get_channel_color(event.channel))

        # Populate row where active keys are displayed
        self.active_box = self.bleepsbox.new_box(self.displayed_box_box.width, 1)
        self.active_box.move(ssb_offset, self.bleepsbox.height - space_buffer)
        self.active_boxes = []


        # Draw guides, and populate active_boxes
        self.bleepsbox.set_fg_color(BleepsBox.BRIGHTBLACK)
        ypos = self.bleepsbox.height - space_buffer - 1
        for n in range(num_of_keys):
            midi_note = n + self.note_range[0]
            x = self.get_displayed_key_position(midi_note)
            new_box = self.active_box.new_box(1, 1)
            new_box.move(x, 0)
            new_box.set_bg_color(BleepsBox.BLACK)
            self.active_boxes.append(new_box)

            if midi_note % 12 in self.SHARPS:
                self.bleepsbox.setc(x + ssb_offset, ypos, chr(9607))
                self.bleepsbox.setc(x + ssb_offset, ypos + 1, chr(9524))
            else:
                self.bleepsbox.setc(x + ssb_offset, ypos + 1, chr(9472))

            if not (x % 14):
                self.bleepsbox.setc(x + ssb_offset, ypos + 2, chr(9474))
                self.bleepsbox.setc(x + ssb_offset, ypos - 1, chr(9474))

        for i in range(math.ceil(num_of_keys / 12)):
            x = (i * 14) + 3
            self.bleepsbox.setc(x + ssb_offset, ypos + 1, chr(9524))
            self.bleepsbox.setc(x + ssb_offset, ypos, chr(9591))
            if i + 1 < math.ceil(num_of_keys / 12):
                x = (i * 14) + 9
                self.bleepsbox.setc(x + ssb_offset, ypos + 1, chr(9524))
                self.bleepsbox.setc(x + ssb_offset, ypos, chr(9591))

        for y in range(self.bleepsbox.height):
            self.bleepsbox.setc(ssb_offset - 1, y, chr(9474))
            self.bleepsbox.setc(ssb_offset + self.displayed_box_box.width, y, chr(9474))

        self.position_display_box = self.bleepsbox.new_box(self.bleepsbox.width, 1)
        self.position_display_box.move(0, self.bleepsbox.height - 1)

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
            else:# Can't Happen. will loop to start before this happens
                result = self.RAISE_QUIT


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
                    x = self.position_display_box.width - len(strpos) - 1 + c
                    self.position_display_box.setc(x, 0, character)

                to_detach = []
                for box in self.displayed_box_box.boxes.values():
                    to_detach.append(box)

                while to_detach:
                    to_detach.pop().detach()

                try:
                    for i in range(self.displayed_box_box.height):
                        try:
                            box_to_use = self.state_boxes[max(0, i + self.song_position - space_buffer)]
                        except KeyError:
                            continue
                        self.displayed_box_box.attach(box_to_use)
                        box_to_use.move(0, self.displayed_box_box.height - 1 - i)
                except IndexError:
                    pass

                self.refresh(2)

        self.quit()

    def _wait_for_input(self, midi_interface):
        '''Waits for user to press correct key combination'''
        pressed = midi_interface.get_pressed()
        while not midi_interface.states_unmatch(self.song_position, pressed):
            self.update_pressed_line(pressed, midi_interface.get_state(self.song_position))
            pressed = midi_interface.get_pressed()

        input_given = 0
        while input_given == 0:
            pressed = midi_interface.get_pressed()
            if midi_interface.states_match(self.song_position, pressed, self.ignored_channels):
                input_given = self.NEXT_STATE
            elif self.flag_isset(self.RAISE_IGNORE_CHANNEL):
                self.flags[self.RAISE_IGNORE_CHANNEL] = 0
                self.toggle_ignore_channel()
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

    def _refresh(self, key):
        if self.redrawing == 0:
            self.redraw_queue.append(key)
            while self.redraw_queue:
                self.redrawing = self.redraw_queue.pop(0)
                self.bleepsbox.draw()
            self.redrawing = 0
        elif self.redrawing != key and key not in self.redraw_queue:
            self.redraw_queue.append(key)

    def refresh(self, key=1):
        if not self.redrawing:
            thread = threading.Thread(target=self._refresh, args=(key, ))
            thread.start()

