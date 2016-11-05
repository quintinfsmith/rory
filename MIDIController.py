'''Read Input from Midi Device'''
import os
class MIDIController(object):
    '''Read Input from Midi Device'''
    def __init__(self):
        self.connected = os.path.exists('/dev/midi1')
        if not self.connected:
            self.pipe = open('/dev/zero', 'rb')
        else:
            self.pipe = open('/dev/midi1', 'rb')
        self.current_pressed = set([])
        self.listening = False
        self.changed = True
        self.tosend = set([])

    def listen(self):
        '''Start listening for MIDI Inputs'''
        import threading
        thread = threading.Thread(target=self._listen)
        thread.daemon = True
        thread.start()

    def enable_note(self, note):
        '''Add note to set of pressed Keys'''
        self.current_pressed.add(note)
        self.changed = True

    def disable_note(self, note):
        '''remove note from set of pressed Keys'''
        self.current_pressed.remove(note)
        self.changed = True

    def force_empty(self):
        '''Clear list of pressed Keys'''
        self.current_pressed = set()
        self.changed = True

    def _listen(self):
        self.listening = True
        while self.listening:
            byte = self.pipe.read(1)[0]
            if byte & 0xF0 == 0x90:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if velocity == 0 and note in self.current_pressed:
                    self.disable_note(note)
                else:
                    self.enable_note(note)
            elif byte & 0xF0 == 0x80:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if note in self.current_pressed:
                    self.disable_note(note)

    def get_pressed(self):
        '''Get Set of pressed keys'''
        if self.changed:
            self.tosend = self.current_pressed.copy()
            self.changed = False
        return self.tosend
