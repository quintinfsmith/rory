'''Read Input from Midi Device'''
import os
import time
import mido

class PipeClosed(Exception):
    pass

class MIDIController:
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
        self.flag_close = True


    def check_byte(self):
        output = None
        while not output:
            output = os.read(self.pipe.fileno(), 1)
            if len(output) > 0:
                output = output[0]
            elif self.flag_close:
                if self.connected:
                    self.pipe.close()
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
                    output = mido.Message('note_off', note=note, velocity=0)
                else:
                    output = mido.Message('note_on', note=note, velocity=velocity)
            elif byte & 0xF0 == 0x80:
                note = self.check_byte()
                velocity = self.check_byte()
                output = mido.Message('note_off', note=note, velocity=velocity)
        except PipeClosed:
            output = mido.Message('stop')

        return output
