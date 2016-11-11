'''Allow subclasses to listen for keyboard input'''
from localfuncs import read_character

class InputNode(object):
    '''tree-like node to determine input-sequence'''
    def __init__(self):
        self.children = {}
        self.action = None
        self.args = None

    def set(self, path, action, args=None):
        '''Assign a function to an end-node in node-tree'''
        if path:
            node = path[0]
            path = path[1:]
            if not node in self.children.keys():
                self.children[node] = InputNode()
            self.children[node].set(path, action, args)
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
        self.cmd_node = InputNode()

        self.active_node = self.cmd_node

    def get_input(self):
        '''Send keypress to be handled'''
        self.check_cmd(read_character())

    def check_cmd(self, char):
        '''Add key-press to key-sequence, call function if any'''
        node = self.active_node.get(char)
        top = self.active_node == self.cmd_node

        if node:
            if node.action:
                if not node.args is None:
                    node.action(node.args)
                else:
                    node.action()
                self.active_node = self.cmd_node
            else:
                self.active_node = node
        else:
            # If an invalid path is given, then interactor
            # will check if the last given character is in
            # a path of its own and either call that function
            # or just get the input sequence started
            self.active_node = self.cmd_node
            if not top:
                self.check_cmd(char)

    def assign_sequence(self, string_seq, func, arg=None):
        '''associate key-sequence with a function'''
        self.cmd_node.set(string_seq, func, arg)


class RegisteredInteractor(Interactor):
    '''Interactor with number register built in'''
    def __init__(self):
        Interactor.__init__(self)

        self.general_register = 0
        self.cmd_node.set('0', self.input_to_register, 0)
        self.cmd_node.set('1', self.input_to_register, 1)
        self.cmd_node.set('2', self.input_to_register, 2)
        self.cmd_node.set('3', self.input_to_register, 3)
        self.cmd_node.set('4', self.input_to_register, 4)
        self.cmd_node.set('5', self.input_to_register, 5)
        self.cmd_node.set('6', self.input_to_register, 6)
        self.cmd_node.set('7', self.input_to_register, 7)
        self.cmd_node.set('8', self.input_to_register, 8)
        self.cmd_node.set('9', self.input_to_register, 9)
        self.cmd_node.set(chr(27), self.clear_register)

    def input_to_register(self, digit): # Might remove
        '''general number register input, base 10'''
        self.general_register *= 10
        self.general_register += digit

    def clear_register(self):
        '''Clear Register'''
        self.general_register = 0
