import sys
from localfuncs import get_terminal_size

def log(msg):
    with open("testlog", "a") as filepipe:
        filepipe.write(msg + "\n")

class Box(object):
    """Easily Mutable Bo to be displayed"""
    def __init__(self, width=10, height=10):
        width = max(1, width)
        height = max(1, height)
        self.id = -1
        self.id_gen = 0
        self.parent = None
        self.refresh_flag = False
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
        '''Hide from get_display()'''
        self.hidden = True

    def show(self):
        '''Make Visible for get_display'''
        self.hidden = False

    def width(self):
        '''get Width'''
        return len(self.grid[0])

    def height(self):
        '''Get height'''
        return len(self.grid)

    def set_string(self, x, y, string):
        '''Set String in box'''
        for xx, c in enumerate(string):
            Y = xx // len(string)
            X = xx % len(string)
            try:
                self.grid[y + Y][x + X] = c
            except IndexError:
                pass
        self.set_refresh_flag()

    def clear(self):
        for y in range(len(self.grid)):
            for x in range(len(self.grid[y])):
                self.set(x,y, "")
        self.set_refresh_flag()

    def set(self, x, y, c):
        '''Set Character in box'''
        self.grid[y][x] = c
        self.set_refresh_flag()

    def set_refresh_flag(self):
        '''Force refresh on next call to get_display'''
        self.refresh_flag = True

    def get_display(self, offset=(0, 0)):
        '''Calculate which box contents to display'''
        if not self.active_box_list:
            active_boxes = list(self.boxes.keys())
        else:
            active_boxes = []
            while self.active_box_list:
                active_boxes.append(self.active_box_list.pop(0).id)

        subdisp = {}
        for box_id in active_boxes:
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
                if nx >= 0 and nx < top.width() and self.grid[y][x]:
                    out[(nx, ny)] = self.grid[y][x]

        out.update(subdisp)
        return out

    def resize(self, new_width, new_height):
        '''Resize the box'''
        old = self.grid.copy()
        self.grid = []
        resize_coords = []
        for y in range(new_height):
            self.grid.append([])
            for x in range(new_width):
                self.grid[-1].append("")
                resize_coords.append((x, y))

        for y, row in enumerate(old):
            for x, entry in enumerate(row):
                try:
                    self.grid[y][x] = entry
                except IndexError:
                    pass

        self.refresh_flag = True
        if self.parent:
            self.parent.set_refresh_flag()

    def get_diff(self):
        '''Get diff of character array to update display'''
        disp = self.get_display()
        diff = []
        for key, c in disp.items():
            x, y = key
            if not self.cached:
                diff.append((x, y, c))
            elif self.cached[(x, y)] != c:
                diff.append((x, y, c))
        self.cached = disp
        return diff


    def _parse_kwargs(self, key, kw_dict, default):
        '''Parse Keyword Arguments more easily'''
        try:
            return kw_dict[key]
        except KeyError:
            return default

    def refresh(self, active_box_list=None):
        '''Force redraw of parent box recursively'''
        if not active_box_list:
            active_box_list = []

        if active_box_list:
            self.active_box_list = active_box_list.copy()
        if self.parent:
            self.parent.refresh()

    def add_box(self, **kwargs):
        '''Create new sub-Box'''
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
        self.box_positions[new_id] = (x, y)
        return new_id

    def move_box(self, box_id, x, y):
        '''Move a sub Box'''
        self.box_positions[box_id] = (x, y)

    def rem_box(self, b_id):
        '''Remove A Sub Box'''
        try:
            del self.boxes[b_id]
        except KeyError:
            pass
        try:
            del self.box_positions[b_id]
        except KeyError:
            pass

    def kill(self):
        '''remove this box from the parent node and refresh'''
        if self.parent:
            self.parent.rem_box(self.id)
            self.parent.refresh()

class BoxEnvironment(Box):
    """Canvas on which to manipulate boxes"""
    def __init__(self):
        width, height = get_terminal_size()
        self.draw_cache = []
        self.w_coords = []
        self.c_coords = []
        for y in range(height):
            self.c_coords.append((20, y))
            for x in range(width):
                self.w_coords.append((x, y))
        Box.__init__(self, width, height)

    def init_screen(self):
        '''Prepare screen for use'''
        sys.stdout.write("\033[1;1H")
        sys.stdout.write("\033[?25l")

    def destroy(self):
        '''Reshow cursor and enable default text'''
        self.boxes = {}
        for y in range(self.height()):
            for x in range(self.width()):
                self.set(x,y, " ")

        sys.stdout.write("\033[1;1H")
        sys.stdout.write("\033[?25h")

    def refresh(self, active_box_list=None):
        '''Redraw display'''
        if not active_box_list:
            active_box_list = []
        self.active_box_list = active_box_list
        disp = self.get_diff()
        for x, y, c in disp:
            if not c:
                c = " "
            sys.stdout.write("\033[%d;%dH%s" % (y + 1, x + 1, c))
        sys.stdout.write("\033[1;1H\n")

