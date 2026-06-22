#!/usr/bin/env python3
# Patches for Tsugaru CPU on aarch64/EmuELEC
import sys

build = sys.argv[1]

def patch(fname, old, new, desc, cnt=1):
    with open(fname, 'r') as f: s = f.read()
    n = s.count(old)
    if n == 0:
        print(f"SKIP (0 matches): {desc}")
        return
    # cnt=-1 means replace all
    s2 = s.replace(old, new) if cnt < 0 else s.replace(old, new, cnt)
    with open(fname, 'w') as f: f.write(s2)
    replaced = n if cnt < 0 else min(n, cnt)
    print(f"OK ({replaced}/{n}): {desc}")

run = f"{build}/src/cpu/i486runinstruction.h"
fid = f"{build}/src/cpu/i486fidelity.h"

# --- Patch 1: default clock count instead of Abort() ---
patch(run,
    '\tif(0==clocksPassed)\n'
    '\t{\n'
    '\t\tstd::string msg="Clocks-Passed is not set.  Opcode=";\n'
    '\t\tmsg+=cpputil::Ustox(inst.RealOpCode());\n'
    '\t\tmsg+="H";\n'
    '\t\tAbort(msg);\n'
    '\t\tEIPIncrement=0;\n'
    '\t}',
    '\tif(0==clocksPassed)\n'
    '\t{\n'
    '\t\tclocksPassed=4; // default for unimplemented opcode timing\n'
    '\t}',
    'clocksPassed default')

# --- Patch 2: OnLock no-op in HIGHFIDELITY ---
patch(fid,
    '\tinline static void OnLock(i486DXCommon &cpu)\n'
    '\t{\n'
    '\t\tcpu.RaiseException(i486DXCommon::EXCEPTION_LOCK_MAYBE,0);\n'
    '\t}',
    '\tinline static void OnLock(i486DXCommon &cpu)\n'
    '\t{\n'
    '\t\t(void)cpu; // PATCHED: LOCK prefix no-op like DEFAULT_FIDELITY\n'
    '\t}',
    'HIGHFIDELITY OnLock no-op')

# --- Patch 3: SAL (REG=6) = SHL (REG=4) on real i486 ---
# In C macros, line continuation = single backslash at end of line.
# In Python strings, '\\' = one backslash, '\n' = newline.
# cat -A of the file shows lines end with ' \\$' i.e. space+backslash+newline.
# But some end with '\\\n' (backslash then newline, no space).
#
# Exact patterns (verified via cat -A):
# Byte: case 6 at 4 tabs, body at 5 tabs
# Word/Dword: case 6 at 5 tabs, body at 6 tabs (same indent for both!)

BODY = 'Abort("Undefined REG for "+cpputil::Ustox(inst.RealOpCode())); \\\n'
CLK  = 'clocksPassed=(OPER_ADDR==op1.operandType ? 4 : 2); \\\n'
RET  = 'return 0; \\'

byte_old  = '\t\t\t\tcase 6: \\\n' + '\t\t\t\t\t' + BODY + '\t\t\t\t\t' + CLK + '\t\t\t\t\t' + RET
byte_new  = '\t\t\t\tcase 6: \\\n' + '\t\t\t\t\tShlByte(i,ctr); \\\n' + '\t\t\t\t\t' + CLK + '\t\t\t\t\tbreak; \\'

word_old  = '\t\t\t\t\tcase 6: \\\n' + '\t\t\t\t\t\t' + BODY + '\t\t\t\t\t\t' + CLK + '\t\t\t\t\t\t' + RET
word_new  = '\t\t\t\t\tcase 6: \\\n' + '\t\t\t\t\t\tShlWord(i,ctr); \\\n' + '\t\t\t\t\t\t' + CLK + '\t\t\t\t\t\tbreak; \\'
dword_new = '\t\t\t\t\tcase 6: \\\n' + '\t\t\t\t\t\tShlDword(i,ctr); \\\n' + '\t\t\t\t\t\t' + CLK + '\t\t\t\t\t\tbreak; \\'

with open(run, 'r') as f: s = f.read()
nb = s.count(byte_old)
nw = s.count(word_old)
# Replace byte (all 2), then first 2 word, then remaining 2 as dword
s = s.replace(byte_old, byte_new)        # 2 replacements
s = s.replace(word_old, word_new, 2)     # first 2 = Word variants
s = s.replace(word_old, dword_new)       # remaining 2 = Dword variants
remaining = s.count('Abort("Undefined REG for "')
with open(run, 'w') as f: f.write(s)
print(f"OK SAL->SHL: Byte={nb} Word+Dword={nw} remaining_aborts={remaining}")


# --- Patch 4: opcode 0xFE REG=2..7 — treat 6=INC, 7=DEC (real i486 behaviour) ---
with open(run, 'r') as f: src = f.read()
old4 = (
    '\t\t\tcase 2:\n'
    '\t\t\tcase 3:\n'
    '\t\t\tcase 4:\n'
    '\t\t\tcase 5:\n'
    '\t\t\tcase 6:\n'
    '\t\t\tcase 7:\n'
    '\t\t\t\tAbort("Undefined REG for "+cpputil::Ustox(inst.RealOpCode()));\n'
    '\t\t\t\treturn 0;'
)
new4 = (
    '\t\t\tcase 2:\n'
    '\t\t\tcase 3:\n'
    '\t\t\tcase 4:\n'
    '\t\t\tcase 5:\n'
    '\t\t\tcase 6:\n'
    '\t\t\t\tIncrementByte(i); // undefined: i486 treats 6 as INC\n'
    '\t\t\t\tbreak;\n'
    '\t\t\tcase 7:\n'
    '\t\t\t\tDecrementByte(i); // undefined: i486 treats 7 as DEC\n'
    '\t\t\t\tbreak;'
)
n = src.count(old4)
src = src.replace(old4, new4, 1)
with open(run, 'w') as f: f.write(src)
print(f"OK ({min(n,1)}/{n}): 0xFE undefined REG -> INC/DEC")


# --- Patch 5: discimg.cpp - fix binaryCache off-by-16 bug for MODE1/2352 sectors ---
disc = f"{build}/src/discimg/discimg.cpp"
with open(disc, 'r') as f: src = f.read()
old5 = (
    '\t\t\t\t\t\t\tfilePtr+=16;\n'
    '\t\t\t\t\t\t\tmemcpy(data.data()+dataPointer,binaryCache.data()+filePtr,MODE1_BYTES_PER_SECTOR);\n'
    '\t\t\t\t\t\t\tfilePtr+=tracks[0].sectorLength;\n'
    '\t\t\t\t\t\t\tdataPointer+=MODE1_BYTES_PER_SECTOR;'
)
new5 = (
    '\t\t\t\t\t\t\tfilePtr+=16;\n'
    '\t\t\t\t\t\t\tmemcpy(data.data()+dataPointer,binaryCache.data()+filePtr,MODE1_BYTES_PER_SECTOR);\n'
    '\t\t\t\t\t\t\tfilePtr+=(tracks[0].sectorLength-16); // fix off-by-16 per sector\n'
    '\t\t\t\t\t\t\tdataPointer+=MODE1_BYTES_PER_SECTOR;'
)
n = src.count(old5)
src = src.replace(old5, new5, 1)
with open(disc, 'w') as f: f.write(src)
print(f"OK ({min(n,1)}/{n}): discimg.cpp binaryCache 2352-sector fix")