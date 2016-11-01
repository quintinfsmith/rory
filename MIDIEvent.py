from localfuncs import to_variable_length

class MIDIEvent(object):
    METAEVENT = 0
    SYSTEMREALTIMEEVENT = 1
    SYSTEMCOMMONEVENT = 2
    CHANNELVOICEEVENT = 3

    # Channel Voice Messages (first nibbles)
    NOTE_OFF = 0x80
    NOTE_ON = 0x90
    POLYPHONIC_KEY_PRESSURE = 0xA0
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    CHANNEL_PRESSURE = 0xD0
    PITCHWHEEL_CHANGE = 0xE0
    CHANNEL_VOICE_MESSAGES = [NOTE_OFF, NOTE_ON, POLYPHONIC_KEY_PRESSURE, CONTROL_CHANGE, PROGRAM_CHANGE, CHANNEL_PRESSURE, PITCHWHEEL_CHANGE, PITCHWHEEL_CHANGE]

    # System Common Messages ( first byte )
    SYSTEM_EXCLUSIVE = 0xF0
    SONG_POSITION_POINTER = 0xF2
    SONG_SELECT = 0xF3
    TUNE_REQUEST = 0xF6
    END_OF_EXCLUSIVE =  0xF7
    SYSTEM_COMMON_MESSAGES = [SYSTEM_EXCLUSIVE, SONG_POSITION_POINTER, SONG_SELECT, TUNE_REQUEST, END_OF_EXCLUSIVE]
    
    # System Real-Time Messages
    TIMING_CLOCK = 0xF8
    START = 0xFB
    CONTINUE = 0xFB
    STOP = 0xFC
    ACTIVE_SENSING = 0xFE
    RESET = 0xFF
    SYSTEM_REALTIME_MESSAGES = [TIMING_CLOCK, START, CONTINUE, STOP, ACTIVE_SENSING, RESET]
    
    #Meta-Event Messages
    #SEQUENCE_NUMBER = 0x01
    #TEXT = 0x02
    #COPYRIGHT_NOTICE = 0x03
    #TRACK_NAME = 0x04
    #INSTRUMENT_NAME
    #LYRIC
    #MARKER
    #CUE_POINT
    #CHANNEL_PREFIX
    #END_OF_TRACK
    
    def __init__(self, eventtype):
        self.event_type = eventtype
        self.eid = 0

    def get_type(self):
        return self.event_type

    def __repr__(self):
        return ""

    def __str__(self):
        return ''

class MetaEvent(MIDIEvent):
    def __init__(self):
        MIDIEvent.__init__(self, self.METAEVENT)

class SequenceNumberEvent(MetaEvent):
    def __init__(self, seq):
        MetaEvent.__init__(self)
        self.sequence = seq
        self.eid = 0x01
    #def __repr__(self):
    #    return chr(0xFF) + chr(self.eid) + to_variable_length(len(self.sequence)) + self.sequence

class TextEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text
        self.eid = 0x02
        print(self.text)

    #def __repr__(self):
    #    return chr(0xFF) + chr(self.eid) + to_variable_length(len(self.text)) + self.text

class CopyrightNoticeEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text
        self.eid = 0x03
        print(self.text)

    #def __repr__(self):
    #    return chr(0xFF) + chr(self.eid) + to_variable_length(len(self.text)) + self.text.decode("ascii")

class TrackNameEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text
        self.eid = 0x04
        print(self.text)

class InstrumentNameEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text
        self.eid = 0x05
        print(self.text)

class LyricEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text

class MarkerEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text
        print(self.text)

class CuePointEvent(MetaEvent):
    def __init__(self, text):
        MetaEvent.__init__(self)
        self.text = text
        print(self.text)

class ChannelPrefixEvent(MetaEvent):
    def __init__(self, prefix):
        MetaEvent.__init__(self)
        self.prefix = prefix

class EndOfTrackEvent(MetaEvent):
    def __init__(self):
        MetaEvent.__init__(self)
        self.eid = 0x2F

class SetTempoEvent(MetaEvent):
    def __init__(self, tempo):
        MetaEvent.__init__(self)
        self.tempo = tempo

class SMTPEOffsetEvent(MetaEvent):
    def __init__(self, hour, minute, second, fr, ff):
        MetaEvent.__init__(self)
        self.hour = hour
        self.minute = minute
        self.second = second
        self.fr = fr
        self.ff = ff

class TimeSignatureEvent(MetaEvent):
    def __init__(self, db):
        numerator = db[0]
        denominator = db[1]
        clocks_per_metronome = db[2]
        thirtyseconds_per_quarter = db[3]
        MetaEvent.__init__(self)
        self.numerator = numerator
        self.denominator = 2 ** denominator
        self.clocks_per_metronome = clocks_per_metronome
        self.thirtyseconds_per_quarter = thirtyseconds_per_quarter

class KeySignatureEvent(MetaEvent):
    def __init__(self, db):
        sharp_count = db[0]
        mi = db[1]
        MetaEvent.__init__(self)
        self.sharp_count = sharp_count
        self.mi = mi

class SequencerSpecificEvent(MetaEvent):
    def __init__(self, data):
        MetaEvent.__init__(self)
        self.data = data

