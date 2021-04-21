'''Plays MIDILike Objects'''
import threading
import time

from apres import MIDI, NoteOn, NoteOff
from rory.midiinterface import MIDIInterface

class Player:
    '''Plays MIDILike Objects'''

    def kill(self):
        ''''Shutdown the player'''
        self.is_active = False
        self.midi_controller.close()

    def next_state(self):
        '''Change the song position to the next state with notes.'''
        self.song_position += 1
        while self.song_position <= self.loop[1] \
        and not self.midi_interface.get_state(self.song_position):
            self.song_position += 1

        self.song_position = min(self.loop[1] + 1, self.song_position)

        if self.song_position > self.loop[1]:
            self.song_position = self.loop[0]


    def prev_state(self):
        '''Change the song position to the last state with notes.'''
        self.song_position -= 1
        while self.song_position > self.loop[0] \
        and not self.midi_interface.get_state(self.song_position):
            self.song_position -= 1

        self.set_state(max(0, self.song_position))

    def set_state(self, song_position):
        '''
            Set the song position as the value in the register,
            then move to the next state with notes.
        '''
        self.song_position = max(0, song_position)

        while self.song_position < self.loop[1] \
        and not self.midi_interface.get_state(self.song_position):
            self.song_position += 1

        self.song_position = min(self.loop[1], self.song_position)

        if self.song_position == self.loop[1]:
            self.song_position = self.loop[0]


    def __init__(self, **kwargs):
        self.active_midi = MIDI(kwargs['path'])

        self.is_active = True
        self.register = 0
        self.loop = [0, 0]
        self.note_range = [21, 21 + 88]

        self.midi_controller = kwargs['controller']
        self.midi_interface = MIDIInterface(self.active_midi, **kwargs)
        self.clear_loop()

        self.pressed_notes = set()
        self.need_to_release = set()

        self.song_position = -1

        self.midi_input_thread = threading.Thread(
            target=self.midi_input_daemon
        )

        self.midi_input_thread.start()
        self.next_state()

    def midi_input_daemon(self):
        '''Listen for and handle midi events coming from the MIDI controller'''
        song_state = set()
        while self.is_active:
            if self.midi_controller.is_connected():
                message = self.midi_controller.read()
                if message:
                    if isinstance(message, NoteOn):
                        self.pressed_notes.add(message.note)
                    elif isinstance(message, NoteOff):
                        try:
                            self.pressed_notes.remove(message.note)
                        except KeyError:
                            pass

                        try:
                            self.need_to_release.remove(message.note)
                        except KeyError:
                            pass
                    song_state = self.midi_interface.get_state(self.song_position)
                if song_state.intersection(self.pressed_notes) == song_state \
                and not self.need_to_release.intersection(song_state):
                    self.need_to_release = self.need_to_release.union(self.pressed_notes)
                    self.next_state()
            else:
                if self.pressed_notes:
                    self.pressed_notes = set()
                    self.need_to_release = set()
                time.sleep(.01)

    def set_loop_start_to_position(self):
        '''Set the beginning of the play loop to the current song position'''
        self.set_loop_start(self.song_position)

    def set_loop_end_to_position(self):
        '''Set the end of the play loop to the current song position'''
        self.set_loop_end(self.song_position)

    def set_loop_start(self, position):
        '''set current positions as loop start'''
        self.loop[0] = min(max(0, position), len(self.midi_interface.state_map) - 1)

    def set_loop_end(self, position):
        '''set current positions as loop end'''
        self.loop[1] = min(max(0, position), len(self.midi_interface.state_map) - 1)

    def clear_loop(self):
        '''Stop Looping'''
        self.loop = [0, len(self.midi_interface.state_map) - 1]

    def set_register_digit(self, digit):
        '''Insert digit to register'''
        assert (digit < 10), "Digit can't be more than 9. Called from somewhere it shouldn't be"

        self.register *= 10
        self.register += digit

    def clear_register(self):
        '''Set the register to 0'''
        self.register = 0

    def jump_to_register_position(self):
        '''Set the song position to the value of the input register'''
        self.set_state(self.register)
        self.clear_register()
