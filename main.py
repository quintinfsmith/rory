#!/usr/bin/env python3
# coding=utf-8
'''main file of Misophonia'''
import sys
from Interface import Interface

if len(sys.argv) < 2:
    print("Specify Midi To Play")
    sys.exit()
interface = Interface()
midilike = interface.load_midi(sys.argv[1])
interface.show_player()
interface.play_along(midilike)
interface.input_loop()
