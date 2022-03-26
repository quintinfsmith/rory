import math, json

class Grouping:
    def __init__(self):
        self.divisions = []
        self.events = set()
    def __len__(self):
        return len(self.divisions)

    def set_size(self, size):
        self.divisions = []
        while len(self.divisions) < size:
            self.divisions.append(Grouping())

    def iter(self):
        return self.divisions

    def get_flat_min(self):
        if len(self) == 0:
            return (1, [(0, set(self.events))])

        sub_divs = []
        div_counts = []
        for div in self.iter():
            sub_div = div.get_flat_min()
            div_counts.append(sub_div[0])
            sub_divs.append(sub_div)

        new_size = math.prod(div_counts) // math.gcd(*div_counts)
        output = []
        size = 0
        for p, sub_div in enumerate(sub_divs):
            factor = new_size // sub_div[0]
            for i, item in sub_div[1]:
                if len(item):
                    output.append(((i * factor) + (p * new_size), item))
            size += new_size
        return (size, output)

    def reduce(self):
        if not self.divisions:
            return

        group_map = {}
        pos_paths = {}
        s = []
        for i in range(len(self.divisions)):
            group = self.get_grouping(i)
            if len(group.events):
                group_map[i] = group
                pos_paths[i] = []
                s.append((i, i))

        paths = {}
        stack = [(s, len(self.divisions), [])]
        while stack:
            current_structure, current_div, path = stack.pop(0)
            indeces = []
            smallest_divisions = []
            while current_structure:
                (i, original_i)  = current_structure.pop(0)
                indeces.append((i, original_i))
                if i == 0:
                    paths[original_i] = path
                    continue

                smallest_division = int(current_div / math.gcd(current_div, i))
                smallest_divisions.append(smallest_division)

            if smallest_divisions:
                gcd = math.gcd(*smallest_divisions)
                if gcd == 1:
                    for (index, o_index) in indeces:
                        next_level = [(0, o_index)]

                        next_path = path.copy()
                        next_path.append(0)

                        current_structure.append(next_level)
                        stack.append((next_level, 1, next_path))
                else:
                    for i in range(gcd):
                        next_level = []
                        for (index, o_index) in indeces:
                            n = int((index * gcd) / current_div)
                            if i == n:
                                next_level.append((index - ((current_div // gcd) * i), o_index))
                        current_structure.append(next_level)
                        next_path = path.copy()
                        next_path.append(i)
                        stack.append((next_level, current_div // gcd, next_path))

        og_divs = self.divisions
        stack = [(s, self)]
        while stack:
            arm, grouping = stack.pop(0)
            grouping.set_size(len(arm))
            for i, element in enumerate(arm):
                stack.append((element, grouping.get_grouping(i)))

        for k, p in paths.items():
            g = self
            for i in p:
                g = g.get_grouping(i)

            while len(g.divisions):
                g = g.get_grouping(0)

            g.events = og_divs[k].events

    def flatten(self):
        ''' if all the subdivisions are the same sizes, merge them up into this level '''
        if not self.divisions:
            return

        for child in self.divisions:
            child.flatten()

        sizes = []
        for child in self.divisions:
            l = len(child.divisions)
            sizes.append(l)
        if sizes and sum(sizes) == len(self.divisions) * sizes[0] and sum(sizes):
            new_size = sizes[0] * len(self.divisions)
            og_divs = self.divisions
            self.set_size(new_size)
            n = 0
            for i, child in enumerate(og_divs):
                for subchild in child.divisions:
                    self.divisions[n] = subchild
                    n += 1

    def get_grouping(self, i):
        return self.divisions[i]

    def add_event(self, event):
        self.events.add(event)
    def remove_event(self, event):
        self.events.remove(event)

    def _get_str(self, depth=0):
        lines = []

        if self.events:
            lines.append(str(self.events))

        subgroupings = []
        if depth > 0 or self.events:
            tab = "\t|"
        else:
            tab = ''

        for grouping in self.divisions:
            grp_str = grouping.get_str(depth + 1)
            subgroupings.append(grp_str)

        if subgroupings:
            for i, line in enumerate(subgroupings):
                if i == 0 and lines:
                    lines[-1] += tab + line
                else:
                    lines.append(tab + line)

        line = '-' * 25
        output = ("\n" + line + "\n").join(lines)

        return output

    def get_str(self, depth=0):
        output = ''
        if self.events:
            output += str(self.events)
        else:
            for i, grouping in enumerate(self.divisions):
                grp_str = grouping.get_str(depth +1).strip()
                if (grp_str):
                    output += "%s%d/%d) \t%s\n" % ("\t" * depth, i + 1, len(self.divisions), grp_str)

        return output.strip() + "\n"

    def __str__(self):
        return self.get_str()


if __name__ == "__main__":
    opus = Grouping()
    measures = 480
    opus.set_size(measures)
    for i in range(16):
        opus.get_grouping(measures * i  // 16).add_event(40)
    opus.reduce()
    #opus.flatten()
    print(opus.get_flat_min())