class ChannelVoiceEvent(MIDIEvent):
    # Instruments
    ACOUSTIC_GRAND_PIANO = 0x00
    BRIGHT_GRAND_PIANO = 0x01
    ELECTRIC_GRAND_PIANO = 0x02
    HONKYTONK_PIANO = 0x03
    RHODES_PIANO = 0x04
    CHORUSED_PIANO = 0x05
    HARPSICHORD = 0x06
    CLAVINET = 0x07
    CELESTA = 0x09
    GLOCKENSPIEL = 0x09
    MUSIC_BOX = 0x0A
    VIBRAPHONE = 0x0B
    MARIMBA = 0x0C
    XYLOPHONE = 0x0D
    TUBULAR_BELLS = 0x0E
    DULCIMER = 0x0F
    DRAWBAR_ORGAN = 0x10
    PERCUSSIVE_ORGAN = 0x11
    ROCK_ORGAN = 0x12
    CHURCH_ORGAN = 0x13
    ACCORDION = 0x14
    HARMONICA = 0x15
    TANGO_ACCORDION = 0x16
    NYLON_GUITAR = 0x17
    STEEL_GUITAR = 0x18
    JAZZ_GUITAR = 0x19
    CLEAN_GUITAR = 0x1A
    MUTED_GUITAR = 0x1B
    OVERDRIVEN_GUITAR = 0x1C
    DISTORTION_GUITAR = 0x1D
    GUITAR_HARMONICS = 0x1E
    ACOUSTIC_BASS = 0x1F
    FINGER_BASS = 0x20
    #....

    def __init__(self, channel):
        MIDIEvent.__init__(self, self.CHANNELVOICEEVENT)
        self.channel = channel

class NoteOffEvent(ChannelVoiceEvent):
    def __init__(self, channel, note, velocity):
        ChannelVoiceEvent.__init__(self, channel)
        self.note = note
        self.velocity = velocity
        self.eid = self.NOTE_OFF

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(self.note) + chr(self.velocity)
        
class NoteOnEvent(ChannelVoiceEvent):
    def __init__(self, channel, note, velocity):
        ChannelVoiceEvent.__init__(self, channel)
        self.note = note
        self.velocity = velocity
        self.eid = self.NOTE_ON

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(self.note) + chr(self.velocity)

class PolyphonicKeyPressureEvent(ChannelVoiceEvent):
    def __init__(self, channel, note, pressure):
        ChannelVoiceEvent.__init__(self, channel)
        self.note = note
        self.pressure = pressure
        self.eid = self.POLYPHONIC_KEY_PRESSURE

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(self.note) + chr(self.pressure)

class ControlChangeEvent(ChannelVoiceEvent):
    def __init__(self, channel, controller, new_value):
        ChannelVoiceEvent.__init__(self, channel)
        self.controller = controller
        self.new_value = new_value
        self.eid = self.CONTROL_CHANGE

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(self.controller) + chr(self.new_value)

class ProgramChangeEvent(ChannelVoiceEvent):
    def __init__(self, channel, program):
        ChannelVoiceEvent.__init__(self, channel)
        self.program = program
        self.eid = self.PROGRAM_CHANGE

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(self.program)

class ChannelPressureEvent(ChannelVoiceEvent):
    def __init__(self, channel, pressure):
        ChannelVoiceEvent.__init__(self, channel)
        self.pressure = pressure
        self.eid = self.CHANNEL_PRESSURE

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(self.pressure)

class PitchWheelChangeEvent(ChannelVoiceEvent):
    def __init__(self, channel, least, most):
        ChannelVoiceEvent.__init__(self, channel)
        self.least = least
        self.most = most
        self.eid = self.PITCHWHEEL_CHANGE

    def __repr__(self):
        return chr(self.eid | self.channel) + chr(least) + chr(most)

class SystemCommonEvent(MIDIEvent):
    def __init__(self):
        MIDIEvent.__init__(self, self.SYSTEMCOMMONEVENT)

class SystemExclusiveEvent(SystemCommonEvent):
    def __init__(self, manufacturer_id, dump):
        SystemCommonEvent.__init__(self)
        self.manufacturer_id = manufacturer_id
        self.dump = dump
    
class SongPositionPointerEvent(SystemCommonEvent):
    def __init__(self, position):
        SystemCommonEvent.__init__(self)
        self.position = position

class SongSelectEvent(SystemCommonEvent):
    def __init__(self, song):
        SystemCommonEvent.__init__(self)
        self.song = song

class TuneRequestEvent(SystemCommonEvent):
    def __init__(self):
        SystemCommonEvent.__init__(self)

class EndOfExclusiveEvent(SystemCommonEvent):
    def __init__(self):
        SystemCommonEvent.__init__(self)
        
class SystemRealTimeEvent(MIDIEvent):
    def __init__(self):
        MIDIEvent.__init__(self, self.SYSTEMREALTIMEEVENT)

class TimingClockEvent(SystemRealTimeEvent):
    def __init__(self):
        SystemRealTimeEvent.__init__(self)

class StartEvent(SystemRealTimeEvent):
    def __init__(self):
        SystemRealTimeEvent.__init__(self)

class ContinueEvent(SystemRealTimeEvent):
    def __init__(self):
        SystemRealTimeEvent.__init__(self)

class StopEvent(SystemRealTimeEvent):
    def __init__(self):
        SystemRealTimeEvent.__init__(self)

class ActiveSensingEvent(SystemRealTimeEvent):
    def __init__(self):
        SystemRealTimeEvent.__init__(self)

class ResetEvent(SystemRealTimeEvent):
    def __init__(self):
        SystemRealTimeEvent.__init__(self)

