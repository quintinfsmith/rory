'''Plays MIDILike Objects'''
import time
import os
import asyncio
from asyncinotify import Inotify, Mask
import threading

from apres import MIDI, MIDIController, MIDIEvent, NoteOn, NoteOff
from .midiinterface import MIDIInterface

class ControllerManager:
    def __init__(self):
        self.callbacks = {}

        self.pressed = set()
        self.state_check_ticket = 0
        self.processing_ticket = 0

        channel = 0
        device_index = 0
        self.controller = None
        self.active_key = None
        self.is_listening = True
        self.watcher = threading.Thread(target=self.kludge_watch_for_midi_devices)
        self.watcher.start()

    def kludge_watch_for_midi_devices(self):
        asyncio.run(self.async_process())

    async def async_process(self):
        watcher_task = asyncio.create_task(self.watch_for_midi_devices())
        await asyncio.create_task(self.task_killer(watcher_task))

    async def task_killer(self, task):
        """Kill the an async task when is_listening becomes false."""
        while self.is_listening:
           await asyncio.sleep(.5)
        task.cancel()

    async def watch_for_midi_devices(self):
        self.is_listening = True
        for filename in os.listdir("/dev/snd/"):
            if "midi" in filename:
                device_index = int(filename[filename.rfind("D") + 1])
                channel = int(filename[filename.rfind("C") + 1])
                self.new_controller(channel, device_index)
                break

        with Inotify() as inotify:
            inotify.add_watch("/dev/snd/", Mask.CREATE | Mask.DELETE)

            async for event in inotify:
                if event.name is None:
                    continue

                file_name = event.path.parts[-1]
                if event.mask == Mask.CREATE:
                    if file_name[0:4] == 'midi':
                        time.sleep(.5)
                        channel = int(file_name[file_name.rfind("C") + 1])
                        device_id = int(file_name[file_name.rfind("D") + 1])
                        self.new_controller(channel, device_id)

                elif event.mask == Mask.DELETE:
                    if 'midi' in file_name:
                        channel = file_name[file_name.rfind("C") + 1]
                        device_id = file_name[file_name.rfind("D") + 1]
                        active_key = self.get_active_key()
                        if active_key == (channel, device_id):
                            self.disconnect_current()

    def get_pressed(self):
        return self.pressed.copy()

    def close(self):
        self.disconnect_current()
        self.is_listening = False

    def press_note(self, note):
        '''Press a Midi Note'''
        self.pressed.add(note)
        self.do_state_check()

    def release_note(self, note):
        '''Release a Midi Note'''
        try:
            self.pressed.remove(note)
        except KeyError:
            pass
        try:
            self._do_callbacks("release_note", note)
        except KeyError:
            pass
        self.do_state_check()

    def do_state_check(self):
        ''' Ticketed wrapper for player's do_state_check '''
        my_ticket = self.state_check_ticket
        self.state_check_ticket += 1

        while my_ticket != self.processing_ticket:
            time.sleep(.05)

        # If there are newer tickets queued, skip this state_check
        if my_ticket == self.state_check_ticket - 1:
            self._do_callbacks('do_state_check')
        else:
            pass

        self.processing_ticket += 1

    def _do_callbacks(self, key, *args):
        if key in self.callbacks:
            for (callback, context_args) in self.callbacks[key]:
                callback(*context_args, *args)

    def add_callback(self, key, callback, *args):
        if key not in self.callbacks:
            self.callbacks[key] = []
        self.callbacks[key].append((callback, args))

    def new_controller(self, channel, device_id):
        if self.controller is not None:
            self.controller.close()

        self._do_callbacks("new_controller")
        self.controller = RoryController(channel, device_id, self)
        self.active_key = (channel, device_id)
        thread = threading.Thread(target=self.controller.listen)
        thread.start()

    def disconnect_current(self):
        if self.controller is None:
            return

        self.controller.close()
        self.controller = None

    def get_active_key(self):
        return self.active_key

    def is_connected(self):
        return self.controller is not None


class RoryController(MIDIController):
    def __init__(self, channel, device_index, controller_manager):
        super().__init__(channel, device_index)
        self.controller_manager = controller_manager

    def hook_NoteOn(self, event):
        if event.velocity == 0:
            self.release_note(event.note)
        else:
            self.press_note(event.note)

    def hook_NoteOff(self, event):
        self.release_note(event.note)

    def press_note(self, note):
        '''Press a Midi Note'''
        self.controller_manager.press_note(note)

    def release_note(self, note):
        '''Release a Midi Note'''
        self.controller_manager.release_note(note)

