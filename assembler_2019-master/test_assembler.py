"""Unit tests for assembler phase 1"""

import unittest
from assembler_phase1 import *

#
class TestResolve(unittest.TestCase):

    def test_sample_resolve(self):
        lines = """
        # comment line at address 0

        # Blank line above is also address 0
        start:   # and start should also be address 0
        next:    ADD/P   r0,r1,r2[15]  # Still address 0
                 SUB     r1,r2,r3      # Address 1
        after:   MUL     r1,r2,r3[15]  # Address 2
        finally:  # Address 3
        fini:    DIV     r1,r2,r3      # Address 3
        """.split("\n")
        labels = resolve(lines)
        self.assertEqual(labels["start"], 0)
        self.assertEqual(labels["next"], 0)
        self.assertEqual(labels["after"], 2)
        self.assertEqual(labels["finally"], 3)
        self.assertEqual(labels["fini"], 3)


class TestParseMemop(unittest.TestCase):

    def test_parse_memop_unlabeled(self):
        line = "  LOAD/P  r3,something"
        fields = parse_line(line)
        self.assertEqual(fields["kind"], AsmSrcKind.MEMOP)
        self.assertEqual(fields["labelref"], "something")
        self.assertEqual(fields["opcode"], "LOAD")
        self.assertEqual(fields["label"], None)

    def test_parse_memop_labeled(self):
        line = "bogon:  STORE/Z r3,something # comments too"
        fields = parse_line(line)
        self.assertEqual(fields["kind"], AsmSrcKind.MEMOP)
        self.assertEqual(fields["labelref"], "something")
        self.assertEqual(fields["opcode"], "STORE")
        self.assertEqual(fields["label"], "bogon")


class TestOptionalFieldsFixup(unittest.TestCase):

    def test_fill_defaults(self):
        line = "  LOAD   r1,something"
        fields = parse_line(line)
        fix_optional_fields(fields)
        self.assertEqual(squish(fields["label"]), squish(""))
        self.assertEqual(squish(fields["predicate"]), squish(""))
        self.assertEqual(squish(fields["comment"]), squish(""))

    def test_keep_optionals(self):
        line = "lab:  LOAD/P   r1,something # comment"
        fields = parse_line(line)
        fix_optional_fields(fields)
        self.assertEqual(squish(fields["label"]), squish("lab:"))
        self.assertEqual(squish(fields["predicate"]), squish("/P"))
        self.assertEqual(squish(fields["comment"]), squish("# comment"))


class TestTransformation(unittest.TestCase):

    def test_memop_no_optional(self):
        lines = """
        # A comment line
        at_zero: ADD r0,r0,r0
        LOAD  r5,later
        STORE r5,at_zero
        ADD  r5,r0,r0[42]
        HALT r0,r0,r0
        later: DATA 84
        """.split("\n")
        transformed = transform(lines)
        expected = """
        # A comment line
        at_zero: ADD r0,r0,r0
        LOAD  r5,r0,r15[4] #later
        STORE r5,r0,r15[-2] #at_zero
        ADD  r5,r0,r0[42]
        HALT r0,r0,r0
        later: DATA 84
        """.split("\n")
        self.assertEqual(len(transformed), len(expected))
        for i in range(len(expected)):
            self.assertEqual(squish(transformed[i]), squish(expected[i]))

    def test_memop_preserve_optionals(self):
        lines = """
        # Just a comment
        zero: # With a comment

        # Blank line above should appear in output
        still_zero:  ADD  r5,more      # Another comment
        now_one:     LOAD r5,zero      # Why not?
        now_two:     STORE/M r5,somewhere # Silly but it's just a test
        somewhere:   HALT r0,r0,r0  # We would clobber this instruction!
        more:        DATA 17
        """.split("\n")
        transformed = transform(lines)
        expected = """
        # Just a comment
        zero: # With a comment

        # Blank line above should appear in output
        still_zero:  ADD  r5,r0,r15[4] #more # Another comment
        now_one:     LOAD r5,r0,r15[-1] #zero # Why not?
        now_two:     STORE/M r5,r0,r15[1] #somewhere # Silly but it's just a test
        somewhere:   HALT r0,r0,r0  # We would clobber this instruction!
        more:        DATA 17
        """.split("\n")
        self.assertEqual(len(transformed), len(expected))
        for i in range(len(expected)):
            self.assertEqual(squish(transformed[i]), squish(expected[i]))

    def test_jump_example(self):
        """This is the example from the header docstring of transform"""
        lines = """
           again: STORE r1,x
                  SUB r1,r0,r0[1]
                  JUMP/P  again
                  HALT  r0,r0,r0
           x: DATA  0
           """.split('\n')
        transformed = transform(lines)
        expected = """
           again:  STORE r1,r0,r15[4]   #x
                   SUB   r1,r0,r0[1]
                   ADD/P r15,r0,r15[-2] #again
                   HALT r0,r0,r0
           x:      DATA 0
           """.split('\n')
        self.assertEqual(len(transformed), len(expected))
        for i in range(len(expected)):
            self.assertEqual(squish(transformed[i]), squish(expected[i]))

    def test_jump_around(self):
        """Just a sample loop with an early exit"""
        lines = """
           begin: LOAD  r1,x
           loop:  SUB r1,r1,r0[1]
                  JUMP/Z endloop
                  STORE r1,r0,r0[511]  # print it
                  JUMP loop
           endloop: 
                   HALT  r0,r0,r0
           x:      DATA 42
           """.split("\n")
        transformed = transform(lines)
        expected = """
           begin: LOAD  r1,r0,r15[6] #x
           loop:  SUB r1,r1,r0[1]
                  ADD/Z  r15,r0,r15[3] #endloop
                  STORE r1,r0,r0[511]  # print it
                  ADD r15,r0,r15[-3] #loop
           endloop: 
                   HALT  r0,r0,r0
           x:      DATA 42
           """.split("\n")
        self.assertEqual(len(transformed), len(expected))
        for i in range(len(expected)):
            self.assertEqual(squish(transformed[i]), squish(expected[i]))


if __name__ == "__main__":
    unittest.main()
