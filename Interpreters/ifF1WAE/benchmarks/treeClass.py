# <file> ::= <Def>* <Prog> <Def>*

# <Prog> ::= <ifF1WAE>

# <Def> ::= { ( <id> <id> )
#                ( <ifF1WAE> ) } 


# <ifF1WAE> :: = <num>
#          | ( <op> <ifF1WAE> <ifF1WAE> )
#          | ( with ( <id> <ifF1WAE> ) <ifF1WAE> )
#          | <id>
#          | ( <id> <ifF1WAE>)
#          | ( if <ifF1WAE> <ifF1WAE> <ifF1WAE> ) # (if <cond> <true> <false>) True <=> !=0

# <op> ::= '+' | '-' | '*' | '/' | '%' | '='
# <num> ::= [ '0' - '9' ]+
# <id> ::= [ '_', 'a' - 'z', 'A' - 'Z'][ '_', 'a' - 'z', 'A' - 'Z', '0' -'9' ]*

try:
    from pypy.rlib.jit import elidable, promote
except ImportError:
    def promote(arg):
        pass

class Func:
    def __init__(self, name, argName, body):
        self.name=name # Id
        self.argName=argName # Id
        self.body=body # ifF1WAE

class NoneFunc(Func):
    """Useful for GetFunc in Interpreter"""
    
    def __init__(self):
        pass

class ifF1WAE:
    def __init__(self):
        pass
        
class Node(ifF1WAE):
    def __init__(self):
        pass

class Leaf(ifF1WAE):
    def __init__(self):
        pass

class Num(Leaf):
    _immutable_fields_ = ["n"]

    def __init__(self, n):
        self.n=n # Int

class Id(Leaf):
    _immutable_fields_ = ["name"]
    def __init__(self, name):
        self.name=name # Id

class Op(Node):
    _immutable_fields_ = ["op", "lhs", "rhs"]
    def __init__(self, op, lhs, rhs):
        self.op=op # Op
        self.lhs=lhs # ifF1WAE
        self.rhs=rhs # ifF1WAE

class With(Node):
    _immutable_fields_ = ["name", "nameExpr", "body"]
    def __init__(self, name, nameExpr, body):
        self.name=name # Id
        self.nameExpr=nameExpr # ifF1WAE
        self.body=body # ifF1WAE

class App(Node):
    _immutable_fields_ = ["funName", "arg"]
    def __init__(self, funName, arg):
        self.funName=funName # Id, name of a function
        self.arg=arg # ifF1WAE

class If(Node):
    _immutable_fields_ = ["cond", "ctrue", "cfalse"]
    def __init__(self, cond, ctrue, cfalse):
        self.cond=cond # Condition
        self.ctrue=ctrue # If condition is true
        self.cfalse=cfalse #If condition is false
        
def treePrint(tree):
    """ Pretty printing a tree """

    if isinstance(tree, Num):
        return("Num " + str(tree.n))
        
    elif isinstance(tree, Id):
        return("Id " + tree.name)

    elif isinstance(tree, Op):
        return("Op " + str(tree.op))

    elif isinstance(tree, With):
        return("With " + tree.name)

    elif isinstance(tree, App):
        return("App "+ tree.funName)

    elif isinstance(tree, If):
        return("If "+ treePrint(tree.cond))

    else:
        return("Not a ifF1WAE!")
        
#####################
# Map and Env Class #
#####################

class Map(object):
    def __init__(self):
        self.indexes = {}
        self.other_maps = {}

    @elidable
    def getindex(self, name):
        return self.indexes.get(name, -1)

    @elidable
    def add_attribute(self, name):
        if name not in self.other_maps:
            newmap = Map()
            newmap.indexes.update(self.indexes)
            newmap.indexes[name] = len(self.indexes)
            self.other_maps[name] = newmap
        return self.other_maps[name]

EMPTY_MAP = Map()

class Env(object):
    def __init__(self):
        self.map = EMPTY_MAP
        self.storage = []
        
    def get_attr(self, name):
        map = self.map
        promote(map)
        index = map.getindex(name)
        if index != -1:
            return self.storage[index]
        else:
            print("Free variable : " + name)
            return 2

    def write_attribute(self, name, value):
        assert isinstance(name, str)
        assert isinstance(value, int)
        map = self.map
        promote(map)
        index = map.getindex(name)
        if index != -1:
            self.storage[index] = value
            return
        self.map = map.add_attribute(name)
        self.storage.append(value)
        