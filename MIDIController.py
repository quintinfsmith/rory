'''Read Input from Midi Device'''
import os
import time
import mido

class MIDIController(object):
    '''Read Input from Midi Device'''
    def __init__(self, midipath="/dev/midi1"):
        self.connected = os.path.exists(midipath)
        if not self.connected:
            self.pipe = open('/dev/null', 'rb')
        else:
            self.pipe = open(midipath, 'rb')

    def close(self):
        self.pipe.close()

    def read(self):
        output = None
        while not output:
            byte = self.pipe.read(1)[0]
            if byte & 0xF0 == 0x90:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                if velocity == 0:
                    output = mido.Message('note_off', note=note, velocity=0)
                else:
                    output = mido.Message('note_on', note=note, velocity=velocity)
            elif byte & 0xF0 == 0x80:
                note = self.pipe.read(1)[0]
                velocity = self.pipe.read(1)[0]
                output = mido.Message('note_off', note=note, velocity=velocity)
        return output

