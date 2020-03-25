"""Expressions (for a calculator)
M Young, January 2019
Revised March 2019 for compiler project;
Revised May 2019 to add comparison operations
"""

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Global variable NO_VALUE is defined below after IntConst

# One global environment (scope) for
# the calculator
from codegen_context import Context

ENV = dict()

def env_clear():
    """Clear all variables in calculator memory"""
    global ENV
    ENV = dict()


class UndefinedVariable(Exception):
    """Raised when expression tries to use a variable that
    is not in ENV
    """
    pass


class Expr(object):
    """Abstract base class of all expressions."""

    def eval(self) -> "IntConst":
        """Implementations of eval should return an integer constant."""
        raise NotImplementedError("Each concrete Expr class must define 'eval'")

    def __str__(self) -> str:
        """Implementations of __str__ should return the expression in algebraic notation"""
        raise NotImplementedError("Each concrete Expr class must define __str__")

    def __repr__(self) -> str:
        """Implementations of __repr__ should return a string that looks like
        the constructor, e.g., Plus(IntConst(5), IntConst(4))
        """
        raise NotImplementedError(f"Class {self.__class__.__name__} doesn't define __repr__")

    def __eq__(self, other: "Expr") -> bool:
        raise NotImplementedError("__eq__ method not defined for class")



class IntConst(Expr):
    def __init__(self, value: int):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"IntConst({self.value})"

    def eval(self) -> "IntConst":
        return self

    def __eq__(self, other: Expr):
        return isinstance(other, IntConst) and self.value == other.eval().value

    def gen(self, context: Context, target: str):
        """Generate code into the context object.
        Result of expression evaluation will be
        left in target register.
        """
        label = context.get_const_symbol(self.value)
        context.add_line(f"    LOAD {target},{label}")
        return




# Globals should normally go at the beginning of the file, but we needed
# IntConst to define this one.
NO_VALUE = IntConst(7777)  # Just an unlikely value to get randomly


class BinOp(Expr):
    """Abstract base class for binary operators +, *, /, -"""

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def eval(self) -> "IntConst":
        """Each concrete subclass must define _apply(int, int)->int"""
        left_val = self.left.eval()
        right_val = self.right.eval()
        return IntConst(self._apply(left_val.value, right_val.value))

    def __str__(self) -> str:
        """Implementations of __str__ should return the expression in algebraic notation"""
        return f"({str(self.left)} {self.opsym} {str(self.right)})"

    def __repr__(self) -> str:
        """Implementations of __repr__ should return a string that looks like
        the constructor, e.g., Plus(IntConst(5), IntConst(4))
        """
        return f"{self.__class__.__name__}({repr(self.left)}, {repr(self.right)})"

    def __eq__(self, other: "Expr") -> bool:
        return type(self) == type(other) and  \
            self.left == other.left and \
            self.right == other.right

    def _opcode(self) -> str:
        """Which operation code do we use in the generated assembly code?"""
        raise NotImplementedError("Each binary operator should define the _opcode method")

    def gen(self, context: Context, target: str):
        self.left.gen(context, target)
        reg = context.allocate_register()
        self.right.gen(context, reg)
        context.add_line(f"   {self._opcode()}  {target},{target},{reg}")
        context.free_register(reg)


class Plus(BinOp):
    """left + right"""

    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right)
        self.opsym = "+"

    def _apply(self, left: int, right: int) -> int:
        return left + right

    def _opcode(self) -> str:
        return "ADD"


class Minus(BinOp):
    """left - right"""

    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right)
        self.opsym = "-"

    def _apply(self, left: int, right: int) -> int:
        return left - right

    def _opcode(self) -> str:
        return "SUB"


class Times(BinOp):
    """left * right"""

    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right)
        self.opsym = "*"

    def _apply(self, left: int, right: int) -> int:
        return left * right

    def _opcode(self) -> str:
        return "MUL"


