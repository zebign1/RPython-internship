import parser

from pypy.rlib.jit import JitDriver, elidable, promote, set_param

#######################################
# Map for environement representation #
#######################################

class Map(object):
    _immutable_fields_=['values']
    def __init__(self):
        self.values = {}

    @elidable
    def getvalue(self, name):
        return self.values.get(name, ErrorV("Free variable : %s" % name))

    @elidable
    def add_attribute(self, name, value):
        newmap = Map()
        newmap.values.update(self.values)
        newmap.values[name] = value
        return newmap

    def __str__(self):
        str = "Map : \n"
        for i in self.values.keys():
            str += "(\n %s, \n %s\n)\n" % (i,(self.values[i].__str__()))
        return str

###############
# Return type #
###############

class ReturnType(object):
    """ Class of objects returned by the Interpret function.
    For Inheritance."""

    def __init__(self):
        pass

    def __str__(self):
        pass

class ErrorV(ReturnType):
    """ In case an error occurs """

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

class NumV(ReturnType):

    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)

    def add(self, other):
        return NumV(self.val + other.val)

    def diff(self, other):
        return NumV(self.val - other.val)

    def mult(self, other):
        return NumV(self.val * other.val)

    def div(self, other):
        return NumV(self.val / other.val)

    def mod(self, other):
        return NumV(self.val % other.val)


def assertNumV(expr, tree):
    """ Assert class of expr is NumV, else blame tree."""
    
    if not isinstance(expr, NumV):
        return "Wrong return type for expression :\n %s\n Should be of type NumV." % tree.__str__()
    else:
        return "True"

class ClosureV(ReturnType):

    def __init__(self, arg, body, env):
        self.arg = arg
        self.body = body
        self.env = env

    def __str__(self):
        return "(fun : %s |-> %s)" % (self.arg.__str__(), self.body.__str__())

def assertClosureV(expr, tree):
    """ Assert class of expr is ClosureV, else blame tree."""
    
    if not isinstance(expr, ClosureV):
        return "Wrong return type for expression :\n %s\n Should be of type ClosureV." % tree.__str__()
    else:
        return "True"

#################
# Continuations #
#################

class Continuation(object):
    """ Super class, for inheritance purpose only."""

    def __init__(self):
        pass

class FinalK(Continuation):
    """To get out of the loop"""
    
    def __init__(self):
        pass

    def _apply(self, reg, tree, env, k):
        return reg, tree, env, FinalK()

class EndK(Continuation):

    def __init__(self):
        pass

    def _apply(self, reg, tree, env, k):
        return reg, tree, env, FinalK()

class Op1K(Continuation):

    def __init__(self, op, lhs, rhs, env, k):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs
        self.env = env
        self.k = k

    def _apply(self, reg, tree, env, k):
        # reg is expected to be interpretation of lhs
        Lhs = reg
        msg = assertNumV(Lhs, self.lhs)
        if msg != "True":
            return ErrorV(msg), tree, env, FinalK()
        k = Op2K(Lhs, self.op, self.rhs, self.k)
        return reg, self.rhs, self.env, k

class Op2K(Continuation):

    def __init__(self, Lhs, op, rhs, k):
        self.Lhs = Lhs
        self.op = op
        self.rhs = rhs
        self.k = k

    def _apply(self, reg, tree, env, k):
        # reg is expected to be interpretation of rhs
        Rhs = reg
        msg = assertNumV(Rhs, self.rhs)
        if msg != "True":
            return ErrorV(msg), tree, env, FinalK()

        if self.op == '+':
            return self.k._apply(self.Lhs.add(Rhs), tree, env, k)
        elif self.op == '-':
            return self.k._apply(self.Lhs.diff(Rhs), tree, env, k)
        elif self.op == '*':
            return self.k._apply(self.Lhs.mult(Rhs), tree, env, k)
        elif self.op == '/':
            return self.k._apply(self.Lhs.div(Rhs), tree, env, k)
        elif self.op == '%':
            return self.k._apply(self.Lhs.mod(Rhs), tree, env, k)
        else:
            msg = "Parsing error, operator %s not valid" % self.op
            return ErrorV(msg), tree, env, FinalK()

class If0K(Continuation):

    def __init__(self, nul, true, false, env, k):
        self.nul = nul
        self.true = true
        self.false = false
        self.env = env
        self.k = k

    def _apply(self, reg, tree, env, k):
        #reg is expected to be the interpratation of nul
        nul = reg
        msg = assertNumV(nul, self.nul)
        if msg  != "True":
            return ErrorV(msg), tree, env, FinalK() 
        if nul.val == 0:
            return reg, self.true, self.env, self.k
        else:
            return reg, self.false, self.env, self.k

