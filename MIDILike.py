'''Mutable Midi Library'''
from localfuncs import to_variable_length, to_bytes

class MIDILike(object):
    """Usable object. Converted from midi files.
        Events are the same midi files from simplicities sake.
    """
    def __init__(self):
        self.tpqn = None
        self.midi_format = None
        self.tracks = []
        self.path = ""

    def set_path(self, path):
        '''Give the object a path'''
        self.path = path

    def get_note_range(self):
        '''Return min/max notes played in the entire midi'''
        cmin = 127
        cmax = 0
        for track in self.tracks:
            tmin, tmax = track.get_note_range()
            cmin = min(cmin, tmin)
            cmax = max(cmax, tmax)
        return (cmin, cmax)

    def __len__(self):
        """The length of the longest track"""
        longest_track_length = 0
        for track in self.tracks:
            longest_track_length = max(len(track), longest_track_length)
        return longest_track_length

    def set_format(self, format_byte):
        '''Set Midi Format'''
        self.midi_format = format_byte

    def set_tpqn(self, tpqn):
        '''Set Ticks Per Quarter Note'''
        self.tpqn = tpqn

    def add_track(self, track):
        '''add MidiTrack'''
        self.tracks.append(track)

    def save_as(self, path):
        '''Save to specified path'''
        tpqn_bytes = 0xFFFF & self.tpqn

        track_reps = []
        for track in self.tracks:
            track_reps.append(bytes(track))

        while b"" in track_reps:
            track_reps.remove(b"")

        with open(path, "wb") as filepipe:
            filepipe.write(b"MThd")
            filepipe.write(b"\x00\x00\x00\x06\x00")
            filepipe.write(bytes([self.midi_format]))
            filepipe.write(b"\x00")
            filepipe.write(bytes([len(track_reps)]))
            filepipe.write(bytes([tpqn_bytes // 256]))
            filepipe.write(bytes([tpqn_bytes % 256]))
            for track in track_reps:
                filepipe.write(track)

class MIDILikeTrack(object):
    """Track in MIDILike Object."""
    def __init__(self):
        self.events = {}

    def get_note_range(self):
        '''Return min/max notes played in the entire midi track'''
        cmin = 127
        cmax = 0
        for events in self.events.values():
            for event in events:
                if event.eid == event.NOTE_ON and event.velocity:
                    cmin = min(event.note, cmin)
                    cmax = max(event.note, cmax)
        return (cmin, cmax)

    def get_events(self, tick):
        '''Return list of events at specified "Tick"'''
        if tick in self.events.keys():
            return self.events[tick]
        return []

    def add_event(self, delta_tick, event):
        """Add Midi Event"""
        if not delta_tick in self.events.keys():
            self.events[delta_tick] = []
        self.events[delta_tick].append(event)

    def __len__(self):
        """The total number of ticks in this track"""
        k = list(self.events.keys())
        if k:
            k.sort()
            return k.pop()
        return 0

    def __bytes__(self):
        """Convert to Bytes (ie, for saving)"""
        e_reps = b""
        last_tick = 0
        zero_tickstr = to_variable_length(0)
        ticks = list(self.events.keys())
        ticks.sort()
        for tick in ticks:
            first = True
            tick_as_str = to_variable_length(tick - last_tick)
            for event in self.events[tick]:
                if first:
                    e_reps += tick_as_str
                else:
                    e_reps += zero_tickstr
                first = False
                for character in list(repr(event)):
                    e_reps += bytes([ord(character)])
            last_tick = tick
        if e_reps:
            out = b"MTrk"
            out += to_bytes(len(e_reps), 4)
            out += bytes(e_reps)
            return out
        return b""