class Div(BinOp):
    """left // right"""

    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right)
        self.opsym = "/"

    def _apply(self, left: int, right: int) -> int:
        return left // right

    def _opcode(self) -> str:
        return "DIV"


class UnOp(Expr):
    """Abstract base class for unary operators ~, @"""

    def __init__(self, left: Expr):
        self.left = left

    def eval(self) -> "IntConst":
        """Each concrete subclass must define _apply(int, int)->int"""
        left_val = self.left.eval()
        return IntConst(self._apply(left_val.value))

    def __str__(self) -> str:
        """Implementations of __str__ should return the expression in algebraic notation"""
        return f"({self.opsym}{str(self.left)})"

    def __repr__(self) -> str:
        """Implementations of __repr__ should return a string that looks like
        the constructor, e.g., Plus(IntConst(5), IntConst(4))
        """
        return f"{self.__class__.__name__}({repr(self.left)})"

    def __eq__(self, other: "Expr") -> bool:
        return type(self) == type(other) and  \
            self.left == other.left


class Neg(UnOp):
    """~left"""

    def __init__(self, left: Expr):
        super().__init__(left)
        self.opsym = "~"

    def _apply(self, left: int) -> int:
        return 0 - left

    def gen(self, context: Context, target: str):
        self.left.gen(context, target)
        context.add_line(f"    SUB {target},r0,{target}  # Flip the sign")


class Abs(UnOp):
    """Absolute value, represented as @"""

    def __init__(self, left: Expr):
        super().__init__(left)
        self.opsym = "@"

    def _apply(self, left: int) -> int:
        return abs(left)

    def gen(self, context: Context, target: str):
        self.left.gen(context, target)
        pos = context.new_label("already_positive")
        context.add_line(f"    SUB  r0,{target},r0  # <Abs>")
        context.add_line(f"    JUMP/PZ {pos}")
        context.add_line(f"    SUB {target},r0,{target}  # Flip the sign")
        context.add_line(f"{pos}:   # </Abs>")


class Var(Expr):

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Var({self.name})"

    def eval(self):
        global ENV
        if self.name in ENV:
            return ENV[self.name]
        else:
            raise UndefinedVariable(f"{self.name} has not been assigned a value")

    def assign(self, value: IntConst):
        ENV[self.name] = value

    def lvalue(self, context: Context) -> str:
        """Return the label that the compiler will use for this variable"""
        return context.get_var_symbol(self.name)

    def gen(self, context: Context, target: str):
        """Generate code into the context object.
        Result of expression evaluation will be
        left in target register.
        """
        label = context.get_var_symbol(self.name)
        context.add_line(f"    LOAD {target},{label}")
        return


class Assign(Expr):
    """Assignment:  x = E represented as Assign(x, E)"""

    def __init__(self, left: Var, right: Expr):
        assert isinstance(left, Var)  # Can only assign to variables!
        self.left = left
        self.right = right

    def __str__(self) -> str:
        return f"{self.left} = {self.right}"

    def __repr__(self) -> str:
        return f"Assign({repr(self.left)}, {repr(self.right)})"

    def eval(self) -> IntConst:
        r_val = self.right.eval()
        self.left.assign(r_val)
        return r_val

    def gen(self, context: Context, target: str):
        """Store value of expression into variable"""
        loc = self.left.lvalue(context)
        self.right.gen(context, target)
        context.add_line(f"   STORE  {target},{loc}")


class Control(Expr):
    """Control flow nodes (while, if, ...).
    Control flow constructs have one or more blocks of statements
    and may have a controlling predicate.  For predicates,
    we take zero as false, and any other value as true.
    Control constructs don't have actual values (they would be 'None'
    in Python and 'void' in C or C++), so we return 0
    from eval.
    """
    pass
    # Note PyCharm will complain that Control doesn't implement all
    # abstract methods, but that's because Control is itself an
    # abstract base class ... the abstract methods should be implemented
    # in its subclasses.


