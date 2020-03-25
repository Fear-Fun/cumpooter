"""Test Codegen:
Simple unit tests for parts of our code generator.
More complete tests will require us to go through the
whole cycle of compiling a Mallard program, assembling the
generated assembly code, and executing the resulting
object code on our Duck Machine simulator.  The test
cases here just catch some bugs in the pieces as we
build up the full code generator.
"""

import unittest
from expr import *
from codegen_context import Context
from typing import List, Union


def squish(s: str) -> str:
    """Discard initial and final spaces and compress
    all other runs of whitespace to a single space,
    """
    parts = s.strip().split()
    return " ".join(parts)

def crush(text: Union[str, List[str]]) -> List[str]:
    """Whether given a single multi-line string or a
    list of strings (each being one line of text),
    'crush' returns a list of squished lines.
    """
    # If it's a single multi-line string, break
    # it into lines
    if isinstance(text, str):
        lines = text.split("\n")
    else:
        # If it's not a string, it better be a list of strings
        assert isinstance(text, list)
        lines = text
    squished = [squish(l) for l in lines]
    crushed = [l for l in squished if len(l) > 0]
    return crushed

class AsmTestCase(unittest.TestCase):

    def codeEqual(self, generated: List[str], expected: str) -> bool:
        gen = crush(generated)
        exp = crush(expected)
        self.assertEqual(len(gen), len(exp))
        for i in range(len(gen)):
            self.assertEqual(gen[i], exp[i])


# test cases will go here.
class Test_IntConst_Gen(AsmTestCase):
    """Generating code for an IntConst"""

    def test_42(self):
        const = IntConst(42)
        context = Context()
        const.gen(context, "r12")
        expected = """
             LOAD  r12,const_42
        const_42:  DATA 42
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_42n(self):
        const = IntConst(-42)
        context = Context()
        const.gen(context, "r12")
        expected = """
             LOAD  r12,const_n_42
        const_n_42:  DATA -42
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


class Test_Var_Gen(AsmTestCase):
    "Generating code for Variable reference (rvalue)"

    def test_var(self):
        var = Var("silly")
        context = Context()
        var.gen(context, "r8")
        expected = """
              LOAD  r8,var_silly
         var_silly:  DATA 0
         """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

class Test_Assign_Gen(AsmTestCase):
    "Generating code for Variable reference (rvalue)"

    def test_assign(self):
        context = Context()
        assignment = Assign(Var("universe"), IntConst(42))
        assignment.gen(context, "r5")
        expected = """
              LOAD  r5,const_42
              STORE r5,var_universe
         const_42: DATA 42
         var_universe: DATA 0
         """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


