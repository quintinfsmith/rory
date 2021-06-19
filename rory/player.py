'''Plays MIDILike Objects'''
import threading
import time
import os
import pyinotify

from apres import MIDI, MIDIController
from rory.midiinterface import MIDIInterface

class TaskHandler(pyinotify.ProcessEvent):
    '''Event hooks to connect/disconnect from newly made midi device'''
    def __init__(self, controller):
        self.controller = controller
        super().__init__()

    def process_IN_CREATE(self, event):
        '''Hook to connect when midi device is plugged in'''
        if event.name[0:4] == 'midi':
            time.sleep(.5)
            self.controller.connect(event.pathname)

    def process_IN_DELETE(self, event):
        '''Hook to disconnect when midi device is unplugged'''
        if self.controller.midipath == event.pathname:
            self.controller.disconnect()

class RoryController(MIDIController):
    def __init__(self, player, path=""):
        self.player = player

        if not path:
            for filename in os.listdir("/dev/"):
                if "midi" in filename:
                    path = "/dev/%s" % filename
                    break

        super().__init__(path)

        self.pressed = set()

        self.watch_manager = pyinotify.WatchManager()
        notifier = pyinotify.ThreadedNotifier(self.watch_manager, TaskHandler(self))
        notifier.daemon = True
        notifier.start()
        self.watch_manager.add_watch(
            "/dev/",
            pyinotify.IN_CREATE | pyinotify.IN_DELETE
        )

    def hook_NoteOn(self, event):
        if event.velocity == 0:
            self.release_note(event.note)
        else:
            self.press_note(event.note)

    def hook_NoteOff(self, event):
        self.release_note(event.note)

    def press_note(self, note):
        '''Press a Midi Note'''
        self.pressed.add(note)
        self.player.do_state_check()

    def release_note(self, note):
        '''Release a Midi Note'''
        self.pressed.add(note)
        try:
            self.pressed.remove(note)
        except KeyError:
            pass
        try:
            self.player.need_to_release.remove(note)
        except KeyError:
            pass
        self.player.do_state_check()

    def connect(self, path):
        self.player.need_to_release = set()
        try:
            super().connect(path)
            # Automatically start listening for input on connect
            input_thread = threading.Thread(
                target=self.listen
            )
            input_thread.start()
        except FileNotFoundError:
            pass

class Player:
    '''Plays MIDILike Objects'''

    def kill(self):
        ''''Shutdown the player'''
        self.is_active = False
        self.midi_controller.close()

    def next_state(self):
        '''Change the song position to the next state with notes.'''
        new_position = self.song_position + 1
        while new_position <= self.loop[1] \
        and not self.midi_interface.get_state(new_position, self.ignored_channels):
            new_position += 1

        new_position = min(self.loop[1] + 1, new_position)

        if new_position > self.loop[1]:
            new_position = self.loop[0]
            self.song_position = new_position
        elif self.use_time_delay:
            delay = self.calculate_delay(new_position)
            diff = new_position - self.song_position
            delay /= diff
            for _ in range(diff):
                time.sleep(delay)
                self.song_position += 1
        else:
            self.song_position = new_position


    def prev_state(self):
        '''Change the song position to the last state with notes.'''
        self.song_position -= 1
        while self.song_position > self.loop[0] \
        and not self.midi_interface.get_state(self.song_position, self.ignored_channels):
            self.song_position -= 1

        self.set_state(max(0, self.song_position))

    def set_state(self, song_position):
        '''
            Set the song position as the value in the register,
            then move to the next state with notes.
        '''
        self.song_position = max(0, song_position)

        while self.song_position < self.loop[1] \
        and not self.midi_interface.get_state(self.song_position, self.ignored_channels):
            self.song_position += 1

        self.song_position = min(self.loop[1], self.song_position)

        if self.song_position == self.loop[1]:
            self.song_position = self.loop[0]

    def set_measure(self, measure):
        state = self.midi_interface.get_first_tick_in_measure(measure)
        self.set_state(state)


    def __init__(self, **kwargs):
        self.active_midi = MIDI(kwargs['path'])

        self.is_active = True
        self.register = 0
        self.loop = [0, 0]
        self.note_range = [21, 21 + 88]

        self.ignored_channels = set()


        self.use_time_delay = False
        if "use_delay" in kwargs.keys():
            self.use_time_delay = kwargs["use_delay"]

        self.midi_interface = MIDIInterface(self.active_midi, **kwargs)

        self.clear_loop()

        self.need_to_release = set()

        self.song_position = -1

        self.next_state()

        if 'controller_path' in kwargs:
            self.midi_controller = RoryController(self, kwargs['controller_path'])
        else:
            self.midi_controller = RoryController(self)



    def calculate_delay(self, new_pos):
        '''
            Calculate the time, in seconds, that is theoritically in between
            the current position and the given one
        '''
        tick_wait = self.midi_interface.get_tick_wait(self.song_position, new_pos)
        beats = tick_wait / self.active_midi.ppqn

        seconds_per_beat = 60 / self.midi_interface.get_tempo(self.song_position)
        actual_wait = beats * seconds_per_beat

        return actual_wait

    def get_pressed_notes(self):
        ''' Get the notes that the midi device has held down '''
        return self.midi_controller.pressed.copy()

    def do_state_check(self):
        ''' Check if the midi device is pressing the coresponding notes '''
        song_state = self.midi_interface.get_state(self.song_position, self.ignored_channels)
        pressed = self.get_pressed_notes()
        if song_state.intersection(pressed) == song_state \
        and not self.need_to_release.intersection(song_state):
            self.need_to_release = self.need_to_release.union(pressed)
            self.next_state()

    def toggle_ignore_channel(self, channel):
        '''
            Add or remove a channel to be ignored when considering
            if the song position needs to be incremented or decremented
        '''
        if channel < 16:
            if channel in self.ignored_channels:
                self.ignored_channels.remove(channel)
            else:
                self.ignored_channels.add(channel)

        self.set_state(self.song_position)

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
