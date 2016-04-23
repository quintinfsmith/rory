import os
class MIDIController(object):
    def __init__(self):
        self.connected = os.path.exists('/dev/midi1')
        if not self.connected:
            self.pipe = open('/dev/zero', 'rb')
        else:
            self.pipe = open('/dev/midi1', 'rb')
        self.current_pressed = set([])
        self.listening = False

    def listen(self):
        import threading
        thread = threading.Thread(target=self._listen)
        thread.daemon = True
        thread.start()

    def _listen(self):
        self.listening = True
        while self.listening:
            b = self.pipe.read(1)[0]
            if b & 0xF0 == 0x90:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if velocity == 0 and note in self.current_pressed:
                    self.current_pressed.remove(note)
                else:
                    self.current_pressed.add(note)
            elif b & 0xF0 == 0x80:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if note in self.current_pressed:
                    self.current_pressed.remove(note)

    def get_pressed(self):
        return self.current_pressed.copy()

