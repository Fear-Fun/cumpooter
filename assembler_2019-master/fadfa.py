"""
CIS 211 Winter 2020
Title: AP 1
Author: Yifeng Cui
Status: Active
Type: Done
Created: 02-Mar-2020
"""
"""
Assembler Phase I for DM2019W assembly language.

This assembler produces fully resolved instructions,
which may be the input of assembler_phase2.py.
The input of this phase may contain symbolic
addresses, e.g.,
    again:   LOAD  r1,x
             SUB  r1,r0,r2[5]
             JUMP/P  again
    x:  DATA 12

Assembly instruction format with all options is

label: instruction

Both parts are optional:  A label may appear without
an instruction, and an instruction may appear without
a label.

A label is at least one alphabetic letter
followed by any number of letters (of any kind)
and underscore, e.g., My_dog_boo.

An instruction has the following form:

  opcode/predicate  target,src1,src2[disp]

Opcode is required, and should be one of the DM2018W
instruction codes (ADD, MOVE, etc); case-insensitive

/predicate is optional.  If present, it should be some
combination of M,Z,P, or V e.g., /NP would be "execute if
not zero".  If /predicate is not given, it is interpreted
as /ALWAYS, which is an alias for /MZPV.

target, src1, and src2 are register numbers (r0,r1, ... r15)

[disp] is optional.  If present, it is a 12 bit
signed integer displacement.  If absent, it is
treated as [0].

The second source register and displacement may be replaced
by a label, e.g.,
    LOAD  r1,x
In an instruction with the pseudo-operation JUMP,
all the registers may be omitted (a target of r15 is implied)
and replaced by a label, e.g.,
    JUMP/Z  again
Instructions with these forms will be translated to fully
resolved instructions, e.g.,
    LOAD r1,r0,r15[14]  #x
    ADD/Z r15,r0,15[-7] #again

DATA is a pseudo-operation:
   myvar:  DATA   18
indicates that the integer value 18
should be stored at this location, rather than
a DM2018S instruction.

"""
from instr_format import Instruction, OpCode, CondFlag, NAMED_REGS
import argparse

from typing import Union, List, Dict
from enum import Enum, auto

import sys
import re

import logging

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Configuration constants
ERROR_LIMIT = 5  # Abandon assembly if we exceed this


# Exceptions raised by this module
class SyntaxError(Exception):
    pass


###
# The whole instruction line is encoded as a single
# regex with capture names for the parts we might
# refer to. Error messages will be crappy (we'll only
# know that the pattern didn't match, and not why), but
# we get a very simple match/process cycle.  By creating
# a dict containing the captured fields, we can determine
# which optional parts are present (e.g., there could be
# label without an instruction or an instruction without
# a label).
###


# To simplify client code, we'd like to return a dict with
# the right fields even if the line is syntactically incorrect.
DICT_NO_MATCH = {'label': None, 'opcode': None, 'predicate': None,
                 'target': None, 'src1': None, 'src2': None,
                 'offset': None, 'comment': None}


###
# Although the DM2019W instruction set is very simple, a source
# line can still come in several forms.  Each form (even comments)
# can start with a label.
###

class AsmSrcKind(Enum):
    """Distinguish which kind of assembly language instruction
    we have matched.  Each element of the enum corresponds to
    one of the regular expressions below.
    """
    # Blank or just a comment, optionally
    # with a label
    COMMENT = auto()
    # Fully specified  (all addresses resolved)
    FULL = auto()
    # A data location, not an instruction
    DATA = auto()
    # An instruction that refers to a memory
    # location in place of its source and offset
    # parts.
    MEMOP = auto()

    JUMP = auto()


# Lines that contain only a comment (and possibly a label).
# This includes blank lines and labels on a line by themselves.
#
ASM_COMMENT_PAT = re.compile(r"""
   \s*
   # Optional label 
   (
     (?P<label> [a-zA-Z]\w*):
   )?
   \s*
   # Optional comment follows # or ; 
   (
     (?P<comment>[\#;].*)
   )?       
   \s*$             
   """, re.VERBOSE)

