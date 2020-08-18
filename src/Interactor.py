'''Allow subclasses to listen for keyboard input'''
from localfuncs import read_character
import threading
import time

class FunctionTreeNode(object):
    '''tree-like node to determine input-sequence'''
    def __init__(self):
        self.children = {}
        self.action = None
        self.args = None

    def get_spread(self):
        output = 0
        if self.action:
            output += 1
        else:
            for child in self.children.values():
                output += child.get_spread()

        return output

    def unset(self, path):
        if path:
            node = path[0]
            path = path[1:]
            if node in self.children.keys():
                self.children[node].unset(path)
                if self.children[node].get_spread() <= 1:
                    del self.children[node]
        else:
            self.action = None
            self.args = None

    def set(self, path, action, *args):
        '''Assign a function to an end-node in node-tree'''
        if path:
            node = path[0]
            path = path[1:]
            if not node in self.children.keys():
                self.children[node] = FunctionTreeNode()
            self.children[node].set(path, action, *args)
        else:
            self.action = action
            self.args = args


    def get(self, path):
        '''Return sequence at current node in sequence, if any'''
        if path:
            node = path[0]
            path = path[1:]
            if node in self.children.keys():
                return self.children[node].get(path)
            else:
                return None
        else:
            return self

class Interactor(object):
    '''Allows for interaction with keyboard input'''
    def __init__(self):
        self.active_context = 0
        self.cmd_nodes = { self.active_context: FunctionTreeNode() }

        self.active_node = self.cmd_nodes[self.active_context]

        self.backup = []
        self.checking_cmds = False

        self.ignoring_input = 0
        self.downtime = 1 / 60


    def get_input(self):
        '''Send keypress to be handled'''
        new_chr = read_character()

        if time.time() - self.ignoring_input < self.downtime:
            pass
        else:
            self.check_cmd(new_chr)


    def check_cmd(self, char):
        '''Add key-press to key-sequence, call function if any'''
        node = self.active_node.get(char)
        top = self.active_node == self.cmd_nodes[self.active_context]

        if node:
            if node.action:
                self.ignoring_input = time.time()
                if node.args:
                    node.action(*(node.args))
                else:
                    node.action()
                self.active_node = self.cmd_nodes[self.active_context]
            else:
                self.active_node = node
        else:
            # If an invalid path is given, then interactor
            # will check if the last given character is in
            # a path of its own and either call that function
            # or just get the input sequence started
            self.active_node = self.cmd_nodes[self.active_context]
            if not top:
                self.check_cmd(char)

    def assign_sequence(self, string_seq, func, *args):
        '''associate key-sequence with a function'''
        self.assign_context_sequence(
            self.active_context,
            string_seq,
            func,
            *args
        )

    def assign_context_sequence(self, context_key, string_seq, func, *args):
        if context_key not in self.cmd_nodes.keys():
            self.cmd_nodes[context_key] = FunctionTreeNode()
        self.cmd_nodes[context_key].set(string_seq, func, *args)

    def set_context(self, context_key):
        self.active_context = context_key
