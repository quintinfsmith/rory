def main():
    import sys
    import time
    from rory.interface import Top, TerminalTooNarrow

    if len(sys.argv) < 2:
        print("Specify Midi To Play")
        sys.exit()

    try:
        interface = Top()
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
