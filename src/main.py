#!/usr/bin/env python3
# coding=utf-8
'''main file of Misophonia'''
import sys
import time
from Interface import Top

if len(sys.argv) < 2:
    print("Specify Midi To Play")
    sys.exit()

interface = Top()
interface.play_along(sys.argv[1])
interface.play()

while interface.running:
    time.sleep(.4)

interface.kill()