class Seq(Control):
    """exp ; exp"""

    def __init__(self, left, right):
        """ exp ; exp """
        self.left = left
        self.right = right

    def __str__(self):
        return f"{{\n{self.left}\n{self.right} }}"

    def __repr__(self):
        return f"Seq({repr(self.left)}, {repr(self.right)}"

    def eval(self) -> IntConst:
        """Just evaluate in order"""
        discard = self.left.eval()
        return self.right.eval()

    def gen(self, context: Context, target: str):
        """ #FIXME """
        self.left.gen(context, target)
        self.left.eval()

        self.right.gen(context, target)
        self.right.eval()







class Print(Control):
    """Print a value.  Returns the value."""

    def __init__(self, expr: Expr):
        """Print e"""
        self.expr = expr

    def __str__(self):
        return f"print {self.expr};"

    def __repr__(self):
        return f"Print({repr(self.expr)})"

    def eval(self) -> IntConst:
        result = self.expr.eval()
        print(f"Quack!: {result.value}")
        return result

    def gen(self, context: Context, target: str):
        """We print by storing to the memory-mapped address 511"""
        self.expr.gen(context, target)
        context.add_line(f"   STORE  {target},r0,r0[511]")


class Read(Expr):
    """Read a value from input"""

    def __init__(self):
        pass

    def __str__(self):
        return "(read)"

    def __repr__(self):
        return "Read()"

    def eval(self) -> IntConst:
        val = input("Quack! Gimme an int! ")
        return IntConst(int(val))

    def gen(self, context: Context, target: str):
        """Get value from input by loading instruction from memory address 510"""
        self.expr.eval()
        context.add_line(f"   LOAD  {target},r0,r0[510]")


class Comparison(Control):
    """A relational operation that may yield 'true' or 'false',
    In the interpreter, relational operators ==, >=, etc
    return an integer 0 for False or 1 for True, and the "if" and "while"
    constructs use that value.
    In the compiler, "if" and "while" delegate that branching
    to the relational construct, i.e., x < y does not create
    a value in a register but rather causes a jump if y - x
    is positive.  Condition code is the condition code for
    the conditional JUMP after a subtraction, e.g., Z for
    equality, P for >, PZ for >=.
    For each comparison, we give two condition codes: One if
    we want to branch when the condition is true, and another
    if we want to branch when the condition is false.
    (Currently the compiler only uses the cond_code_false
    conditions, because it is jumping to the 'else' branch
    or out of the loop.)
    """
    def __init__(self, left: Expr, right: Expr,
                 opsym: str, cond_code_true: str, cond_code_false: str):
        self.left = left
        self.right = right
        self.opsym = opsym
        self.cond_code_true = cond_code_true
        self.cond_code_false = cond_code_false

    def __str__(self) -> str:
        return f"{str(self.left)} {self.opsym} {str(self.right)}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.left)}, {repr(self.right)})"

    def __eq__(self, other: "Expr") -> bool:
        return type(self) == type(other) and  \
            self.left == other.left and \
            self.right == other.right

    def eval(self) -> "IntConst":
        """In the interpreter, relations return 0 or 1.
        Each concrete subclass must define _apply(int, int)->int
        """
        left_val = self.left.eval()
        right_val = self.right.eval()
        return IntConst(self._apply(left_val.value, right_val.value))

    def gen(self, context: Context, target: str):
        """We don't support using relational operators to
        produce a value (although it would be easy to add).
        """
        raise NotImplementedError("Relational operators do not support 'gen'; try 'condjump'")

    def condjump(self, context: Context, target: str, label: str, jump_cond: bool = True):
        """Generate jump to label conditional on relation. """
        self.left.gen(context, target)
        reg = context.allocate_register()
        self.right.gen(context, reg)
        if jump_cond:
            cond = self.cond_code_true
        else:
            cond = self.cond_code_false
        # All relations are implemented by subtraction.  What varies is
        # the condition code controlling the jump.
        context.add_line(f"   SUB  r0,{target},{reg}")
        context.add_line(f"   JUMP/{cond}  {label}  #{self.opsym}")
        context.free_register(reg)


