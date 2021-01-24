'''Interface between user and player'''
import threading
import time
import wrecked
from wrecked import RectStage
from apres import MIDI

from rory.midicontroller import MIDIController
from rory.player import Player
from rory.interactor import Interactor

class TerminalTooNarrow(Exception):
    '''Error thrown when the minimum width required isn't available'''

class Top(RectStage):
    '''Interface to Run the MidiPlayer'''
    CONTEXT_DEFAULT = 0
    CONTEXT_PLAYER = 1
    def __init__(self):
        super().__init__()

        if self.rect.width < 90:
            self.kill()
            raise TerminalTooNarrow()

        self.interactor = Interactor()
        self.midi_controller = MIDIController()
        self.interactor.assign_context_sequence(
            self.CONTEXT_DEFAULT,
            'q',
            self.kill
        )

        self.playerscene = None
        self.set_fps(24)

        thread = threading.Thread(target=self._input_daemon)
        thread.start()


    def play_along(self, midi_path):
        '''Run the Player with the loaded MidiLike Object'''

        if not self.playerscene:
            self.playerscene = self.create_scene(self.CONTEXT_PLAYER, PlayerScene,
                path=midi_path,
                controller=self.midi_controller
            )
        player = self.playerscene.player

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'j',
            player.next_state
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'k',
            player.prev_state
        )

        for digit in range(10):
            self.interactor.assign_context_sequence(
                self.CONTEXT_PLAYER,
                str(digit),
                player.set_register_digit,
                digit
            )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'p',
            player.jump_to_register_position,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            '[',
            player.set_loop_start_to_position,
        )
        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            ']',
            player.set_loop_end_to_position,
        )

        self.interactor.assign_context_sequence(
            self.CONTEXT_PLAYER,
            'q',
            self.kill
        )

        self.interactor.set_context(self.CONTEXT_PLAYER)
        self.start_scene(self.CONTEXT_PLAYER)

    def kill(self):
        try:
            self.playerscene.kill()
        except:
            pass
        super().kill()

    def _input_daemon(self):
        '''Main loop, just handles computer keyboard input'''
        while not self.playing:
            time.sleep(.01)

        while self.playing:
            self.interactor.get_input()


#def logg(*msg):
#    with open('logg', 'a') as fp:
#        for m in msg:
#            fp.write(str(m) + "\n")

