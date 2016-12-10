'''Read Input from Midi Device'''
import os
import time

from MIDIEvent import *
from MIDILike import MIDILike, MIDILikeTrack

class MIDIController(object):
    '''Read Input from Midi Device'''
    def __init__(self, midipath="/dev/midi1"):
        self.connected = os.path.exists(midipath)
        if not self.connected:
            self.pipe = open('/dev/zero', 'rb')
        else:
            self.pipe = open(midipath, 'rb')
        self.current_pressed = set([])
        self.history_track = MIDILikeTrack()
        self.listening = False
        self.changed = True
        self.tosend = set([])
        self.recording = 0

    def listen(self):
        '''Start listening for MIDI Inputs'''
        import threading
        thread = threading.Thread(target=self._listen)
        thread.daemon = True
        thread.start()

    def save_history(self, path="history.mid"):
        midilike = MIDILike()
        midilike.set_tpqn(120)
        midilike.set_format(1)
        midilike.add_track(self.history_track)
        midilike.save_as(path)

    def enable_note(self, note, velocity, tick):
        '''Add note to set of pressed Keys'''
        self.current_pressed.add(note)
        self.changed = True
        if self.recording:
            e = NoteOnEvent(0, note, velocity)
            self.history_track.add_event(tick, e)

    def disable_note(self, note, tick):
        '''remove note from set of pressed Keys'''
        self.current_pressed.remove(note)
        self.changed = True
        if self.recording:
            e = NoteOffEvent(0, note, 00)
            self.history_track.add_event(tick, e)

    def force_empty(self):
        '''Clear list of pressed Keys'''
        self.current_pressed = set()
        self.changed = True

    def toggle_recording(self, path=""):
        if self.recording == 0:
            self.midilike = MIDILike()
            self.start_recording()
        else:
            if path:
                self.save_history(path)
            self.stop_recording()
            
    def start_recording(self):
        self.recording = time.time()

    def stop_recording(self):
        self.recording = 0

    def _listen(self):
        self.listening = True
        tps = 240 # 120 tqpn, 2 qnps
        
        while self.listening:
            byte = self.pipe.read(1)[0]
            ts = time.time() - self.recording
            tick = int(ts * tps)
            if byte & 0xF0 == 0x90:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if velocity == 0 and note in self.current_pressed:
                    self.disable_note(note, tick)
                else:
                    self.enable_note(note, velocity, tick)
            elif byte & 0xF0 == 0x80:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if note in self.current_pressed:
                    self.disable_note(note, tick)

    def get_pressed(self):
        '''Get Set of pressed keys'''
        if self.changed:
            self.tosend = self.current_pressed.copy()
            self.changed = False
        return self.tosend
