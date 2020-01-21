'''Plays MIDILike Objects'''

from Interactor import RegisteredInteractor
from localfuncs import read_character
from MIDIInterface import MIDIInterface
from MidiLib.MidiInterpreter import MIDIInterpreter as MI
from Rect import Rect
import threading
import math, time

def logg(msg):
    with open('logg', 'a') as fp:
        fp.write(str(msg) + "\n")

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


    def __init__(self, rect):
        super().__init__()
        self.rect = rect

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

        self.displayed_box_box = None
        self.state_boxes = None
        self.active_boxes = None
        self.position_display_box = None

        self.flag_refresh = True

    def width(self):
        return (self.note_range[1] - self.note_range[0]) + 2

    def get_channel_color(self, channel):
        colors = [
            Rect.BRIGHTYELLOW,
            Rect.WHITE,
            Rect.CYAN,
            Rect.GREEN,
            Rect.MAGENTA,
            Rect.BLUE,
            Rect.BRIGHTBLACK, # i *think* it's channel 7 that is drums... if so, this is just a placeholder
            Rect.RED
        ]
        color = colors[channel % 8]

        if channel > 8:
            color ^= Rect.BRIGHT

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
            keybox.detach()
            #keybox.unset_color()
            #keybox.unset_character(0, 0)
            self.displayed_box_box.queue_draw()
            self.flag_refresh = True

        # Newly Pressed
        for midi_index in pressed.difference(self.last_pressed):
            piano_index = midi_index - self.note_range[0]
            keybox = self.active_boxes[piano_index]
            self.displayed_box_box.attach(keybox)
            character = self.NOTELIST[midi_index % len(self.NOTELIST)]
            keybox.set_character(0, 0, character)
            keybox.set_fg_color(Rect.BRIGHTWHITE)
            if matched.intersection(set([midi_index])):
                keybox.set_bg_color(Rect.BRIGHTGREEN)
            else:
                keybox.set_bg_color(Rect.BRIGHTRED)
            self.displayed_box_box.queue_draw()
            self.flag_refresh = True


        self.last_pressed = pressed

    def play_along(self, path, controller):
        '''Display notes in console. Main function'''
        midilike = MI.parse_midi(path)
        midi_interface = MIDIInterface(midilike, controller)
        space_buffer = 8

        self.active_midi = midilike
        self.channels_used = midi_interface.channels_used

        num_of_keys = self.note_range[1] - self.note_range[0] + 1
        box_width = self.get_displayed_key_position(self.note_range[1] + 1) - self.get_displayed_key_position(self.note_range[0])

        self.displayed_box_box = self.rect.new_rect(
            width=box_width,
            height=self.rect.height
        )

        buffer_rect = self.displayed_box_box.new_rect(
            width=box_width,
            height=self.rect.height
        )

        ssb_offset = (self.rect.width - self.displayed_box_box.width) // 2
        self.displayed_box_box.move(ssb_offset, 0)
        self.state_boxes = {}


        # Populate state_boxes
        for j, current_state in enumerate(midi_interface.event_map):
            if current_state.values():
                self.state_boxes[j] = {}

                for event in current_state.values():
                    key_box = buffer_rect.new_rect(
                        width=1,
                        height=1
                    )
                    key_box.set_character(0, 0, self.NOTELIST[event.note % 12])

                    if event.note % 12 in self.SHARPS:
                        key_box.set_bg_color(self.get_channel_color(event.channel))
                        key_box.set_fg_color(Rect.BLACK)
                    else:
                        key_box.set_fg_color(self.get_channel_color(event.channel))

                    key_box.detach()

                    x = self.get_displayed_key_position(event.note)
                    self.state_boxes[j][event.note] = (x, key_box)

        # Populate row where active keys are displayed
        self.active_boxes = []

        # Draw guides, and populate active_boxes
        buffer_rect.set_fg_color(Rect.BRIGHTBLACK)
        #self.displayed_box_box.set_bg_color(Rect.BRIGHTRED)
        ypos = self.displayed_box_box.height - space_buffer - 1
        for n in range(num_of_keys):
            midi_note = n + self.note_range[0]
            x = self.get_displayed_key_position(midi_note)
            new_box = buffer_rect.new_rect()
            new_box.move(x, buffer_rect.height - space_buffer)
            new_box.set_bg_color(Rect.YELLOW)
            self.active_boxes.append(new_box)

            if midi_note % 12 in self.SHARPS:
                buffer_rect.set_character(x, ypos, chr(9607))
                buffer_rect.set_character(x, ypos + 1, chr(9524))
            else:
                buffer_rect.set_character(x, ypos + 1, chr(9472))

            if not (x % 14):
                buffer_rect.set_character(x, ypos + 2, chr(9474))
                for i in range((ypos + 1) // 4):
                    buffer_rect.set_character(x, ypos - 1 - (i * 4), chr(9474))

        for i in range(math.ceil(num_of_keys / 12)):
            x = (i * 14) + 3
            buffer_rect.set_character(x, ypos + 1, chr(9524))
            buffer_rect.set_character(x, ypos, chr(9591))
            if i + 1 < math.ceil(num_of_keys / 12):
                x = (i * 14) + 9
                buffer_rect.set_character(x, ypos + 1, chr(9524))
                buffer_rect.set_character(x, ypos, chr(9591))

        for y in range(buffer_rect.height):
            buffer_rect.set_character(0, y, chr(9474))
            buffer_rect.set_character(buffer_rect.width - 1, y, chr(9474))

        self.position_display_box = self.displayed_box_box.new_rect(
            width=self.displayed_box_box.width - 1,
            height=1
        )


        self.start_display_daemon()

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
                self.position_display_box.resize(len(strpos), 1)
                xpos = self.displayed_box_box.width - self.position_display_box.width - 1
                self.position_display_box.move(xpos, buffer_rect.height - 1)

                for c, character in enumerate(strpos):
                    self.position_display_box.set_character(c, 0, character)

                to_detach = []
                for box in buffer_rect.rects.values():
                    if box != self.position_display_box:
                        to_detach.append(box)

                while to_detach:
                    to_detach.pop().detach()

                for i in range(buffer_rect.height):
                    try:
                        boxes_to_use = self.state_boxes[max(0, (self.song_position - space_buffer) + i)]
                    except KeyError:
                        continue

                    for note, (keypos, box) in boxes_to_use.items():
                        buffer_rect.attach(box)
                        box.move(keypos, buffer_rect.height - i)
                        box.queue_draw()

                buffer_rect.queue_draw()
                self.position_display_box.queue_draw()
                self.flag_refresh = True

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

    def display_daemon(self):
        delay = 1 / 60
        while self.is_active:
            if self.flag_refresh:
                self.flag_refresh = False
                self.rect.draw_queued()
            time.sleep(delay)

    def start_display_daemon(self):
        thread = threading.Thread(target=self.display_daemon)
        thread.start()


