'''Read Input from Midi Device'''
import os
import time
import select
import pyinotify
from apres import NoteOn, NoteOff, MIDIStop

class PipeClosed(Exception):
    pass

class TaskHandler(pyinotify.ProcessEvent):
    def __init__(self, controller):
        self.controller = controller
        super().__init__()

    def process_IN_CREATE(self, event):
        if event.name[0:4] == 'midi':
            time.sleep(.5)
            self.controller.connect(event.pathname)

    def process_IN_DELETE(self, event):
        if event.name[0:4] == 'midi':
            self.controller.disconnect(event.pathname)

class MIDIController:
    '''Read Input from Midi Device'''
    def __init__(self, midipath=""):
        self.pipe = None
        self.midipath = None
        if midipath:
            if os.path.exists(midipath):
                self.connect(midipath)
        else:
            for dev in os.listdir('/dev/'):
                if dev[0:4] == 'midi':
                    self.connect('/dev/' + dev)
                    break


        self.flag_close = False
        self.watch_manager = pyinotify.WatchManager()
        notifier = pyinotify.ThreadedNotifier(self.watch_manager, TaskHandler(self))
        notifier.daemon = True
        notifier.start()
        self.watch_manager.add_watch('/dev/', pyinotify.IN_CREATE | pyinotify.IN_DELETE)

    def is_connected(self):
        return bool(self.pipe)

    def connect(self, path):
        if not self.pipe and os.path.exists(path):
            self.pipe = open(path, 'rb')
            self.midipath = path

    def disconnect(self, midipath):
        if self.midipath == midipath:
            try:
                self.pipe.close()
            except:
                pass

            self.pipe = None
            self.midipath = ''

    def close(self):
        self.flag_close = True

    def check_byte(self):
        output = None
        while not output:
            try:
                ready, _, __ = select.select([self.pipe], [], [], 0)
            except TypeError:
                ready = []
            except ValueError:
                ready = []

            if self.pipe in ready:
                output = os.read(self.pipe.fileno(), 1)
                if len(output):
                    output = output[0]
                else:
                    continue

            elif self.flag_close:
                self.disconnect(self.midipath)
                raise PipeClosed()
            else: #wait for input
                time.sleep(.01)

        return output

    def read(self):
        output = None
        try:
            byte = self.check_byte()
            if byte & 0xF0 == 0x90:
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
        except PipeClosed:
            output = MIDIStop()

        return output
