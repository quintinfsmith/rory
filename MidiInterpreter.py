from Interpreter import *
from MIDILike import *
from MIDIEvent import *

class MIDIInterpreter(SongInterpreter):
    """Interpret MIDIs"""

    def __init__(self):
        SongInterpreter.__init__(self)
        self.cve = {
            0x8: NoteOffEvent,
            0x9: NoteOnEvent,
            0xA: PolyphonicKeyPressureEvent,
            0xB: ControlChangeEvent,
            0xC: ProgramChangeEvent,
            0xD: ChannelPressureEvent,
            0xE: PitchWheelChangeEvent,
        }
        self.se = {
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
        self.me = {
            0x01: SequenceNumberEvent,
            0x02: TextEvent,
            0x03: CopyrightNoticeEvent,
            0x04: TrackNameEvent,
            0x05: InstrumentNameEvent
        }

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

    def process_mtrk_event(self, firstbyte, queue, current_deltatime, track):
        channel = firstbyte & 0x0F
        # Channel Voice Message
        if int(firstbyte >> 4) in (8, 9, 10, 11, 14):
            b = self.pop_n(queue)
            c = self.pop_n(queue)
            if int(firstbyte >> 4) == 9 and c == 0:
                firstbyte &= 0xEF
            midi_event = self.cve[int(firstbyte >> 4)](channel, b, c)
            track.add_event(current_deltatime, midi_event)
            return firstbyte
        elif int(firstbyte >> 4) in (12, 13):
            b = self.pop_n(queue)
            midi_event = self.cve[int(firstbyte >> 4)](channel, b)
            track.add_event(current_deltatime, midi_event)
            return firstbyte
        # System Common Message
        elif firstbyte == 0xF0:
            dump = []
            while True:
                x = self.pop_n(queue)
                if x == 0xF7:
                    break
                else:
                    dump.append(x)
            midi_event = SystemExclusiveEvent(firstbyte, dump)
            track.add_event(current_deltatime, midi_event)
        elif firstbyte == 0xF2: # Song Position pointer
            nb = self.pop_n(queue)
            nc = self.pop_n(queue)
            midi_event = SongPositionPointerEvent((nc & 0x7) + ((nb & 0x7) << 7))
            track.add_event(current_deltatime, midi_event)

        elif firstbyte == 0xF3:
            b = self.pop_n(queue)
            track.add_event(current_deltatime, SongSelectEvent(b))
        elif firstbyte == 0xF6:
            track.add_event(current_deltatime, self.se[firstbyte]())
        elif firstbyte == 0xF7:
            vlen = self.get_variable_length(queue)
            data = self.pop_n(queue, vlen)
            track.add_event(current_deltatime, SystemExclusiveEvent(0xF0, data))
        elif firstbyte in (0xF1, 0xF4, 0xF5): # Undefined
            return 0

        # Meta-Event
        elif firstbyte == 0xFF:
            meta_type = self.pop_n(queue)
            v_length = self.get_variable_length(queue)
            event_data_bytes = queue[0:v_length]
            self.pop_n(queue, v_length)
            # Deal with Meta Events Later
            if meta_type in self.me.keys():
                midi_event = self.me[meta_type](event_data_bytes)
                track.add_event(current_deltatime, midi_event)
        # System Real-Time Message
        elif firstbyte >= 0xF8:
            midi_event = SystemRealTimeEvent()
            track.add_event(current_deltatime, midi_event)
        elif firstbyte < 128:
           queue.insert(0, firstbyte)  
           return self.process_mtrk_event(self.lastgoodbyte, queue, current_deltatime, track)
        else:
            return 0
        return firstbyte


    def __call__(self, midifile):
        """Convert raw bytes to a MIDILike object"""
        queue = []
        tpqn = 120
        with open(midifile, 'rb') as fp:
            queue = bytearray(fp.read())
            ml = fp.tell()
        self.lastgoodbyte = 0x90
        mlo = MIDILike()
        chunkcount = {}
        while queue:
            chunk_type = str(queue[0:4], 'ascii')
            queue = queue[4:]
            if not chunk_type in chunkcount.keys():
                chunkcount[chunk_type] = 0
            chunkcount[chunk_type] += 1
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
                while subqueue:
                    vlen = self.get_variable_length(subqueue)
                    current_deltatime += vlen
                    n = self.pop_n(subqueue)
                    gb = self.process_mtrk_event(n, subqueue, current_deltatime, track)
                    if gb & 0xf0 == 0x90: 
                        self.lastgoodbyte = gb
            else:
                break
            mlo.add_track(track)
        return mlo

