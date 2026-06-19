#!/usr/bin/env python3
# Patches i486runinstruction.h to use a default clock count instead of aborting
# when an opcode has no clock cycle definition (clocksPassed==0).
import sys

fname = sys.argv[1]
with open(fname, 'r') as f:
    s = f.read()

old = (
    '\tif(0==clocksPassed)\n'
    '\t{\n'
    '\t\tstd::string msg="Clocks-Passed is not set.  Opcode=";\n'
    '\t\tmsg+=cpputil::Ustox(inst.RealOpCode());\n'
    '\t\tmsg+="H";\n'
    '\t\tAbort(msg);\n'
    '\t\tEIPIncrement=0;\n'
    '\t}'
)
new = (
    '\tif(0==clocksPassed)\n'
    '\t{\n'
    '\t\tclocksPassed=4; // default for unimplemented opcode timing (was: Abort)\n'
    '\t}'
)

if old in s:
    s = s.replace(old, new)
    with open(fname, 'w') as f:
        f.write(s)
    print("i486 clock patch OK")
else:
    print("ERROR: pattern not found in " + fname, file=sys.stderr)
    sys.exit(1)
