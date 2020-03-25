"""
A container for the context information kept
for assembly code generation while walking
an abstract syntax tree.

The context object is passed around from node to
node during code generation. Having a context
object, rather than a set of different pieces
of information passed around, isolates in one
place several small design decisions:  How
registers are allocated, how constants and variables
are declared, when and how the code is actually
emitted to the output file.
"""

from typing import List

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Context(object):
    """The state of code generation"""

    # Instructions in the source code, as a list of
    # strings.
    def __init__(self):
        # A table of integer constants to be declared at
        # the end of the source program.  The table maps
        # values to names, so that we can reuse them.
        self.consts = {}

        # A table of variables to be declared at
        # the end of the source program, with the
        # symbols used for them in the assembly code.
        self.vars = {}

        # Instructions in the source code, as a list of
        # strings.
        self.assm_lines = []

        # The available registers
        self.registers = [f"r{i}" for i in range(1, 15)]

        # creates a unique label for identifying sign of integers
        self.label_count = 0

    def add_line(self, line: str):
        """Add a line of assembly code"""
        self.assm_lines.append(line)
       # log.info("Added line, now {}".format(self.assm_lines))

    def get_lines(self) -> List[str]:
        """Get all the generated source code, including
        declarations of variables and constants.
        """
        code = self.assm_lines.copy()
        for constval in sorted(self.consts):
            code.append(f"{self.consts[constval]}:  DATA {constval}")

        for name in (self.vars):
          #  log.info(f"var name is: {name}")
          #  log.info(f"data for var is: {self.vars[name]}")
            code.append(f"{self.vars[name]}:  DATA 0")
         #   log.info(f"code line is:   {code}")
        return code

    def get_const_symbol(self, value: int) -> str:
        """Returns the name of the label associated
        with a constant value, and remembers to
        declare it at the end of the source code.
        """
        assert isinstance(value, int)
        if value < 0:
            label = f"const_n_{abs(value)}"
        else:
            label = f"const_{value}"
        self.consts[value] = label
        return label

    def get_var_symbol(self, name: str) -> str:
        """Returns the name of the label associated
        with a constant value, and remembers to
        declare it at the end of the source code.
        """
        label = f"var_{name}"
        self.vars[name] = label
        return label

    def new_label(self, prefix: str) -> str:
        """Return a unique label starting with prefix"""
        self.label_count += 1
        return f"{prefix}_{self.label_count}"

    def allocate_register(self) -> str:
        """Get the name of a register that is not otherwise
        occupied. Keep exclusive access until it is returned with
        free_register(reg).
        """
        return self.registers.pop()

    def free_register(self, reg_name: str):
        """Return the named register to the pool of
        available registers.
        """
        self.registers.append(reg_name)








