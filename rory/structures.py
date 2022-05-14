"""
    Specialized generic structures to help with midi note processing.
    Only Grouping at the moment.
"""
from __future__ import annotations
import math
from enum import Enum, auto
from typing import Optional

class BadStateError(Exception):
    """Thrown if an incompatible operation is attempted on a Grouping Object"""
class SelfAssignError(Exception):
    """Thrown when a Grouping is assigned to itself as a subgrouping"""

class GroupingState(Enum):
    """The states that a Grouping can be in"""
    EVENT = auto()
    STRUCTURE = auto()
    OPEN = auto()

class Grouping:
    """
        Tree-like structure that can be flattened and
        unflattened as necessary while keeping relative positions
    """
    def __init__(self):
        self.size: int = 1
        self.divisions = {}
        self.events = set()
        self.state: GroupingState = GroupingState.OPEN
        self.parent: Optional[Grouping] = None

    def __str__(self):
        output = ''
        if self.events:
            output += str(self.events)
        else:
            for i, grouping in self.divisions.items():
                grp_str = str(grouping).strip()
                if grp_str:
                    tab = "\t" * self.get_depth()
                    output += f"{tab}{i+1}/{len(self)}) \t{grp_str}\n"

        return output.strip() + "\n"

    def __len__(self):
        return self.size

    def __getitem__(self, i: int) -> Grouping:
        """
            Get a the grouping at the specified index.
            Will create a new grouping if none exists yet
        """
        if not self.is_structural():
            raise BadStateError()

        if i >= self.size:
            raise IndexError()

        try:
            output = self.divisions[i]
        except KeyError:
            output = Grouping()
            self[i] = output

        return output

    def __setitem__(self, i: int, grouping: Grouping):
        """Assign an existing Grouping to be a subgrouping."""
        if not self.is_structural():
            raise BadStateError()

        if grouping == self:
            raise SelfAssignError()

        if i >= self.size:
            raise IndexError()

        grouping.parent = self
        self.divisions[i] = grouping

    def _get_state(self) -> GroupingState:
        return self.state

    def is_structural(self) -> bool:
        """Check if this grouping has sub groupings"""
        return self._get_state() == GroupingState.STRUCTURE

    def is_event(self) -> bool:
        """Check if this grouping has any events"""
        return self._get_state() == GroupingState.EVENT

    def is_open(self) -> bool:
        """Check that this grouping is neither event nor structural"""
        return self._get_state() == GroupingState.OPEN

    def is_flat(self) -> bool:
        """Check if this grouping has no sub-subgroupings and only event/open subgroupings"""
        is_flat = True
        for child in self.divisions.values():
            if child.is_structural():
                is_flat = False
                break
        return is_flat

    def set_size(self, size: int):
        """Resize a grouping if it doesn't have any events. Will clobber existing subgroupings."""
        if self.is_event():
            raise BadStateError()

        self.set_state(GroupingState.STRUCTURE)
        self.divisions = {}
        self.size = size

    def set_state(self, new_state: GroupingState):
        """Sets the state of the Grouping so that invalid operations can't be applied to them"""
        self.state = new_state

    # TODO: Should this be recursive?
    def reduce(self, target_size=0):
        """
            Reduce a flat list of event groupings into smaller divisions
            while keeping the correct ratios.
            (eg midi events to musical notation)
        """
        if not self.is_structural():
            raise BadStateError()

        # Get the active indeces on the current level
        indeces = []
        for i, grouping in self.divisions.items():
            indeces.append((i, grouping))
        indeces.sort()

        # Use a temporary Grouping to build the reduced version
        place_holder = Grouping()
        stack = [(1, indeces, self.size, place_holder)]
        first_pass = True
        while stack:
            denominator, indeces, previous_size, grouping = stack.pop(0)
            current_size = previous_size // denominator

            # Create separate lists to represent the new equal groupings
            split_indeces = []
            for _ in range(denominator):
                split_indeces.append([])
            grouping.set_size(denominator)

            # move the indeces into their new lists
            for i, subgrouping in indeces:
                split_index = i // current_size
                split_indeces[split_index].append((i % current_size, subgrouping))

            for i in range(denominator):
                working_indeces = split_indeces[i]
                if not working_indeces:
                    continue

                working_grouping = grouping[i]

                # Get the most reduced version of each index
                minimum_divs = []
                for index, subgrouping in working_indeces:
                    most_reduced = int(current_size / math.gcd(current_size, index))
                    # mod the indeces to match their new relative positions
                    if most_reduced > 1:
                        minimum_divs.append(most_reduced)

                minimum_divs = list(set(minimum_divs))
                minimum_divs.sort()
                if first_pass and target_size > 0:
                    stack.append((
                        target_size,
                        working_indeces,
                        current_size,
                        working_grouping
                    ))
                elif minimum_divs:
                    stack.append((
                        minimum_divs[0],
                        working_indeces,
                        current_size,
                        working_grouping
                    ))
                else: # Leaf
                    _, event_grouping = working_indeces.pop(0)
                    for event in event_grouping.events:
                        working_grouping.add_event(event)
            first_pass = False

        self.set_size(len(place_holder[0]))
        for i, grouping in place_holder[0].divisions.items():
            self[i] = grouping

        return place_holder

    def flatten(self):
        """if all the subdivisions are the same sizes, merge them up into this level"""

        sizes = []
        subgroup_backup = []
        original_size = self.size
        for i, child in self.divisions.items():
            if not child.is_structural():
                pass
            elif not child.is_flat():
                child.flatten()
                sizes.append(max(1, len(child)))
            subgroup_backup.append((i, child))

        # TODO: This needs to be minimized/factored
        new_size = len(sizes)
        sizes = list(set(sizes))
        for size in sizes:
            new_size *= size

        self.set_size(new_size)
        chunk_size = new_size / original_size
        for i, child in subgroup_backup:
            pass
            #TODO Reimplement


    def add_event(self, event):
        """Add an event to grouping's set of events"""
        if self.is_structural():
            raise BadStateError()

        self.set_state(GroupingState.EVENT)
        self.events.add(event)

    def remove_event(self, event):
        """Remove an event from the groupings set of events"""
        if not self.is_event():
            raise BadStateError()

        if event not in self.events:
            raise IndexError(f"{event} not in event list")

        self.events.remove(event)

    def get_events(self):
        """Get set of grouping's set of events"""
        if not self.is_event():
            raise BadStateError()

        return self.events

    def get_depth(self):
        """Find how many parents/supergroupings this grouping has """
        depth = 0
        working_grouping = self
        while working_grouping is not None:
            depth += 1
            working_grouping = working_grouping.parent

        return depth

    def __list__(self):
        output = []
        for i in range(self.size):
            grouping = self[i]
            output.append(grouping)
        return output

def main():
    """Testing Main Function"""
    opus = Grouping()
    opus.set_size(48)
    opus[0].add_event(1)
    opus[4].add_event(1)
    opus[8].add_event(1)

    opus[12].add_event(1)
    opus[16].add_event(1)
    opus[20].add_event(1)

    opus[24].add_event(1)
    opus[28].add_event(1)
    opus[32].add_event(1)

    opus[36].add_event(1)
    opus[40].add_event(1)
    opus[44].add_event(1)

    opus[47].add_event(2)

    print(opus)
    #print(opus.get_flat_min())
    opus.reduce(4)
    print(opus)
    opus.flatten()
    print(opus)

if __name__ == "__main__":
    main()
