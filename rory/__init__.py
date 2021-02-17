#!/usr/bin/env python3
# coding=utf-8
"""
Usage:
    rory path/to/midi.midi
"""

__version__ = "0.2.14"
__license__ = "GPL-2.0"
__author__ = "Quintin Smith"
__email__ = "smith.quintin@protonmail.com"
__url__ = "https://github.com/quintinfsmith/rory"

def main():
    import sys
    import time
    from rory.interface import RoryStage, TerminalTooNarrow

    if len(sys.argv) < 2:
        print("Specify Midi To Play")
        sys.exit()

    try:
        interface = RoryStage()
    except TerminalTooNarrow:
        print("Terminal needs to be at least 90 characters wide")
        sys.exit()

    interface.play()
    interface.play_along(sys.argv[1])

    while interface.playing:
        time.sleep(.4)

    interface.kill()

if __name__ == "__main__":
    main()