class App1K(Continuation):

    def __init__(self, fun, env, k):
        self.fun = fun
        self.env = env
        self.k = k

    def _apply(self, reg, tree, env, k):
        # reg is expected to be the interpretation of arg
        arg = reg
        newK = App2K(self.fun, arg, self.k)
        return arg, self.fun, self.env, newK

class App2K(Continuation):

    def __init__(self, fun, arg, k):
        self.fun = fun
        self.arg = arg
        self.k = k

    def _apply(self, reg, tree, env, k):
        # reg is expected to be the interpretation of fun
        fun = reg
        msg = assertClosureV(fun, self.fun)
        if msg != "True":
            return ErrorV(msg), tree, env, FinalK()
        param = fun.arg
        assert isinstance(param, parser.Id)
        newEnv = fun.env
        promote(newEnv)
        newEnv = newEnv.add_attribute(param.name, self.arg)
        return fun, fun.body, newEnv, self.k
        

class RecK(Continuation):

    def __init__(self, funName, body, expr, k):
        self.funName = funName
        self.body = body
        self.expr = expr
        self.k = k

    def _apply(self, reg, tree, env, k):
        # reg is suppose to be te interpretation of fun
        funDef = reg
        msg = assertClosureV(funDef, self.body)
        if msg != "True":
            return ErrorV(msg), tree, env, FinalK()
        newEnv = funDef.env
        promote(newEnv)
        funDef.env = newEnv.add_attribute(self.funName, funDef)
        return funDef, self.expr, funDef.env, self.k

###############
# Interpreter #
###############

# JITing instructions

def get_printable_location(tree):
    return tree.printable()

jitdriver = JitDriver(greens=['tree'], reds=['env', 'k', 'register'], get_printable_location=get_printable_location)

def Interpret(tree):
    """Interpret the tree, iteratively."""

    set_param(jitdriver, "trace_limit", 25000)

    register = ReturnType()
    tree = tree
    env = Map()
    k = EndK()

    while 1:
        jitdriver.jit_merge_point(tree=tree, env=env, k=k, register=register)

        if isinstance(k, FinalK):
            break

        if isinstance(tree, parser.Num):
            register, tree, env, k = k._apply(NumV(tree.val), tree, env, k)

        elif isinstance(tree, parser.Op):
            k = Op1K(tree.op, tree.lhs, tree.rhs, env, k)
            tree = tree.lhs

        elif isinstance(tree, parser.Id):
            promote(env)
            register = env.getvalue(tree.name)
            if isinstance(register, ErrorV):
                k = FinalK()
            else:
                register, tree, env, k = k._apply(register, tree, env, k)

        elif isinstance(tree, parser.If):
            k = If0K(tree.nul, tree.true, tree.false, env, k)
            tree = tree.nul

        elif isinstance(tree, parser.Func):
            assert isinstance(tree.arg, parser.Id)
            register, tree, env, k = k._apply(ClosureV(tree.arg, tree.body, env), tree, env, k)

        elif isinstance(tree, parser.App):
            k = App1K(tree.fun, env, k)
            tree = tree.arg
            jitdriver.can_enter_jit(tree=tree, env=env, k=k, register=register)

        elif isinstance(tree, parser.Rec):
            k = RecK(tree.funName, tree.body, tree.expr, k)
            dummy = NumV(42)
            promote(env)
            env = env.add_attribute(tree.funName, dummy)
            tree = tree.body

        else:
            msg = "Parsing error, tree %s is not valid" % tree.__str__()
            register = ErrorV(msg)
            k = FinalK()

    return register


#####################            
# Main instructions #
#####################

def Main(source):
    """Main function."""
    
    tree = parser._parse(source)
    transforme = parser.Transformer()
    ourTree = transforme.visitRCFAE(tree)
    #    print ourTree.__str__()
    answer = Interpret(ourTree)
    print answer.__str__()

import os

def jitpolicy(driver):
    from pypy.jit.codewriter.policy import JitPolicy
    return JitPolicy()

def run(fp):
    program_envents = ""
    while True:
        read = os.read(fp, 4096)
        if len(read) == 0:
            break
        program_envents += read
    os.close(fp)
    Main(program_envents)

def entry_point(argv):
    try:
        filename = argv[1]
    except IndexError:
        print "You must supply a filename"
        return 1

    run(os.open(filename, os.O_RDONLY, 0777))
    return 0


def target(*args):
    return entry_point, None

if __name__ == "__main__":
    entry_point(sys.argv)
