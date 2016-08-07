import console
import sys

class Box(object):
    def __init__(self, width=10, height=10):
        width = max(1, width)
        height = max(1, height)
        self.id_gen = 0
        self.parent = None
        self.refresh_flag = False
        self.has_border = False
        self.hidden = False
        self.grid = []
        self.box_positions = {}
        self.boxes = {}
        self.cached = [] # for diff()
        for y in range(height):
            self.grid.append([])
            for x in range(width):
                self.grid[-1].append("")

    def hide(self):
        self.hidden = True

    def show(self):
        self.hidden = False

    def toggle_border(self):
        self.has_border ^= True

    def width(self):
        return len(self.grid[0])

    def height(self):
        return len(self.grid)

    def set(self, x, y, c):
        self.grid[y][x] = c
        self.set_refresh_flag()

    def set_refresh_flag(self):
        self.refresh_flag = True

    def get_display(self):
        outgrid = []
        for line in self.grid:
            outgrid.append(line.copy())

        if self.has_border:
            for x in range(self.width()):
                if not outgrid[0][x]:
                    outgrid[0][x] = "."
                if not outgrid[-1][x]:
                    outgrid[-1][x] = "."

            for y in range(self.height() - 2):
                if not outgrid[y + 1][0]:
                    outgrid[y + 1][0] = "|"
                if not outgrid[y + 1][-1]:
                    outgrid[y + 1][-1] = "|"

        if not self.refresh_flag:
            return outgrid

        for box_id, box in self.boxes.items():
            if box.hidden:
                continue

            boxpos = self.box_positions[box_id]
            if boxpos[1] >= self.height() or boxpos[0] >= self.width() or (boxpos[1] + box.height() <= 0) or (boxpos[0] + box.width() <= 0):
                continue
            boxdisp = box.get_display()
            for y in range(min(box.height(), len(outgrid) - boxpos[1])):
                for x in range(min(box.width(), len(outgrid[0]) - boxpos[0])):
                    try:
                        if boxdisp[y][x]:
                            outgrid[boxpos[1] + y][boxpos[0] + x] = boxdisp[y][x]
                    except IndexError:
                        pass
        self.refresh_flag = False
        return outgrid
            
    def resize(self, new_width, new_height):
        old = self.grid.copy()
        self.reinit_flag = True
        self.grid = []
        self.resize_coords = []
        for y in range(new_height):
            self.grid.append([])
            for x in range(new_width):
                self.grid[-1].append("")
                self.resize_coords.append((x,y))

        for y in range(len(old)):
            for x in range(len(old[y])):
                try:
                    self.grid[y][x] = old[y][x]
                except IndexError:
                    pass

        self.refresh_flag = True
        if self.parent:
            self.parent.set_refresh_flag()

    def get_diff(self):
        disp = self.get_display()
        diff = []
        for y in range(len(disp)):
            for x in range(len(disp[y])):
                if not self.cached:
                    diff.append((x, y, disp[y][x]))
                elif self.cached[y][x] != disp[y][x]:
                    diff.append((x, y, disp[y][x]))

        self.cached = disp
        return diff


    def _parse_kwargs(self, key, kw_dict, default):
        try:
            return kw_dict[key]
        except KeyError:
            return default

    def refresh(self):
        self.refresh_flag = True
        if self.parent:
            self.parent.refresh()  

    def add_box(self, **kwargs):
        x = self._parse_kwargs("x", kwargs, 0)
        y = self._parse_kwargs("y", kwargs, 0)
        w = self._parse_kwargs("width", kwargs, 10)
        h = self._parse_kwargs("height", kwargs, 10)

        box = Box(w, h)
        box.parent = self
        new_id = self.id_gen
        self.id_gen += 1
        box.id = new_id
        self.boxes[new_id] = box
        self.box_positions[new_id] = (x,y)

        return new_id

    def rem_box(self, b_id):
        try:
            del self.boxes[b_id]
        except KeyError:
            pass
        try:
            del self.box_positions[b_id]
        except KeyError:
            pass

    def kill(self):
        if self.parent:
            self.parent.rem_box(self.id)
            self.parent.refresh()
        
class BoxEnvironment(Box):
    def __init__(self):
        width, height = console.getTerminalSize()
        self.draw_cache = []
        Box.__init__(self, width, height)

    def init_screen(self):
        sys.stdout.write("\033[?25l")

    def destroy(self):
        sys.stdout.write("\033[1;1H")
        sys.stdout.write("\033[?25h")

    def refresh(self):
        self.refresh_flag = True
        disp = self.get_diff()
        for x, y, c in disp:
            if not c:
                c = " "
            sys.stdout.write("\033[%d;%dH%s" % (y + 1, x + 1, c))
        sys.stdout.write("\033[1;1H\n")

