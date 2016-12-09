from MIDIEvent import SequenceNumberEvent, TextEvent, CopyrightNoticeEvent, TrackNameEvent, InstrumentNameEvent, LyricEvent, MarkerEvent, CuePointEvent, ChannelPrefixEvent, EndOfTrackEvent, SetTempoEvent, SMTPEOffsetEvent, TimeSignatureEvent, KeySignatureEvent, SequencerSpecificEvent, NoteOffEvent, NoteOnEvent, PolyphonicKeyPressureEvent, ControlChangeEvent, ProgramChangeEvent, ChannelPressureEvent, PitchWheelChangeEvent, SystemExclusiveEvent, SongPositionPointerEvent, SongSelectEvent, TuneRequestEvent, EndOfExclusiveEvent, TimingClockEvent, StartEvent, ContinueEvent, StopEvent, ActiveSensingEvent, ResetEvent
from Interpreter import SongInterpreter
from MIDILike import MIDILike, MIDILikeTrack
from localfuncs import pop_n, from_twos_comp, to_twos_comp, get_variable_length

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
            0x05: InstrumentNameEvent,
            0x58: TimeSignatureEvent,
            0x59: KeySignatureEvent
        }
        self.lastgoodbyte = None

    def process_mtrk_event(self, firstbyte, queue, current_deltatime, track):
        # Channel Voice Message
        if int(firstbyte >> 4) in (8, 9, 10, 11, 14):
            channel = firstbyte & 0x0F
            b = pop_n(queue)
            c = pop_n(queue)
            if int(firstbyte >> 4) == 9 and c == 0:
                tmpbyte = firstbyte & 0xEF
            else:
                tmpbyte = firstbyte
            track.add_event(
                current_deltatime,
                self.cve[int(tmpbyte >> 4)](channel, b, c))

        elif int(firstbyte >> 4) in (12, 13):
            channel = firstbyte & 0x0F
            b = pop_n(queue)
            track.add_event(
                current_deltatime,
                self.cve[int(firstbyte >> 4)](channel, b))

        # System Common Message
        elif firstbyte == 0xF0:
            dump = []
            while True:
                x = pop_n(queue)
                if x == 0xF7:
                    break
                dump.append(x)
            track.add_event(current_deltatime, SystemExclusiveEvent(firstbyte, dump))

        elif firstbyte == 0xF2: # Song Position pointer
            nb = pop_n(queue)
            nc = pop_n(queue)
            track.add_event(
                current_deltatime,
                SongPositionPointerEvent((nc & 0x7) + ((nb & 0x7) << 7)))

        elif firstbyte == 0xF3:
            b = pop_n(queue)
            track.add_event(current_deltatime, SongSelectEvent(b))

        elif firstbyte == 0xF6:
            track.add_event(current_deltatime, self.se[firstbyte]())

        elif firstbyte == 0xF7:
            vlen = get_variable_length(queue)
            data = pop_n(queue, vlen)
            track.add_event(current_deltatime, SystemExclusiveEvent(0xF0, data))

        elif firstbyte in (0xF1, 0xF4, 0xF5): # Undefined
            return 0 # TODO: isn't this handled by the else case?
                     # SORTA: The "else" bytes would indicate a failure in the midi file itself. Someone could potentially use these bytes for their own purposes
                     #   I know it's not a funcitonal difference, but should the occasion arise, i'll have these here for reference

        # Meta-Event
        elif firstbyte == 0xFF:
            meta_type = pop_n(queue)
            v_length = get_variable_length(queue)
            event_data_bytes = queue[0:v_length]
            pop_n(queue, v_length)
            # Deal with Meta Events Later
            if meta_type in self.me.keys():
                track.add_event(current_deltatime, self.me[meta_type](event_data_bytes))

        # System Real-Time Message
        elif firstbyte >= 0xF8:
            track.add_event(current_deltatime, SystemRealTimeEvent())

        elif firstbyte < 0x80:
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
        mlo = MIDILike()
        mlo.set_path(midifile)
        chunkcount = {}
        self.lastgoodbyte = 0x90
        while queue:
            chunk_type = str(queue[0:4], 'utf-8')
            queue = queue[4:]
            if not chunk_type in chunkcount.keys():
                chunkcount[chunk_type] = 0
            chunkcount[chunk_type] += 1
            print("Chunk Type", chunk_type)
            track = MIDILikeTrack()
            current_deltatime = 0
            if chunk_type == 'MThd':
                pop_n(queue, 4) # pop size
                midi_format = pop_n(queue, 2)
                pop_n(queue, 2) # pop num_tracks
                divword = pop_n(queue, 2)
                if divword & 0x8000:
                    neg = int((divword & 0x7F00) >> 8)
                    SMPTE = self.from_twos_comp(neg, 7)
                    tpf = divword & 0x00FF
                    print("SMPTE", SMPTE, "TPF:", tpf)
                else:
                    tpqn = divword & 0x7FFF
                    print("ticks per quarter note:", tpqn)
                mlo.set_tpqn(tpqn)
                mlo.set_format(midi_format)
            elif chunk_type == 'MTrk':
                length = pop_n(queue, 4)
                print(length)
                subqueue = queue[:length]
                queue = queue[length:]
                while subqueue:
                    current_deltatime += get_variable_length(subqueue)
                    n = pop_n(subqueue)
                    gb = self.process_mtrk_event(n, subqueue, current_deltatime, track)
                    if (gb & 0xf0) >> 4 in self.cve.keys():
                        self.lastgoodbyte = gb
                mlo.add_track(track)
            else:
                break
        return mlo

