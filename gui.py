from kivy.app import App
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.graphics import *
from kivy.config import Config
from kivy.uix.label import Label

from MIDIInterface import MIDIInterface
from MidiLib.MidiInterpreter import MIDIInterpreter as MI
from MidiLib.MIDIController import MIDIController

import sys
import threading
import time
import math

tick_height = 5
note_height = 15
note_width = 10
note_space = 2

note_color = [
    (1, 1, 0),
    (1, 1, 1),
    (1, 0, 1),
    (0, 1, 1),
]

class IScreen(Widget):
    IDGEN = 0x01
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen_id = IScreen.IDGEN
        self.active = False
        IScreen.IDGEN += 1

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        pass

    def background_update(self):
        pass

    def background_daemon(self):
        self.active = True
        while self.active:
            self.background_update()

    def stop(self):
        self.active = False


class SongScreen(IScreen):
    NEXT_STATE = 1
    PREV_STATE = 2
    RAISE_QUIT = 3
    JUMP_TO_TICK = 4

    def __init__(self, midi_path, **kwargs):
        super().__init__(**kwargs)

        self.current_tick = 0
        self.flags = set()
        mlo = MI.parse_midi(midi_path)

        self.pixels_per_qn = 15 * 5
        self.pixels_per_tick = self.pixels_per_qn / mlo.ppqn

        self.midi_interface = MIDIInterface(mlo, MIDIController())
        self.buffer_ticks = mlo.ppqn * 2

        self.loop_points = (0, len(self.midi_interface))

        self.register = 0
        self.visuals_changed = True

    def add_to_register(self, n):
        self.register *= 10
        self.register += n

    def set_register(self, n):
        self.register = n

    def wait_for_input(self):
        input_given = 0
        while not input_given:
            pressed = self.midi_interface.get_pressed()
            if False and self.midi_interface.states_match(self.current_tick, pressed, []):
                input_given = self.NEXT_STATE
            elif self.check_flag(self.NEXT_STATE):
                input_given = self.NEXT_STATE
            elif self.check_flag(self.PREV_STATE):
                input_given = self.PREV_STATE
            elif self.check_flag(self.JUMP_TO_TICK):
                input_given = self.JUMP_TO_TICK
            elif self.check_flag(self.RAISE_QUIT):
                input_given = self.RAISE_QUIT
        return input_given

    def jump_to_tick(self, tick):
        self.current_tick = max(0, min(tick, len(self.midi_interface) - 1))

    def move_to_next_active_tick(self):
        skipped_first = False
        while not skipped_first or self.midi_interface.is_state_empty(self.current_tick):
            skipped_first = True
            self.current_tick += 1
            if self.current_tick >= len(self.midi_interface):
                self.current_tick = 0

    def move_to_prev_active_tick(self):
        skipped_first = False
        while self.current_tick > 0 and not skipped_first or self.midi_interface.is_state_empty(self.current_tick):
            skipped_first = True
            self.current_tick -= 1

    def set_flag(self, flag):
       self.flags.add(flag)

    def check_flag(self, flag):
        try:
            self.flags.remove(flag)
            return True
        except KeyError:
            return False

    def _get_keyposition(self, note):
        notedists = [0, .5, 1, 2, 2.5, 3, 3.5, 4, 5, 5.5, 6, 6.5]
        output = notedists[note % 12] + ((note // 12) * 7)
        return output

    def note_is_sharp(self,note):
        return note % 12 in (1,4,6,9,11)

    def update(self, dt):
        if not self.visuals_changed: return
        self.canvas.clear()
        width, height = self.get_root_window().size
        ticks_in_screen = (height / self.pixels_per_tick)
        active_i = max(0, int(self.current_tick - self.buffer_ticks))
        active_f = min(len(self.midi_interface), int(self.current_tick - self.buffer_ticks + ticks_in_screen))
        w = (width / 58)
        orig_size = [int(w), 25]

        tickcount = active_f - active_i
        yoff = max(0, self.buffer_ticks - self.current_tick)

        sharps = [1,0,1,1,0,1,1]
        # Background Rendering
        with self.canvas:
            for i in range(58):
                Color(.2, .2, .2)
                linewidth = 1

                if (sharps[i % 7] == 1):
                    h = (self.buffer_ticks // 2) * self.pixels_per_tick
                    Rectangle(pos=(w * (i + .666), h), size=(w * (2 / 3), h + orig_size[1]))
                y = 0

                Line(points=(w * i, y, w * i, height), width=linewidth)

            Color(1, 0, 0, .5)
            Rectangle(pos=(0, (self.pixels_per_tick * self.buffer_ticks)), size=(width, orig_size[1]))
        # ---------------------

        for Y in range(tickcount):
            # Rendered in reverse order so the next notes to be played are rendered on top of the ones to follow
            active = self.midi_interface.event_map[(active_i + tickcount) - 1 - Y]
            y = tickcount - 1 - Y
            for note, event in active.items():
                size = orig_size
                n = (event.note - 21)
                if self.note_is_sharp(n):
                    size[0] = (w * 1.3) * 2 / 3
                else:
                    size[0] = (w * 1.3)

                xx = w * self._get_keyposition(n)

                if y + yoff <= self.buffer_ticks:
                    ratio = (y + yoff) / self.buffer_ticks
                    ratio **= 2
                    yy = self.buffer_ticks * ratio
                    yy *= self.pixels_per_tick
                else:
                    yy = ((y + yoff) - self.buffer_ticks)
                    yy += self.buffer_ticks
                    yy *= self.pixels_per_tick

                pos = (xx + ((w - size[0]) / 2), yy)

                with self.canvas:
                    is_sharp = self.note_is_sharp(event.note - 21)
                    if (y + active_i) == self.current_tick:
                        Color(*(note_color[event.channel % len(note_color)]))
                        if is_sharp:
                            Rectangle(pos=pos, size=size)
                        else:
                            Ellipse(pos=pos, size=size)
                        pos = (pos[0] + 2, pos[1] + 2)
                        size = (size[0] - 4, size[1] - 4)
                        Color(0, .8, 0)
                        if is_sharp:
                            Rectangle(pos=pos, size=size)
                        else:
                            Ellipse(pos=pos, size=size)
                    elif y + yoff <= self.buffer_ticks:
                        Color(1, 1, 1, .1)
                        Ellipse(pos=pos, size=size)
                    else:
                        Color(*(note_color[event.channel % len(note_color)]))
                        if is_sharp:
                            Rectangle(pos=pos, size=size)
                        else:
                            Ellipse(pos=pos, size=size)
                        pos = (pos[0] + 2, pos[1] + 2)
                        size = (size[0] - 4, size[1] - 4)
                        Color(0,0,0)
                        if is_sharp:
                            Rectangle(pos=pos, size=size)
                        else:
                            Ellipse(pos=pos, size=size)

        pressed = self.midi_interface.get_pressed()
        active = self.midi_interface.event_map[self.current_tick]
        with self.canvas:
            if n in pressed:
                Color(1, 1, 0, .1)
            else:
                Color(1, 1, 1, .1)
            size_natural = (w, self.buffer_ticks * self.pixels_per_tick)
            size_sharp = (w * 2 / 3, (self.buffer_ticks // 2) * self.pixels_per_tick)
            for event in active.values():
                n = (event.note - 21)
                if self.note_is_sharp(n):
                    size = size_sharp
                    yy = size[1]
                else:
                    size = size_natural
                    yy = 0

                xx = size_natural[0] * self._get_keyposition(n)
                pos = (xx + ((size_natural[0] - size[0]) / 2), yy)
                Rectangle(pos=pos, size=size)
        self.visuals_changed = False

    def background_update(self):
        control = self.wait_for_input()
        if control == self.NEXT_STATE:
            self.move_to_next_active_tick()
        elif control == self.PREV_STATE:
            self.move_to_prev_active_tick()
        elif control == self.RAISE_QUIT:
            self.stop()
        elif control == self.JUMP_TO_TICK:
            self.jump_to_tick(self.register)
            self.set_register(0)
        self.visuals_changed = True

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        k = keycode[1]
        if k == "j":
            self.set_flag(self.NEXT_STATE)
        elif k == "k":
            self.set_flag(self.PREV_STATE)
        elif k == "p":
            self.set_flag(self.JUMP_TO_TICK)
        elif k in "0123456789":
            self.add_to_register(int(k))
        elif k == "q":
            self.set_flag(self.RAISE_QUIT)

class ControlWidget(Widget):
    def __init__(self):
        super().__init__(size=(1000,500))
        self.active_screen = None
        self.screens = {}

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        active_screen = self.get_active_screen()
        if active_screen:
            active_screen._on_keyboard_down(keyboard, keycode, text, modifiers)

    def update(self, dt):
        active_screen = self.get_active_screen()
        if active_screen:
            active_screen.update(dt)

    def create_song_screen(self, path):
        song_screen = SongScreen(path, size=self.size)
        self.screens[song_screen.screen_id] = song_screen
        return song_screen

    def get_active_screen(self):
        try:
            return self.screens[self.active_screen]
        except KeyError:
            return None

    def set_active_screen(self, n):
        # Stop the currently active screen
        screen = self.get_active_screen()
        if screen:
            screen.stop()
            self.remove_widget(screen)

        self.active_screen = n
        screen = self.get_active_screen()
        # Start up the newly active screen
        if screen:
            thread = threading.Thread(target=screen.background_daemon)
            thread.start()
            self.add_widget(screen, 0, self.canvas)


class TheApp(App):
    def __init__(self):
        super().__init__()
        self.control = ControlWidget()

        # Do not touch. There seems to be a bug in Kivy when resizing Windows. This is needed to workaround
        self.y = self.control.y
        self.x = self.control.x

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self.control._on_keyboard_down)
        self._keyboard = None

    def build(self):
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self.control._on_keyboard_down)
        Clock.schedule_interval(self.control.update, 1 / 60)
        return self.control

    # Do not touch. There seems to be a bug in Kivy when resizing Windows. This is needed to workaround
    def to_window(self, x, y):
        return self.control.to_window(x, y)

if __name__ == "__main__":

    app = TheApp()
    c = app.control
    songscreen = c.create_song_screen(sys.argv[1])
    c.set_active_screen(songscreen.screen_id)
    app.run()

