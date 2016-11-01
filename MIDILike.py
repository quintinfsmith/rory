from localfuncs import to_variable_length, to_bytes
import sys

class MIDILike(object):
    """Usable object. Converted from midi files.
        Events are the same midi files from simplicities sake.
    """
    def __init__(self):
        self.tpqn = None
        self.midi_format = None
        self.tracks = []

    def get_note_range(self):
        cmin = 127
        cmax = 0
        for track in self.tracks:
            tmin, tmax = track.get_note_range()
            cmin = min(cmin, tmin)
            cmax = max(cmax, tmax)
        return (cmin, cmax)

    def __len__(self):
        """The length of the longest track"""
        m = 0
        for track in self.tracks:
            m = max(len(track), m)
        return m

    def set_format(self, f):
        self.midi_format = f

    def set_tpqn(self, tpqn):
        self.tpqn = tpqn

    def add_track(self, track):
        self.tracks.append(track)

    def save_as(self, path):
        tpqn_bytes = 0xFFFF & self.tpqn

        track_reps = []
        for track in self.tracks:
            track_reps.append(bytes(track))

        while b"" in track_reps:
            track_reps.remove(b"")

        with open(path, "wb") as fp:
            fp.write(b"MThd")
            fp.write(b"\x00\x00\x00\x06\x00")
            fp.write(bytes([self.midi_format]))
            fp.write(b"\x00")
            fp.write(bytes([len(track_reps)]))
            fp.write(bytes([int(tpqn_bytes / 256)]))
            fp.write(bytes([int(tpqn_bytes % 256)]))
            for track in track_reps:
                fp.write(track)

class MIDILikeTrack(object):
    """Track in MIDILike Object."""
    def __init__(self):
        self.events = {}

    def get_note_range(self):
        cmin = 127
        cmax = 0
        for events in self.events.values():
            for event in events:
                if event.eid == event.NOTE_ON and event.velocity:
                    cmin = min(event.note, cmin)
                    cmax = max(event.note, cmax)
        return (cmin, cmax)

    def get_events(self, tick):
        if tick in self.events.keys():
            return self.events[tick]
        return []

    def add_event(self, dt, event):
        if not dt in self.events.keys():
            self.events[dt] = []
        self.events[dt].append(event)

    def __len__(self):
        """The total number of ticks in this track"""
        k = list(self.events.keys())
        if k:
            k.sort()
            return k.pop()
        return 0

    def __bytes__(self):
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
                for c in list(repr(event)):
                    e_reps += bytes([ord(c)])
            last_tick = tick
        if e_reps:
            out = b"MTrk"
            out += to_bytes(len(e_reps), 4)
            out += bytes(e_reps)
            return out
        return b""

