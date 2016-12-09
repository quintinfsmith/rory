#!/usr/bin/env python3
# coding=utf-8
'''main file of Misophonia'''
import sys
from Interface import Interface

if len(sys.argv) < 2:
    print("Specify Midi To Play")
    sys.exit()
interface = Interface()
interface.show_player()
midilike = interface.play_along(sys.argv[1])
interface.input_loop()
