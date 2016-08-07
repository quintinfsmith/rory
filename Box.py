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
        self.grid = []
        self.box_positions = {}
        self.boxes = {}
        self.cached = [] # for diff()
        for y in range(height):
            self.grid.append([])
            for x in range(width):
                self.grid[-1].append("")

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
            for y in range(len(outgrid)):
                if y in (0, len(outgrid) - 1):
                    for x in range(len(outgrid[y])):
                        if not outgrid[y][x]:
                            outgrid[y][x] = "."
                else:
                    if not outgrid[y][0]:
                        outgrid[y][0] = "|"
                    if not outgrid[y][-1]:
                        outgrid[y][-1] = "|"

        if not self.refresh_flag:
            return outgrid

        for box_id, box in self.boxes.items():
            boxpos = self.box_positions[box_id]
            if boxpos[1] >= self.height() or boxpos[0] >= self.width() or (boxpos[1] + box.height() <= 0) or (boxpos[0] + box.width() <= 0):
                continue
            boxdisp = box.get_display()
            for y in range(min(len(boxdisp), len(outgrid) - boxpos[1])):
                for x in range(min(len(boxdisp[0]), len(outgrid[0]) - boxpos[0])):
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
        self.boxes[new_id] = box
        self.box_positions[new_id] = (x,y)

        return new_id
        
class BoxEnvironment(Box):
    def __init__(self):
        width, height = console.getTerminalSize()
        self.draw_cache = []
        height -= 1
        Box.__init__(self, width, height)

    def init_screen(self):
        sys.stdout.write("\033[?25l")       

    def destroy(self):
        sys.stdout.write("\033[0;0H")
        sys.stdout.write("\033[?25h")

    def refresh(self):
        self.refresh_flag = True
        disp = self.get_diff()
        for x, y, c in disp:
            if not c:
                c = " "
            sys.stdout.write("\033[%d;%dH%s" % (y, x, c))
        sys.stdout.write("\n")

if __name__ == "__main__":
    be = BoxEnvironment()
    be.init_screen()
    new_box = be.add_box(x=10, y=10, w=10, h=2)
    new_box.set(3,1, "H")
    new_box.set(4,1, "E")
    new_box.set(5,1, "L")
    new_box.set(6,1, "L")
    new_box.set(7,1, "O")
    be.refresh()
    be.destroy()