# Instructions with fully specified fields. We can generate
# code directly from these.
ASM_FULL_PAT = re.compile(r"""
   \s*
   # Optional label 
   (
     (?P<label> [a-zA-Z]\w*):
   )?
   \s*
    # The instruction proper 
    (?P<opcode>    [a-zA-Z]+)           # Opcode
    (/ (?P<predicate> [A-Z]+) )?   # Predicate (optional)
    \s+
    (?P<target>    r[0-9]+),            # Target register
    (?P<src1>      r[0-9]+),            # Source register 1
    (?P<src2>      r[0-9]+)             # Source register 2
    (\[ (?P<offset>[-]?[0-9]+) \])?     # Offset (optional)
   # Optional comment follows # or ; 
   (
     \s*
     (?P<comment>[\#;].*)
   )?       
   \s*$             
   """, re.VERBOSE)

# Defaults for values that ASM_FULL_PAT makes optional
INSTR_DEFAULTS = [('predicate', 'ALWAYS'), ('offset', '0')]

# A data word in memory; not a DM2019W instruction
#
ASM_DATA_PAT = re.compile(r""" 
   \s* 
   # Optional label 
   (
     (?P<label> [a-zA-Z]\w*):
   )?
   # The instruction proper  
   \s*
    (?P<opcode>    DATA|data)           # Opcode
    (/ (?P<predicate> [A-Z]+) )?   # Predicate (optional)
   # Optional data value
   \s*
   (?P<value>  (0x[a-fA-F0-9]+)
             | ([0-9]+))?
    # Optional comment follows # or ; 
   (
     \s*
     (?P<comment>[\#;].*)
   )?       
   \s*$             
   """, re.VERBOSE)

ASM_MEMOP_PAT = re.compile(r"""
   \s*
   # Optional label 
   (
     (?P<label> [a-zA-Z]\w*):
   )?
   \s*
    # The instruction proper 
    (?P<opcode>    \b((?!LDA|lda)[a-zA-Z])+)           # Opcode
    (/ (?P<predicate> [A-Z]+) )?   # Predicate (optional)
    \s+
    (?P<target>    r[0-9]+),            # Target register
    (?P<labelref>      [a-zA-Z]\w*)            # label reference
   # Optional comment follows # or ; 
   (
     \s*
     (?P<comment>[\#;].*)
   )?       
   \s*$             
    """, re.VERBOSE)

ASM_JUMP_PAT = re.compile(r"""
   \s*
   # Optional label 
   (
     (?P<label> [a-zA-Z]\w*):
   )?
   \s*
    # The instruction proper 
    (?P<opcode>    JUMP|jump)           # Opcode
    (/ (?P<predicate> [A-Z]+) )?   # Predicate (optional)
    \s+
    (?P<labelref>      [a-zA-Z]\w*)            # label reference
   # Optional comment follows # or ; 
   (
     \s*
     (?P<comment>[\#;].*)
   )?       
   \s*$             
    """, re.VERBOSE)

PATTERNS = [(ASM_FULL_PAT, AsmSrcKind.FULL),
            (ASM_DATA_PAT, AsmSrcKind.DATA),
            (ASM_COMMENT_PAT, AsmSrcKind.COMMENT),
            (ASM_MEMOP_PAT, AsmSrcKind.MEMOP),
            (ASM_JUMP_PAT, AsmSrcKind.JUMP)
            ]


def parse_line(line: str) -> dict:
    """Parse one line of assembly code.
    Returns a dict containing the matched fields,
    some of which may be empty.  Raises SyntaxError
    if the line does not match assembly language
    syntax. Sets the 'kind' field to indicate
    which of the patterns was matched.
    """
    log.debug("\nParsing assembler line: '{}'".format(line))
    # Try each kind of pattern
    for pattern, kind in PATTERNS:
        match = pattern.fullmatch(line)
        if match:
            fields = match.groupdict()
            fields["kind"] = kind
            log.debug("Extracted fields {}".format(fields))
            return fields
    raise SyntaxError("Assembler syntax error in {}".format(line))


