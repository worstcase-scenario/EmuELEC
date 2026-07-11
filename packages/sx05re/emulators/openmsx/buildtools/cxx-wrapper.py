#!/usr/bin/env python3
# openMSX cross-compile CXX wrapper for EmuELEC.
# Rewrites absolute -I/usr/ and -L/usr/ paths (emitted by openMSX's build
# probing) to point into the target sysroot, then execs the real compiler.
# Configuration comes from the environment (set in package.mk):
#   OPENMSX_SYSROOT   - target sysroot prefix
#   OPENMSX_REAL_CXX  - path to the real cross compiler
import sys, os

sysroot = os.environ["OPENMSX_SYSROOT"]
real    = os.environ["OPENMSX_REAL_CXX"]

args = []
for a in sys.argv[1:]:
    if   a.startswith('-I/usr/'): a = '-I' + sysroot + a[2:]
    elif a.startswith('-L/usr/'): a = '-L' + sysroot + a[2:]
    args.append(a)

os.execv(real, [real] + args)
