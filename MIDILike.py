class MIDILike(object):
    """Usable object. Converted from midi files.
        Events are the same midi files from simplicities sake.
    """
    def __init__(self):
        self.tpqn = None
        self.midi_format = None
        self.tracks = []

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
            track_reps.append(repr(track))
        track_reps.remove("")

        with open(path, "w") as fp:
            fp.write("MThd")
            fp.write("\x00\x00\x00\x06\x00")
            fp.write(chr(self.midi_format))
            fp.write("\x00")
            fp.write(chr(len(self.tracks)))
            fp.write(chr(int(tpqn_bytes / 256)))
            fp.write(chr(int(tpqn_bytes % 256)))
            fp.write("".join(track_reps))

class MIDILikeTrack(object):
    """Track in MIDILike Object."""
    def __init__(self):
        self.events = {}

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

    @staticmethod
    def _to_variable_length(n):
        chrlist = []
        while n:
            if n > 0:
                c = chr(0xFF & n)
            else:
                c = chr(0x7F & n)
            n >>= 7
            chrlist.insert(0, c)
        return "".join(chrlist)

    def __repr__(self):
        e_reps = []
        for tick, eventlist in self.events.items():
            tick_as_str = self._to_variable_length(tick)
            for event in eventlist:
                e_reps.append(tick_as_str)
                e_reps.append(repr(event))

        if e_reps:
            e_string = "".join(e_reps)
            return "MTrk%s%s" % (self._to_variable_length(len(e_string)), e_string)

        return ""