class PlayerScene(wrecked.RectScene):
    '''Handles visualization of the Player'''
    # Display constants
    SHARPS = (1, 3, 6, 8, 10)
    NOTELIST = 'CCDDEFFGGAAB'

    def __init__(self, rect_id, rectmanager, **kwargs):
        super().__init__(rect_id, rectmanager, **kwargs)

        self.active_midi = MIDI(kwargs['path'])
        self.midi_controller = kwargs['controller']

        self.rect_background = self.new_rect()
        self.layer_visible_notes = self.rect_background.new_rect()
        self.layer_active_notes = self.rect_background.new_rect()

        self.visible_note_rects = []
        self.pressed_note_rects = {}

        self.rect_position_display = self.new_rect()

        self.active_row_position = 8
        self.player = Player(**kwargs)

    def tick(self):
        was_flagged = False
        player = self.player
        if player.disp_flags[player.FLAG_BACKGROUND]:
            self.__draw_background()
            player.disp_flags[player.FLAG_BACKGROUND] = False
            was_flagged = True

        if player.disp_flags[player.FLAG_POSITION]:
            self.__draw_visible_notes()
            player.disp_flags[player.FLAG_POSITION] = False
            player.disp_flags[player.FLAG_PRESSED] = True
            was_flagged = True

        if player.disp_flags[player.FLAG_PRESSED]:
            self.__draw_pressed_row()
            player.disp_flags[player.FLAG_PRESSED] = False
            was_flagged = True

        if was_flagged:
            self.draw()

    def __draw_visible_notes(self):
        while self.visible_note_rects:
            self.visible_note_rects.pop().detach()

        song_position = self.player.song_position
        midi_interface = self.player.midi_interface
        state_map = midi_interface.state_map

        for _y in range(self.layer_visible_notes.height):
            tick = song_position - self.active_row_position + _y

            if tick < 0 or tick >= len(state_map):
                continue

            if _y == self.active_row_position:
                y = self.rect_background.height - _y
            elif _y < self.active_row_position:
                y = self.rect_background.height - _y + 1
            else:
                y = self.rect_background.height - ((_y * 2) - self.active_row_position)


            row = midi_interface.active_notes_map[tick]
            blocked_xs = set()
            for note, message in row.items():
                x = self.__get_displayed_key_position(message.note)
                blocked_xs.add(x)

                note_rect = self.layer_visible_notes.new_rect()
                note_rect.set_character(0, 0, self.NOTELIST[message.note % 12])
                note_rect.move(x, y)

                color = self.get_channel_color(message.channel)
                if message.note % 12 in self.SHARPS:
                    note_rect.set_bg_color(color)
                    note_rect.set_fg_color(wrecked.BLACK)
                else:
                    note_rect.set_fg_color(color)

                self.visible_note_rects.append(note_rect)

            # Draw Measure Lines
            if tick in midi_interface.measure_map.keys() and _y != self.active_row_position:
                for x in range(2, self.rect_background.width, 4):
                    if x in blocked_xs:
                        continue
                    if x % 14 == 0:
                        continue

                    line_rect = self.layer_visible_notes.new_rect()
                    line_rect.set_character(0, 0, '-')
                    line_rect.move(x, y)
                    line_rect.set_fg_color(wrecked.BRIGHTBLACK)

                    self.visible_note_rects.append(line_rect)


        # Active Row Line
        active_y = self.rect_background.height - self.active_row_position
        if song_position in midi_interface.measure_map.keys():
            line_char = chr(9552)
        else:
            line_char = chr(9472)

        for x in range(self.rect_background.width):
            self.rect_background.set_character(x, active_y, line_char)

        position_string = "%s / %s" % (song_position, len(state_map))
        self.rect_position_display.resize(len(position_string), 1)
        self.rect_position_display.move(self.width - len(position_string) - 1, self.height - 1)
        self.rect_position_display.set_string(0, 0, position_string)

    def __draw_pressed_row(self):
        keys = list(self.pressed_note_rects.keys())
        for key in keys:
            self.pressed_note_rects[key].remove()
            del self.pressed_note_rects[key]

        player = self.player
        midi_interface = player.midi_interface
        song_position = player.song_position

        active_state = midi_interface.get_state(song_position)

        y = self.height - self.active_row_position

        pressed_notes = player.pressed_notes.copy()
        for note in pressed_notes:
            x = self.__get_displayed_key_position(note)

            note_rect = self.layer_active_notes.new_rect()
            note_rect.set_character(0, 0, chr(9473))
            note_rect.move(x, 1)

            if note in player.need_to_release:
                if note in active_state:
                    note_rect.set_fg_color(wrecked.YELLOW)
                else:
                    note_rect.set_fg_color(wrecked.RED)
            else:
                if note in active_state:
                    note_rect.set_fg_color(wrecked.GREEN)
                else:
                    note_rect.set_fg_color(wrecked.RED)

            self.pressed_note_rects[note] = note_rect


    def __draw_background(self):
        player = self.player
        note_range = player.note_range
        width = self.__get_displayed_key_position(note_range[1] + 1)
        self.rect_background.set_fg_color(wrecked.BRIGHTBLACK)

        self.rect_background.resize(
            height = self.height,
            width = width
        )
        self.layer_visible_notes.resize(
            height=self.height,
            width = width
        )
        self.layer_visible_notes.set_transparency(True)

        background_pos = (self.width - width) // 2
        self.rect_background.move(background_pos, 0)

        y = self.height - self.active_row_position

        self.layer_active_notes.resize(self.rect_background.width, 2)
        self.layer_active_notes.move(0, y)
        self.layer_active_notes.set_transparency(True)

        for i in range(note_range[0], note_range[1]):
            x = self.__get_displayed_key_position(i)

            if i % 12 in self.SHARPS:
                self.rect_background.set_character(x, y - 1, chr(9608))
            else:
                self.rect_background.set_character(x, y + 1, chr(9620))

            if (i + 3) % 12 == 0:
                for j in range(0, y - 1):
                    self.rect_background.set_character(x, j, chr(9550))

                for j in range(y + 2, self.rect_background.height):
                    self.rect_background.set_character(x, j, chr(9550))

        for y in range(self.height):
            self.set_character(background_pos - 1, y, chr(9475))
            self.set_character(background_pos + width, y, chr(9475))

    def __get_displayed_key_position(self, midi_key):
        piano_position = midi_key - self.player.note_range[0]
        octave = piano_position // 12
        piano_key = piano_position % 12
        position = (octave * 14) + piano_key

        if piano_key > 2: # B
            position += 1
        if piano_key > 7:
            position += 1

        return position

    @staticmethod
    def get_channel_color(channel):
        colors = [
            wrecked.BRIGHTYELLOW,
            wrecked.WHITE,
            wrecked.CYAN,
            wrecked.GREEN,
            wrecked.MAGENTA,
            wrecked.BLUE,
             # i *think* it's channel 7 that is drums... if so, this is just a placeholder
            wrecked.BRIGHTBLACK,
            wrecked.RED
        ]
        color = colors[channel % 8]

        if channel > 8:
            color ^= wrecked.BRIGHT

        return color

    def kill(self):
        ''' Tear down the player backend '''
        self.player.kill()