class Test_Binops_Gen(AsmTestCase):
    """A simple shakedown of each binary operation"""

    def test_plus_gen(self):
        context = Context()
        target = context.allocate_register()
        e = Plus(Var("x"), IntConst(3))
        e.gen(context, target)
        expected = """
        LOAD r14,var_x
        LOAD r13,const_3
        ADD  r14,r14,r13
        const_3: DATA 3
        var_x:   DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_minus_gen(self):
        context = Context()
        target = context.allocate_register()
        e = Minus(Var("x"), IntConst(3))
        e.gen(context, target)
        expected = """
        LOAD r14,var_x
        LOAD r13,const_3
        SUB  r14,r14,r13
        const_3: DATA 3
        var_x:   DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_times_gen(self):
        context = Context()
        target = context.allocate_register()
        e = Times(Var("x"), IntConst(3))
        e.gen(context, target)
        expected = """
        LOAD r14,var_x
        LOAD r13,const_3
        MUL  r14,r14,r13
        const_3: DATA 3
        var_x:   DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


    def test_div_gen(self):
        context = Context()
        target = context.allocate_register()
        e = Div(Var("x"), IntConst(3))
        e.gen(context, target)
        expected = """
        LOAD r14,var_x
        LOAD r13,const_3
        DIV  r14,r14,r13
        const_3: DATA 3
        var_x:   DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_binop_combo(self):
        """Combining the operations involves some register
        management.
        """
        e = Plus(Times(Var("x"), Var("y")), Minus(IntConst(2), IntConst(3)))
        context = Context()
        target = context.allocate_register()
        e.gen(context, target)
        expected = """
        LOAD r14,var_x
        LOAD r13,var_y
        MUL r14,r14,r13
        LOAD r13,const_2
        LOAD r12,const_3
        SUB r13,r13,r12
        ADD r14,r14,r13
        const_2: DATA 2
        const_3: DATA 3
        var_x: DATA 0
        var_y: DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


class Test_Unops_Gen(AsmTestCase):
    """Unary operations Neg and Abs"""

    def test_neg_gen(self):
        context = Context()
        target = context.allocate_register()
        e = Neg(IntConst(8))
        e.gen(context, target)
        expected = """
        LOAD r14,const_8
        SUB  r14,r0,r14 # Flip the sign 
        const_8: DATA 8
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


    def test_abs_gen(self):
        context = Context()
        target = context.allocate_register()
        e = Abs(IntConst(-3))
        e.gen(context, target)
        expected = """
        LOAD r14,const_n_3
        SUB  r0,r14,r0  # <Abs>
        JUMP/PZ already_positive_1
        SUB r14,r0,r14  # Flip the sign
        already_positive_1:   # </Abs>
        const_n_3:  DATA -3
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


class Test_Condjump(AsmTestCase):

    def test_EQ_iftrue(self):
        """==, jump if true"""
        context = Context()
        target = context.allocate_register()
        e = EQ(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_true")
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/Z  here_if_true #==
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_EQ_iffalse(self):
        """==, jump if false"""
        context = Context()
        target = context.allocate_register()
        e = EQ(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_false", jump_cond=False)
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/PM  here_if_false #==
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_NE_iftrue(self):
        """!=, jump if true"""
        context = Context()
        target = context.allocate_register()
        e = NE(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_true")
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/PM  here_if_true #!=
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_NE_iffalse(self):
        """!=, jump if false"""
        context = Context()
        target = context.allocate_register()
        e = NE(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_false", jump_cond=False)
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/Z  here_if_false #!=
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_GT_iftrue(self):
        """>, jump if true"""
        context = Context()
        target = context.allocate_register()
        e = GT(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_true")
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/P  here_if_true #>
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_GT_iffalse(self):
        """>, jump if false"""
        context = Context()
        target = context.allocate_register()
        e = GT(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_false", jump_cond=False)
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/ZM  here_if_false #>
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_GE_iftrue(self):
        """>=, jump if true"""
        context = Context()
        target = context.allocate_register()
        e = GE(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_true")
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/PZ  here_if_true #>=
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_GE_iffalse(self):
        """>=, jump if false"""
        context = Context()
        target = context.allocate_register()
        e = GE(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_false", jump_cond=False)
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/M  here_if_false #>=
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_LT_iftrue(self):
        """<, jump if true"""
        context = Context()
        target = context.allocate_register()
        e = LT(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_true")
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/M  here_if_true #<
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_LT_iffalse(self):
        """>=, jump if false"""
        context = Context()
        target = context.allocate_register()
        e = LT(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_false", jump_cond=False)
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/PZ  here_if_false #<
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_LE_iftrue(self):
        """<=, jump if true"""
        context = Context()
        target = context.allocate_register()
        e = LE(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_true")
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/MZ  here_if_true #<=
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)

    def test_LE_iffalse(self):
        """>=, jump if false"""
        context = Context()
        target = context.allocate_register()
        e = LE(IntConst(3), IntConst(5))
        e.condjump(context, target, "here_if_false", jump_cond=False)
        expected = """
        LOAD  r14,const_3
        LOAD  r13,const_5
        SUB   r0,r14,r13
        JUMP/P  here_if_false #<=
        const_3: DATA 3
        const_5: DATA 5
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


class Test_While_Gen(AsmTestCase):

    def test_while_gen(self):
        context = Context()
        target = context.allocate_register()
        e = While(EQ(Var("x"), Var("x")), Assign(Var("x"), Minus(Var("x"), IntConst(1))))
        e.gen(context, target)
        expected = """
        while_do_1: 
        LOAD  r14,var_x
        LOAD  r13,var_x
        SUB  r0,r14,r13
        JUMP/PM  od_2    #==
        LOAD  r14,var_x
        LOAD  r13,const_1
        SUB   r14,r14,r13
        STORE r14,var_x
        JUMP  while_do_1
        od_2: 
        const_1: DATA 1
        var_x: DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


class Test_If_Gen(AsmTestCase):

    def test_if_gen(self):
        context = Context()
        target = context.allocate_register()
        e = If(EQ(Var("x"), IntConst(1)),
               Assign(Var("y"), Minus(Var("x"), IntConst(1))),
               Assign(Var("x"), IntConst(2)))
        e.gen(context, target)
        expected = """
        LOAD  r14,var_x
        LOAD  r13,const_1
        SUB  r0,r14,r13
        JUMP/PM  else_1 #==
        LOAD  r14,var_x
        LOAD  r13,const_1
        SUB   r14,r14,r13
        STORE r14,var_y
        JUMP  fi_2
        else_1: 
        LOAD r14,const_2
        STORE r14,var_x 
        fi_2: 
        const_1: DATA 1
        const_2: DATA 2
        var_x: DATA 0
        var_y: DATA 0
        """
        generated = context.get_lines()
        self.codeEqual(generated, expected)


if __name__ == "__main__":
    unittest.main()
