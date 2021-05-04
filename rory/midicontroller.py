'''Read Input from Midi Device'''
import os
import time
import select
import pyinotify
from apres import NoteOn, NoteOff, MIDIStop, ControlChange

class PipeClosed(Exception):
    '''Error Thrown when the midi device pipe is closed or disconnected'''

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
        if event.name[0:4] == 'midi':
            self.controller.disconnect(event.pathname)

class MIDIController:
    DEVROOT = '/dev/'
    '''Read Input from Midi Device'''
    def __init__(self, midipath=""):
        self.pipe = None
        self.midipath = None
        if midipath:
            if os.path.exists(midipath):
                self.connect(midipath)
        else:
            for dev in os.listdir(MIDIController.DEVROOT):
                if dev[0:4] == 'midi':
                    self.connect(MIDIController.DEVROOT + dev)
                    break


        self.watch_manager = pyinotify.WatchManager()
        notifier = pyinotify.ThreadedNotifier(self.watch_manager, TaskHandler(self))
        notifier.daemon = True
        notifier.start()
        self.watch_manager.add_watch(
            MIDIController.DEVROOT,
            pyinotify.IN_CREATE | pyinotify.IN_DELETE
        )

    def is_connected(self):
        '''Check if pipe is open and ready to be read'''
        return bool(self.pipe)

    def connect(self, path):
        '''Attempt to open a pipe to the path specified'''
        if not self.pipe and os.path.exists(path):
            self.pipe = open(path, 'rb')
            self.midipath = path

    def disconnect(self, midipath):
        '''Close the pipe to the path specified'''
        if self.midipath == midipath:
            try:
                if self.pipe != None:
                    self.pipe.close()
            except Exception as e:
                raise e

            self.pipe = None
            self.midipath = ''

    def close(self):
        '''Tear down this midi controller'''
        self.disconnect(self.midipath)

    def check_byte(self):
        '''Attempt to read next byte from pipe'''
        output = None
        while not output:
            try:
                ready, _, __ = select.select([self.pipe], [], [], 0)
            except TypeError:
                ready = []
            except ValueError:
                ready = []

            if self.is_connected():
                if self.pipe in ready:
                    try:
                        output = os.read(self.pipe.fileno(), 1)
                        if output:
                            output = output[0]
                        else:
                            continue
                    except ValueError:
                        continue

                else: #wait for input
                    time.sleep(.01)
            else:
                raise PipeClosed()


        return output

    def read(self):
        '''Read Midi Input Device until relevant event is found'''
        output = None
        try:
            byte = self.check_byte()
            if byte & 0xF0 == 0xB0:
                controller = self.check_byte()
                value = self.check_byte()
                output = ControlChange(channel=(byte & 0x0F), value=value, controller=controller)
            elif byte & 0xF0 == 0x90:
                note = self.check_byte()
                velocity = self.check_byte()
                if velocity == 0:
                    output = NoteOff(note=note, velocity=0, channel=(byte & 0x0F))
                else:
                    output = NoteOn(note=note, velocity=velocity, channel=(byte & 0x0F))
            elif byte & 0xF0 == 0x80:
                note = self.check_byte()
                velocity = self.check_byte()
                output = NoteOff(note=note, velocity=velocity, channel=(byte & 0x0F))
            elif byte & 0xF0 == 0xC0:
                for i in range(1):
                    self.check_byte()
            elif byte == 0xFF:
                _meta_type = self.check_byte()
                for i in range(self.check_byte()):
                    self.check_byte()

        except PipeClosed:
            output = MIDIStop()

        return output
