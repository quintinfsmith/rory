from Interpreter import *
from MIDILike import *
from MIDIEvent import *

class MIDIInterpreter(SongInterpreter):
    """Interpret MIDIs"""
    def __init__(self):
        SongInterpreter.__init__(self)

    def from_twos_comp(self, n, bits=8):
        """Convert two's compliment representation of n"""
        f = 0
        for i in range(bits):
            f <<= 2
            f += 1
        return (n - 1).__xor__(f)

    def to_twos_comp(self, n, bits=8):
        """Get two's compliment representation of n"""
        f = 0
        for i in range(bits):
            f <<= 2
            f += 1
        return n.__xor__(f)

    def pop_n(self, queue, nbytes=1):
        """Get first N bytes from byte list"""
        out = 0
        for i in range(nbytes):
            out <<= 8
            out += int(queue.pop(0))
        return out

    def get_variable_length(self, queue):
        """Calculate variable length integer from byte list"""
        n = 0
        while True:
            n <<= 7
            c = int(queue.pop(0))
            n += c & 0x7F
            if not c & 0x80:
                break
        return n

    def __call__(self, midifile):
        """Convert raw bytes to a MIDILike object"""
        queue = []
        tpqn = 120
        with open(midifile, 'rb') as fp:
            queue = bytearray(fp.read())
            ml = fp.tell()

        mlo = MIDILike()
        while queue:
            chunk_type = str(queue[0:4], 'ascii')
            queue = queue[4:]
            print("Chunk Type", chunk_type)
            track = MIDILikeTrack()
            current_deltatime = 0
            if chunk_type == 'MThd':
                size = self.pop_n(queue, 4)
                midi_format = self.pop_n(queue, 2)
                num_tracks = self.pop_n(queue, 2)
                divword = self.pop_n(queue, 2)
                if divword & 0x8000:
                    neg = int((divword & 0x7F00) >> 8)
                    SMPTE = self.from_twos_comp(neg, 7)
                    tpf = divword & 0x00FF
                    print ("SMPTE", SMPTE, "TPF:", tpf)
                else:
                    tpqn = divword & 0x7FFF
                    print ("ticks per quarter note:", tpqn)
                mlo.set_tpqn(tpqn)
                mlo.set_format(midi_format)
            elif chunk_type == 'MTrk':
                length = self.pop_n(queue, 4)
                subqueue = queue[0:length]
                queue = queue[length:]
                cve = {
                    0x8: NoteOffEvent,
                    0x9: NoteOnEvent,
                    0xA: PolyphonicKeyPressureEvent,
                    0xB: ControlChangeEvent,
                    0xC: ChannelPressureEvent,
                    0xD: PitchWheelChangeEvent,
                }
                se = {
                    0xF0: SystemExclusiveEvent,
                    0xF2: SongPositionPointerEvent,
                    0xF3: SongSelectEvent,
                    0xF6: TuneRequestEvent,
                    0xF7: EndOfExclusiveEvent,
                    0xF8: TimingClockEvent,
                    0xFA: StartEvent,
                    0xFB: ContinueEvent,
                    0xFC: StopEvent,
                    0xFE: ActiveSensingEvent,
                    0xFF: ResetEvent
                }

                while subqueue:
                    current_deltatime += self.get_variable_length(subqueue)
                    n = self.pop_n(subqueue)
                    channel = n & 0x0F
                    # Channel Voice Message
                    if int(n >> 4) in (8, 9, 10, 11, 13, 14):
                        b = self.pop_n(subqueue)
                        c = self.pop_n(subqueue)
                        if int (n >> 4) == 9 and c == 0:
                            n &= 0xEF
                        midi_event = cve[int(n >> 4)](channel, b, c)
                        track.add_event(current_deltatime, midi_event)
                    elif int(n >> 4) == 12:
                        b = self.pop_n(subqueue)
                        midi_event = cve[int(n >> 4)](channel, b)
                        track.add_event(current_deltatime, midi_event)
                    # System Common Message
                    elif n == 0xF0:
                        dump = []
                        while True:
                            x = self.pop_n(subqueue)
                            if x == 0xF7:
                                break
                            else:
                                dump.append(x)
                        midi_event = SystemExclusiveEvent(n, dump)
                        track.add_event(current_deltatime, midi_event)
                    elif n == 0xF2: # Song Position pointer
                        nb = self.pop_n(subqueue)
                        nc = self.pop_n(subqueue)
                        midi_event = SongPositionPointerEvent((nc & 0x7) + ((nb & 0x7) << 7))
                        track.add_event(current_deltatime, midi_event)

                    elif n == 0xF3:
                        b = self.pop_n(subqueue)
                        track.add_event(current_deltatime, SongSelectEvent(b))
                    elif n in (0xF6, 0xF7):
                        track.add_event(current_deltatime, se[n]())
                    elif n in (0xF1, 0xF4, 0xF5): # Undefined
                        continue

                    # Meta-Event
                    elif n == 0xFF:
                        meta_type = self.pop_n(subqueue)
                        v_length = self.get_variable_length(subqueue)
                        event_data_bytes = subqueue[0:v_length]
                        subqueue = subqueue[v_length:]
                        event_data_bytes.insert(0, meta_type)
                        event_data_bytes.insert(0, n)
                        # Deal with Meta Events Later
                        #midi_event = MetaEvent(event_data_butes)
                        #track.add_event(current_deltatime, midi_event)
                    # System Real-Time Message
                    elif n >= 0xF8:
                        midi_event = SystemRealTimeEvent(n)
                        track.add_event(current_deltatime, midi_event)
            else:
                break
            mlo.add_track(track)
        return mlo

