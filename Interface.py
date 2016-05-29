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
        self.args = None

    def set(self, path, action, args=None):
        if path:
            n = path[0]
            path = path[1:]
            if not n in self.children.keys():
                self.children[n] = InputNode()
            self.children[n].set(path, action, args)
        else:
            self.action = action
            self.args = args

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
        self.number_register = 0
        self.cmdNode = InputNode()
        self.cmdNode.set('q', self.quit)
        self.cmdNode.set('l', self.player.next_state)
        self.cmdNode.set('o', self.player.prev_state)
        self.cmdNode.set('0', self.set_register, 0)
        self.cmdNode.set('1', self.set_register, 1)
        self.cmdNode.set('2', self.set_register, 2)
        self.cmdNode.set('3', self.set_register, 3)
        self.cmdNode.set('4', self.set_register, 4)
        self.cmdNode.set('5', self.set_register, 5)
        self.cmdNode.set('6', self.set_register, 6)
        self.cmdNode.set('7', self.set_register, 7)
        self.cmdNode.set('8', self.set_register, 8)
        self.cmdNode.set('9', self.set_register, 9)
        self.cmdNode.set(chr(27), self.clear_register)
        self.cmdNode.set('t', self.toggle_track)
        self.listening = False
        self.midi_interpreter = MIDIInterpreter()
        if 'songs' in cache:
            self.songsettings = cache['songs']
        else:
            self.songsettings = {}

    def toggle_track(self):
        self.player.toggle_trackn(self.number_register)
        self.clear_register()

    def set_register(self, n):
        self.number_register *= 10
        self.number_register += n

    def clear_register(self):
        self.number_register = 0

    def load_midi(self, midi_path):
        midilike = self.midi_interpreter(midi_path)
        return midilike

    def quit(self):
        self.listening = False
        self.player.quit()

    def play_along(self, midilike, hidden=[]):
        thread = threading.Thread(target=self.player.play_along, args=[midilike, MIDIController(), hidden])
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
                    if not node.args is None:
                        node.action(node.args)
                    else:
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
    ignore = []
    for i in sys.argv[2:]:
        ignore.append(int(i))
    interface.play_along(midilike, ignore)
    interface.input_loop()
    sys.stdout.write('\033[0;0H')
    sys.stdout.write('\033[0m%s' % ((w * h) * ' '))

