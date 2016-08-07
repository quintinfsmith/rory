from Box import Box, BoxEnvironment
from getCh import getCh

class InputNode(object):
    def __init__(self):
        self.children = {}
        self.action = None
        self.args = None

    def set(self, path, action, args=None):
        if path:
            n = path[0]
            path = path[1:]
            if not n in self.children.keys():
                self.children[n] = InputNode()
            self.children[n].set(path, action, args)
        else:
            self.action = action
            self.args = args

    def get(self, path):
        if path:
            n = path[0]
            path = path[1:]
            if n in self.children.keys():
                return self.children[n].get(path)
            else:
                return None
        else:
            return self

class Interactor(object):
    def __init__(self):
        self.cmdNode = InputNode()
        self.general_register = 0

        self.cmdNode.set('0', self.input_to_register, 0)
        self.cmdNode.set('1', self.input_to_register, 1)
        self.cmdNode.set('2', self.input_to_register, 2)
        self.cmdNode.set('3', self.input_to_register, 3)
        self.cmdNode.set('4', self.input_to_register, 4)
        self.cmdNode.set('5', self.input_to_register, 5)
        self.cmdNode.set('6', self.input_to_register, 6)
        self.cmdNode.set('7', self.input_to_register, 7)
        self.cmdNode.set('8', self.input_to_register, 8)
        self.cmdNode.set('9', self.input_to_register, 9)
        self.cmdNode.set(chr(27), self.clear_register)
        
        self.active_node = self.cmdNode

    def get_input(self):
        self.check_cmd(getCh())

    def check_cmd(self, char):
        node = self.active_node.get(char)
        top = self.active_node == self.cmdNode 

        if node:
            if node.action:
                if not node.args is None:
                    node.action(node.args)
                else:
                    node.action()
                self.active_node = self.cmdNode
            else:
                self.active_node = node
        else:
            # If an invalid path is given, then interactor
            # will check if the last given character is in
            # a path of its own and either call that function
            # or just get the input sequence started
            self.active_node = self.cmdNode
            if not top:
                self.check_cmd(char)

    def assign_sequence(self, string_seq, func, arg=None):
        self.cmdNode.set(string_seq, func, arg)

    def input_to_register(self, n):
        self.general_register *= 10
        self.general_register += n
    
    def clear_register(self):
        self.general_register = 0

