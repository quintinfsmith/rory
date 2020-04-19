'''Read Input from Midi Device'''
import os
import time
import mido

class MIDIController(object):
    '''Read Input from Midi Device'''
    def __init__(self, midipath="/dev/midi1"):
        self.midipath = midipath
        self.connected = os.path.exists(midipath)
        if not self.connected:
            self.pipe = None
        else:
            self.pipe = open(midipath, 'rb')

        self.flag_close = False

    def close(self):
        if self.connected:
            self.pipe.close()


    def read(self):
        output = None
        while not output and not self.flag_close:
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