def transform(lines: List[str]) -> List[str]:
    """
    Transform some assembly language lines, leaving others
    unchanged.
    Initial version:  No changes to any source line.

    Planned version:
       again:   STORE r1,x
                SUB   r1,r0,r0[1]
                JUMP/P  again
                HALT r0,r0,r0
       x:       DATA 0
    should become
       again:   STORE r1,r0,r15[4]   # x
                SUB   r1,r0,r0[1]
                ADD   r15,r0,r15[-2]
                HALT r0,r0,r0
       x:       DATA 0
     """
    error_count = 0
    transformed = []
    address = 0
    lables = resolve(lines)
    for lnum in range(len(lines)):
        line = lines[lnum].rstrip()
        log.debug("Processing line {}: {}".format(lnum, line))
        try:
            fields = parse_line(line)
            f = fields
            if fields["kind"] != AsmSrcKind.COMMENT:
                fields['opcode'] = fields['opcode'].upper()
            if fields["kind"] == AsmSrcKind.FULL:
                log.debug("Passing through FULL instruction")
                fix_optional_fields(f)
                if fields["offset"] is None:
                    full = (f"{f['label']}   {f['opcode']}{f['predicate']} " +
                            f" {f['target']},{f['src1']},{f['src2']} " +
                            f" {f['comment']}")
                else:
                    full = (f"{f['label']}   {f['opcode']}{f['predicate']} " +
                            f" {f['target']},{f['src1']},{f['src2']}[{f['offset']}] " +
                            f" {f['comment']}")
                transformed.append(full)
            elif fields["kind"] == AsmSrcKind.DATA:
                log.debug("Passing through DATA instruction")
                fix_optional_fields(f)
                full = (f"{f['label']}   {f['opcode']} " +
                        f" {f['value']} " +
                        f" {f['comment']}")
                transformed.append(full)
            elif fields["kind"] == AsmSrcKind.MEMOP:
                mem_addr = lables[fields["labelref"]]
                pc_relative = mem_addr - address
                fix_optional_fields(f)
                full = (f"{f['label']}   {f['opcode']}{f['predicate']} " +
                        f" {f['target']},r0,r15[{pc_relative}] #{f['labelref']} " +
                        f" {f['comment']}")
                transformed.append(full)
            elif fields["kind"] == AsmSrcKind.JUMP:
                mem_addr = lables[fields["labelref"]]
                pc_relative = mem_addr - address
                f['opcode'] = "ADD"
                fix_optional_fields(f)
                full = (f"{f['label']}   {f['opcode']}{f['predicate']} " +
                        f" r15,r0,r15[{pc_relative}] #{f['labelref']} " +
                        f" {f['comment']}")
                transformed.append(full)
            else:
                log.debug(" -xxx- No pattern matched -xxx- ")
                transformed.append(line)
            if fields["kind"] != AsmSrcKind.COMMENT:
                address += 1
        except SyntaxError as e:
            error_count += 1
            print("Syntax error in line {}: {}".format(lnum, line))
        except KeyError as e:
            error_count += 1
            print("Unknown word in line {}: {}".format(lnum, e))
        except Exception as e:
            error_count += 1
            print("Exception encountered in line {}: {}".format(lnum, e))
        if error_count > ERROR_LIMIT:
            print("Too many errors; abandoning")
            sys.exit(1)
    return transformed


def fix_optional_fields(fields: Dict[str, str]):
    """Fill in values of optional fields label,
    predicate, and comment, adding the punctuation
    they require.
    """
    if fields["label"] is None:
        fields["label"] = "    "
    else:
        fields["label"] = fields["label"] + ":"
    if fields["predicate"] is None:
        fields["predicate"] = ""
    else:
        fields["predicate"] = "/" + fields["predicate"]
    if fields["comment"] is None:
        fields["comment"] = ""
    else:
        fields["comment"] = fields["comment"]


def resolve(lines: List[str]) -> Dict[str, int]:
    """
    Build table associating labels in the source code
    with addresses.
    """
    labels = {}
    address = 0
    for lnum in range(len(lines)):
        line = lines[lnum].rstrip()
        log.debug("Processing line {}: {}".format(lnum, line))
        try:
            fields = parse_line(line)
            if fields["label"] is not None:
                labels[fields["label"]] = address
            if fields["kind"] != AsmSrcKind.COMMENT:
                address += 1
        except  Exception:
            # Just ignore errors here; they will be handled in
            # transform
            pass

    return labels


def cli() -> object:
    """Get arguments from command line"""
    parser = argparse.ArgumentParser(description="Duck Machine Assembler (phase 1)")
    parser.add_argument("sourcefile", type=argparse.FileType('r'),
                        nargs="?", default=sys.stdin,
                        help="Duck Machine assembly code file")
    parser.add_argument("objfile", type=argparse.FileType('w'),
                        nargs="?", default=sys.stdout,
                        help="Transformed assembly language file")
    args = parser.parse_args()
    return args


def main():
    """"Assemble a Duck Machine program"""
    args = cli()
    lines = args.sourcefile.readlines()
    object_code = transform(lines)
    log.debug("Object code: \n{}".format(object_code))
    for word in object_code:
        log.debug("Instruction word {}".format(word))
        print(word, file=args.objfile)


if __name__ == "__main__":
    main()
