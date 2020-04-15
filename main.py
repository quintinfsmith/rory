#!/usr/bin/env python3
# coding=utf-8
'''main file of Misophonia'''
import sys
from Interface import Top

if len(sys.argv) < 2:
    print("Specify Midi To Play")
    sys.exit()

interface = Top()
interface.play_along(sys.argv[1])
try:
    interface.play()
except KeyboardInterrupt:
    pass
interface.kill()