class EQ(Comparison):
    """left == right"""

    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right, "==", "Z", "PM")

    def _apply(self, left: int, right: int) -> int:
        return 1 if left == right else 0

class NE(Comparison):
    """left != right"""
    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right, "!=", "PM", "Z")

    def _apply(self, left: int, right: int) -> int:
        return 1 if left != right else 0

class GT(Comparison):
    """left > right"""
    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right, ">", "P", "ZM")

    def _apply(self, left: int, right: int) -> int:
        return 1 if left > right else 0

class GE(Comparison):
    """left >= right"""
    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right, ">=", "PZ", "M")

    def _apply(self, left: int, right: int) -> int:
        return 1 if left >= right else 0

class LT(Comparison):
    """left < right"""
    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right, "<", "M", "PZ")

    def _apply(self, left: int, right: int) -> int:
        return 1 if left < right else 0

class LE(Comparison):
    """left <= right"""
    def __init__(self, left: Expr, right: Expr):
        super().__init__(left, right, "<=", "MZ", "P")

    def _apply(self, left: int, right: int) -> int:
        return 1 if left <= right else 0


class While(Control):
    """Classic while loop."""

    def __init__(self, cond: Comparison, expr: Expr):
        """While cond do expr"""
        self.cond = cond
        self.expr = expr

    def __str__(self):
        return f"while {self.cond} do\n{self.expr}\nod"

    def __repr__(self):
        return f"While({repr(self.cond)}, {repr(self.expr)})"

    def eval(self) -> IntConst:
        """
        Repeat 'expr' part while 'cond' part evaluates to a non-zero
        value.  Returns value of last statement executed.
        """
        last = NO_VALUE
        cond_val = self.cond.eval()
        while cond_val.value != 0:
            last = self.expr.eval()
            cond_val = self.cond.eval()
        return last

    def gen(self, context: Context, target: str):
        """Looping"""
        loop_head = context.new_label("while_do")
        loop_exit = context.new_label("od")
        context.add_line(f"{loop_head}:")
        self.cond.condjump(context, target, loop_exit, jump_cond=False)
        self.expr.gen(context, target)
        context.add_line(f"   JUMP  {loop_head}")
        context.add_line(f"{loop_exit}:")


class Pass(Control):
    """
    The 'else' part of an 'if' statement is optional.  This node
    is a stand-in for the empty block ... it does nothing.
    """

    def __init__(self):
        """La la la la la I can't hear you"""
        return

    def __repr__(self):
        return "pass"

    def __str__(self):
        return "pass"

    def eval(self) -> IntConst:
        """Does nothing, has no value."""
        return NO_VALUE

    def gen(self, context: Context, target: str):
        pass


class If(Control):
    """If with optional Else (no elif)"""

    def __init__(self, cond, thenpart, elsepart=Pass()):
        """if cond then block else block fi"""
        self.cond = cond
        self.thenpart = thenpart
        self.elsepart = elsepart

    def __str__(self):
        return "if {} then\n{}\nelse\n{}\nfi".format(self.cond, self.thenpart, self.elsepart)

    def __repr__(self):
        return f"If({repr((self.cond))}, {repr(self.thenpart)}, {repr(self.elsepart)})"

    def eval(self) -> IntConst:
        """If statement.  Returns nothing. """
        cond_value = self.cond.eval()
        if cond_value.value != 0:
            result = self.thenpart.eval()
        else:
            result = self.elsepart.eval()
        return result

    def gen(self, context: Context, target: str):

        predicate = context.new_label("if")
        self.cond.condjump(context, target, predicate, jump_cond=False)
        otherwise = context.new_label("else")
        context.add_line(f"{predicate}")
        #self.cond.gen(context, target)
        execute = context.new_label("fi")
        context.add_line(f"   JUMP  {execute}")










