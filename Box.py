import console
import sys
import time
import math

def log(msg):
    with open("testlog", "a") as fp:
        fp.write(msg + "\n")

def do_collide(a, b):
    ax = a[0] + (a[2] / 2)
    bx = b[0] + (b[2] / 2)
    ay = a[1] + (a[3] / 2)
    by = b[1] + (b[3] / 2)
    return (math.fabs(ax - bx) * 2) < (a[2] + b[2]) and (math.fabs(ay - by) * 2) < (a[3] + b[3])

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
        self.active_box_list = []
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

        
    def get_display(self, offset=(0,0)):
        if not self.active_box_list:
            boxes = set(self.boxes.keys())
        else:
            boxes = []
            while self.active_box_list:
                boxes.append(self.active_box_list.pop().id)

        

        subdisp = {}
        for box_id in boxes:
            box = self.boxes[box_id]
            boxpos = self.box_positions[box_id]
            new_offset = (offset[0] + boxpos[0], offset[1] + boxpos[1])
            tmp = box.get_display(new_offset)
            subdisp.update(tmp)

        top = self
        while top.parent:
           top = top.parent

        out = {}
        for y in range(self.height()):
            ny = y + offset[1]
            if ny < 0 or ny >= top.height():
                continue
            for x in range(self.width()):
                nx = x + offset[0]
                if  nx >= 0 and  nx < top.width() and self.grid[y][x]:
                    out[(nx,ny)] = self.grid[y][x]

        out.update(subdisp)
        return out
            
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
        for key, c in disp.items():
            x, y  = key
            if not self.cached:
                diff.append((x, y, c))
            elif self.cached[(x,y)] != c:
                diff.append((x, y, c))
        self.cached = disp
        return diff


    def _parse_kwargs(self, key, kw_dict, default):
        try:
            return kw_dict[key]
        except KeyError:
            return default

    def refresh(self, active_box_list=[]):
        if active_box_list:
            self.active_box_list = active_box_list.copy()
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

    def move_box(self, box_id, x, y):
        self.box_positions[box_id] = (x,y)

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
        self.w_coords = []
        self.c_coords = []
        for y in range(height):
            self.c_coords.append((20, y))
            for x in range(width):
                self.w_coords.append((x,y))
        Box.__init__(self, width, height)

    def init_screen(self):
        sys.stdout.write("\033[?25l")

    def destroy(self):
        sys.stdout.write("\033[1;1H")
        sys.stdout.write("\033[?25h")

    def refresh(self, active_box_list=[]):
        self.active_box_list = active_box_list
        disp = self.get_diff()
        for x, y, c in disp:
            if not c:
                c = " "
            sys.stdout.write("\033[%d;%dH%s" % (y + 1, x + 1, c))
        sys.stdout.write("\033[1;1H\n")

