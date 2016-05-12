import json
import threading
import os
from MIDILike import *
from Player import Player
from MidiInterpreter import MIDIInterpreter
from MIDIController import *
from getCh import getCh

class InputNode(object):
    def __init__(self):
        self.children = {}
        self.action = None
        self.args = {}

    def set(self, path, action):
        if path:
            n = path[0]
            path = path[1:]
            if not n in self.children.keys():
                self.children[n] = InputNode()
            self.children[n].set(path, action)
        else:
            self.action = action

    def get(self, path):
        if path:
            n = path[0]
            path = path[1:]
            if n in self.children.keys():
                return self.children[n].get(path)
            else:
                return None
        else:
            return self


class Interface(object):
    def __init__(self, cache_path='.cache.json'):
        if os.path.isfile(cache_path):
            with open(cache_path, 'r') as fp:
                cache = json.loads(fp.read())
        else:
            cache = {}
        self.active_threads = []
        self.player = Player()
        self.cmdNode = InputNode()
        self.cmdNode.set('q', self.quit)
        self.cmdNode.set('l', self.player.next_state)
        self.cmdNode.set('o', self.player.prev_state)
        self.cmdNode.set('t0', self.player.toggle_track0)
        self.cmdNode.set('t1', self.player.toggle_track1)
        self.cmdNode.set('t2', self.player.toggle_track2)
        self.cmdNode.set('t3', self.player.toggle_track3)
        self.cmdNode.set('t4', self.player.toggle_track4)
        self.cmdNode.set('t5', self.player.toggle_track5)
        self.cmdNode.set('t6', self.player.toggle_track6)
        self.cmdNode.set('t7', self.player.toggle_track7)
        self.cmdNode.set('t8', self.player.toggle_track8)
        self.cmdNode.set('t9', self.player.toggle_track9)
        self.cmdNode.set('ta', self.player.toggle_track10)
        self.cmdNode.set('tb', self.player.toggle_track11)
        self.cmdNode.set('tc', self.player.toggle_track12)
        self.cmdNode.set('td', self.player.toggle_track13)
        self.cmdNode.set('te', self.player.toggle_track14)
        self.cmdNode.set('tf', self.player.toggle_track15)
        self.listening = False
        self.midi_interpreter = MIDIInterpreter()
        if 'songs' in cache:
            self.songsettings = cache['songs']
        else:
            self.songsettings = {}

    def load_midi(self, midi_path):
        midilike = self.midi_interpreter(midi_path)
        return midilike

    def quit(self):
        self.listening = False
        self.player.quit()

    def play_along(self, midilike):
        thread = threading.Thread(target=self.player.play_along, args=[midilike, MIDIController()])
        thread.start()
        self.active_threads.append(thread)

    def input_loop(self):
        self.listening = True
        current_path = []
        while self.listening:
            current_path.append(getCh())
            node = self.cmdNode.get(current_path)
            if node:
                if node.action:
                    node.action()
                    current_path = []
            else:
                current_path = []
import sys
import console
if __name__ == '__main__':
    interface = Interface()
    midilike = interface.load_midi(sys.argv[1])

    w,h = console.getTerminalSize()
    sys.stdout.write('\033[0;0H')
    sys.stdout.write('\033[46m%s' % ((w * h) * ' '))
    sys.stdout.write('\033[0;0H\033[0m')
    for i in range(7):
        sys.stdout.write('\033[3%dm%s\033[0m' % (i + 1, hex(i)[2:]))
    interface.play_along(midilike)
    interface.input_loop()
    sys.stdout.write('\033[0;0H')
    sys.stdout.write('\033[0m%s' % ((w * h) * ' '))

