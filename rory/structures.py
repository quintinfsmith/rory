from __future__ import annotations
import math
from abc import ABC
from enum import Enum, auto
from typing import Optional

class BadStateError(Exception):
    """Thrown if an incompatible operation is attempted on a Grouping Object"""

class GroupingState(Enum):
    Event = auto()
    Structure = auto()
    Open = auto()

class Grouping:
    def __init__(self):
        self.size: int = 1
        self.divisions: dict[int, Grouping] = {}
        self.events = set()
        self.state: GroupingState = GroupingState.Open

    def get_state(self) -> GroupingState:
        return self.state

    def __len__(self):
        return self.size

    def set_size(self, size: int):
        if self.state == GroupingState.Event:
            raise BadStateError()

        self.state = GroupingState.Structure
        self.divisions = {}
        self.size = size

    def reduce(self):
        if self.state != GroupingState.Structure:
            return

        # Get the active indeces on the current level
        indeces = list(self.divisions.keys())
        print(indeces)
        indeces.sort()

        # YO Q!, Right now the math working but nothing being modified.
        # I think making this a recusive function may make it simpler to track
        # event indeces in order to modify them
        stack = [(1, indeces, self.size)]
        while stack:
            print(stack[0])
            denominator, indeces, previous_size = stack.pop(0)
            current_size = previous_size // denominator

            # Create separate lists to represent the new equal groupings
            split_indeces = []
            for _ in range(denominator):
                split_indeces.append([])

            # move the indeces into their new lists
            for i in indeces:
                split_index = i // current_size
                split_indeces[split_index].append(i % current_size)

            for i in range(denominator):
                working_indeces = split_indeces[i]
                # Get the most reduced version of each index
                minimum_divs = []
                for index in working_indeces:
                    most_reduced = int(current_size / math.gcd(current_size, index))
                    # mod the indeces to match their new relative positions
                    if most_reduced > 1:
                        minimum_divs.append(most_reduced)

                minimum_divs = list(set(minimum_divs))
                minimum_divs.sort()
                if minimum_divs:
                    stack.append((minimum_divs[0], working_indeces, current_size))




        #min_div = min(*smallest_divisions)
        #indeces = [i / min_div for i in smallest_divisions]
        #new_size = self.size // min_div

        #if smallest_divisions:
        #    gcd = math.gcd(*smallest_divisions)
        #    for index in indeces:
        #        pass


        #if smallest_divisions:
        #    gcd = math.gcd(*smallest_divisions)
        #    print(gcd, smallest_divisions)
        #    for i in range(gcd):
        #        next_level = []
        #        for (index, o_index) in indeces:
        #            n = int((index * gcd) / current_div)
            #            if i == n:
        #                next_level.append((index - ((current_div // gcd) * i), o_index))
        #        current_structure.append(next_level)
        #        next_path = path.copy()
        #        next_path.append(i)
        #        stack.append((next_level, current_div // gcd, next_path))



    def flatten(self):
        ''' if all the subdivisions are the same sizes, merge them up into this level '''
        if not self.divisions:
            return

        sizes = []
        subgroup_backup = []
        original_size = self.size
        for i, child in self.divisions.items():
            child.flatten()
            sizes.append(max(1, len(child)))
            subgroup_backup.append((i, child))

        # TODO: This could probably be minimized/factored
        new_size = len(sizes)
        sizes = list(set(sizes))
        for size in sizes:
            new_size *= size

        self.set_size(new_size)
        chunk_size = new_size / original_size
        for i, child in subgroup_backup:
            new_position_coarse = i * chunk_size
            if child.get_state() == GroupingState.Structure:
                fine_chunk_size = chunk_size / len(child)
                for j, grandchild in child.divisions.items():
                    new_position_fine = j * fine_chunk_size
                    position = new_position_coarse + new_position_fine
                    for event in grandchild.events:
                        self.get_grouping(int(position)).add_event(event)
            else:
                new_position_fine = 0
                position = new_position_coarse + new_position_fine
                for event in child.events:
                    self.get_grouping(int(position)).add_event(event)


    def get_grouping(self, i: int) -> Grouping:
        if self.state != GroupingState.Structure:
            raise BadStateError()

        if i >= self.size:
            raise IndexError()

        try:
            output = self.divisions[i]
        except KeyError:
            output = Grouping()
            self.divisions[i] = output

        return output

    def add_event(self, event: int):
        if self.state == GroupingState.Structure:
            raise BadStateError()

        self.state = GroupingState.Event
        self.events.add(event)

    def remove_event(self, event: int):
        if self.state != GroupingState.Event:
            raise BadStateError()
        if event not in self.events:
            raise IndexError(f"{event} not in event list")

        self.events.remove(event)

    def get_str(self, depth=0):
        output = ''
        if self.events:
            output += str(self.events)
        else:
            for i, grouping in self.divisions.items():
                grp_str = grouping.get_str(depth +1).strip()
                if grp_str:
                    tab = "\t" * depth
                    output += f"{tab}{i+1}/{len(self)}) \t{grp_str}\n"

        return output.strip() + "\n"

    def __str__(self):
        return self.get_str()


def main():
    opus = Grouping()
    opus.set_size(48)
    opus.get_grouping(0).add_event(1)
    opus.get_grouping(4).add_event(1)
    opus.get_grouping(8).add_event(1)
    opus.get_grouping(12).add_event(1)
    opus.get_grouping(16).add_event(1)
    opus.get_grouping(20).add_event(1)
    opus.get_grouping(24).add_event(1)
    opus.get_grouping(28).add_event(1)
    opus.get_grouping(32).add_event(1)
    opus.get_grouping(36).add_event(1)
    opus.get_grouping(39).add_event(1)
    opus.get_grouping(42).add_event(1)
    opus.get_grouping(45).add_event(2)


    #print(opus)
    #print(opus.get_flat_min())
    opus.reduce()
if __name__ == "__main__":
    main()
