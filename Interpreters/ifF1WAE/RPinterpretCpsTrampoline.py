import treeClass
import parser
import sys

##########################
# Class Function for CPS #
##########################

class Funck:
    def __init__(self):
        pass
    
    def apply(self,arg):
        return ExpVal(arg)

class Idk(Funck):
    def __init__(self):
        pass
    
    def apply(self,arg):
        return ExpVal(arg)

class Opk(Funck):
    def __init__(self,argLeft,op,k):
        self.argLeft=argLeft
        self.op=op
        self.k=k


    def apply(self,arg):
        if self.op == '+':
            return self.k.apply(self.argLeft + arg)
        elif self.op == '-':
            return self.k.apply(self.argLeft - arg)
        elif self.op == '*':
            return self.k.apply(self.argLeft * arg)
        elif self.op == '/':
            return self.k.apply(self.argLeft / arg)
        elif self.op == '%':
            return self.k.apply(self.argLeft % arg)
        elif self.op == '=':
            if self.argLeft - arg == 0:
                return self.k.apply(1)
            else:
                return self.k.apply(0)
        else:
            print("Parsing Error, symobl "+ self.op +" shouldn't be here.")
            return ExpVal(2)

class OpLeftk(Funck):
    def __init__(self, exprRight, funDict, env, k, op):
        self.exprRight=exprRight
        self.funDict=funDict
        self.env=env
        self.k=k
        self.op=op

    def apply(self, arg):
        return Interpk(self.exprRight,self.funDict,self.env, Opk(arg,self.op,self.k))

class Appk(Funck):
    def __init__(self, funName, funDict, k):
        self.funName=funName
        self.funDict=funDict
        self.k=k

    def apply(self, arg):
        if self.funName in self.funDict.keys():
            g=self.funDict[self.funName]
            return Interpk(g.body,self.funDict, {g.argName: arg}, self.k)
        else:
            print("Invalid function : " + self.funName)
            return ExpVal(2)

class Ifk(Funck):
    def __init__(self, true, false, funDict, env, k):
        self.true=true
        self.false=false
        self.funDict=funDict
        self.env=env
        self.k=k

    def apply(self,arg):
        if arg != 0:
            return Interpk(self.true, self.funDict, self.env, self.k)
        else:
            return Interpk(self.false, self.funDict, self.env, self.k)


#####################
# Bounce Definition #
#####################

class Bounce:
    def __init__(self):
        pass

class ExpVal(Bounce):
    def __init__(self,val):
        self.val=val

class BounceFun(Bounce):
    def __init__(self,arg,funDict,env,funName,k):
        self.arg=arg
        self.funDict=funDict
        self.env=env
        self.funName=funName
        self.k=k
        
    def bounce(self):
        return Interpk(self.arg, self.funDict, self.env, Appk(self.funName, self.funDict, self.k))


#############################    
#Interpret CPS - Trampoline #
#############################

def Interpk(tree, funDict, env,k):
    """ Interpret the F1WAE AST given a set of defined functions. We use deferred substituion and eagerness."""

    #
    if isinstance(tree, treeClass.Num):
        return k.apply(tree.n)
    #
    elif isinstance(tree, treeClass.Op):
        k2 = OpLeftk(tree.rhs, funDict, env, k, tree.op)
        return Interpk(tree.lhs, funDict, env, k2)
    #
    elif isinstance(tree, treeClass.With):
        
        val = (Interpk(tree.nameExpr, funDict, env, Idk()))
        while isinstance(val, BounceFun):
            val2 = val.bounce()
        if isinstance(val,ExpVal):
            val2 = val.val
        else:
            print("Not a bounce!")
            val2 = 2
        env[tree.name] = val2 #Eager
        return Interpk(tree.body, funDict, env, k)
    #
    elif isinstance(tree, treeClass.Id):
        if tree.name in env.keys():
            return k.apply(env[tree.name])
        else:
            print("Interpret Error: free identifier :\n" + tree.name)
            return k.apply(2)
    #
    elif isinstance(tree, treeClass.App):
        return BounceFun(tree.arg, funDict, env, tree.funName, k)
    #
    elif isinstance(tree, treeClass.If):
        return Interpk(tree.cond,funDict,env,Ifk(tree.ctrue,tree.cfalse,funDict,env,k))
    #
    else: # Not an <F1WAE>
        print("Argument of Interpk is not a <F1WAE>:\n")
        return k.apply(2)
    #


def Main(file):
    t,d = parser.Parse(file)
    bou = Interpk(t,d,{},Idk())
    while isinstance(bou,BounceFun):
        bou = bou.bounce()
    if isinstance(bou,ExpVal):
        j=bou.val
        print("the answer is :" + str(j))
    else:
        print("Not a bounce!")

import os

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
