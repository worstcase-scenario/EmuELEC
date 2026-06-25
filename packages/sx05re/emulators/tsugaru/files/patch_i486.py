#!/usr/bin/env python3
# patch_i486.py — Tsugaru source patches for EmuELEC aarch64
# Called from package.mk pre_configure_target() with ${PKG_BUILD} as argument.
#
# Patches (all verified against commit 0e31cb4065fd5b7888cb6c13d19f358925f9366e):
#
# 1. i486runinstruction.h : clocksPassed=4 instead of Abort() for unknown timing
# 2. i486fidelity.h       : HIGHFIDELITY OnLock → no-op (prevents #UD loop FFFE:2397)
# 3. i486runinstruction.h : SAL (shift REG=6) → SHL — real i486 behaviour
# 4. i486runinstruction.h : 0xFE REG=2..5 → NOP, REG=6 → INC, REG=7 → DEC
# 5. discimg.cpp          : fix off-by-16 binaryCache pointer for MODE1/2352 sectors
# 6. i486runinstruction.h : 0xFF REG=7 → NOP (runs AFTER Patch 4 clears 0xFE match)
# 7. i486.cpp             : fpuState.FNINIT() in CPU Reset — clears STATUS_ES=0x80
#                           which prevents spurious FPU exception → IRQ13 → INT 75H
#                           → uninitialized IVT vector 0000:0000 at T≈1.57s into boot

import sys

build = sys.argv[1]

def patch(fname, old, new, desc, cnt=1):
    with open(fname, 'r') as f:
        s = f.read()
    n = s.count(old)
    if n == 0:
        print(f'SKIP (0 matches): {desc}')
        return
    s2 = s.replace(old, new) if cnt < 0 else s.replace(old, new, cnt)
    with open(fname, 'w') as f:
        f.write(s2)
    replaced = n if cnt < 0 else min(n, cnt)
    print(f'OK ({replaced}/{n}): {desc}')

run = f'{build}/src/cpu/i486runinstruction.h'
fid = f'{build}/src/cpu/i486fidelity.h'
i486 = f'{build}/src/cpu/i486.cpp'
disc = f'{build}/src/discimg/discimg.cpp'

# ── Patch 1: clocksPassed default ────────────────────────────────────────────
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

# ── Patch 2: HIGHFIDELITY OnLock no-op ───────────────────────────────────────
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

# ── Patch 3: SAL (REG=6) = SHL (REG=4) ───────────────────────────────────────
# All 6 occurrences: 2 Byte (4-tab case), 2 Word + 2 Dword (5-tab case).
# Byte and Word/Dword differ only in indentation; word_old serves both.
BODY = 'Abort("Undefined REG for "+cpputil::Ustox(inst.RealOpCode())); \\\n'
CLK  = 'clocksPassed=(OPER_ADDR==op1.operandType ? 4 : 2); \\\n'
RET  = 'return 0; \\'

byte_old  = ('\t\t\t\tcase 6: \\\n'
             '\t\t\t\t\t' + BODY +
             '\t\t\t\t\t' + CLK +
             '\t\t\t\t\t' + RET)
byte_new  = ('\t\t\t\tcase 6: \\\n'
             '\t\t\t\t\tShlByte(i,ctr); \\\n'
             '\t\t\t\t\t' + CLK +
             '\t\t\t\t\tbreak; \\')

word_old  = ('\t\t\t\t\tcase 6: \\\n'
             '\t\t\t\t\t\t' + BODY +
             '\t\t\t\t\t\t' + CLK +
             '\t\t\t\t\t\t' + RET)
word_new  = ('\t\t\t\t\tcase 6: \\\n'
             '\t\t\t\t\t\tShlWord(i,ctr); \\\n'
             '\t\t\t\t\t\t' + CLK +
             '\t\t\t\t\t\tbreak; \\')
dword_new = ('\t\t\t\t\tcase 6: \\\n'
             '\t\t\t\t\t\tShlDword(i,ctr); \\\n'
             '\t\t\t\t\t\t' + CLK +
             '\t\t\t\t\t\tbreak; \\')

with open(run, 'r') as f: s = f.read()
nb = s.count(byte_old)
nw = s.count(word_old)
s = s.replace(byte_old, byte_new)       # 2 Byte replacements
s = s.replace(word_old, word_new, 2)    # first 2 = Word
s = s.replace(word_old, dword_new)      # remaining 2 = Dword
with open(run, 'w') as f: f.write(s)
print(f'OK SAL→SHL: Byte={nb} Word+Dword={nw}')

# ── Patch 4: 0xFE REG=2..7 ───────────────────────────────────────────────────
# Real i486: REG=6 → INC, REG=7 → DEC, 2-5 → undocumented no-ops.
# NOTE: This MUST run before Patch 6 — it clears the 0xFE match that would
# otherwise confuse Patch 6's pattern search.
patch(run,
    '\t\t\tcase 2:\n'
    '\t\t\tcase 3:\n'
    '\t\t\tcase 4:\n'
    '\t\t\tcase 5:\n'
    '\t\t\tcase 6:\n'
    '\t\t\tcase 7:\n'
    '\t\t\t\tAbort("Undefined REG for "+cpputil::Ustox(inst.RealOpCode()));\n'
    '\t\t\t\treturn 0;',
    '\t\t\tcase 2:\n'
    '\t\t\tcase 3:\n'
    '\t\t\tcase 4:\n'
    '\t\t\tcase 5:\n'
    '\t\t\t\tclocksPassed=2; // undefined: treat as NOP\n'
    '\t\t\t\tbreak;\n'
    '\t\t\tcase 6:\n'
    '\t\t\t\tIncrementByte(i); // undefined: i486 treats REG=6 as INC\n'
    '\t\t\t\tbreak;\n'
    '\t\t\tcase 7:\n'
    '\t\t\t\tRaiseException(EXCEPTION_UD,0); // #UD for real i486 / FreeTOWNS dispatch\n'
    '\t\t\t\tEIPIncrement=0;\n'
    '\t\t\t\tclocksPassed=ClocksForHandlingException();\n'
    '\t\t\t\tbreak;',
    '0xFE undefined REG=2..7 → NOP/INC/RaiseExceptionUD')

# ── Patch 5: discimg binaryCache off-by-16 ───────────────────────────────────
# MODE1/2352 raw sectors have a 16-byte header. The binaryCache pointer
# advanced by sectorLength (2352) after skipping the header, so each
# subsequent sector read was off by 16 bytes. Fix: subtract the 16 bytes
# already consumed from the sectorLength advance.
patch(disc,
    '\t\t\t\t\t\t\tfilePtr+=16;\n'
    '\t\t\t\t\t\t\tmemcpy(data.data()+dataPointer,binaryCache.data()+filePtr,MODE1_BYTES_PER_SECTOR);\n'
    '\t\t\t\t\t\t\tfilePtr+=tracks[0].sectorLength;\n'
    '\t\t\t\t\t\t\tdataPointer+=MODE1_BYTES_PER_SECTOR;',
    '\t\t\t\t\t\t\tfilePtr+=16;\n'
    '\t\t\t\t\t\t\tmemcpy(data.data()+dataPointer,binaryCache.data()+filePtr,MODE1_BYTES_PER_SECTOR);\n'
    '\t\t\t\t\t\t\tfilePtr+=(tracks[0].sectorLength-16); // fix: -16 already advanced above\n'
    '\t\t\t\t\t\t\tdataPointer+=MODE1_BYTES_PER_SECTOR;',
    'discimg binaryCache 2352-sector off-by-16')

# ── Patch 6: 0xFF REG=7 → NOP ────────────────────────────────────────────────
# After Patch 4 removes the 0xFE match, this pattern appears exactly once
# (in the 0xFF = I486_RENUMBER_INC_DEC_CALL_CALLF_JMP_JMPF_PUSH handler).
# Defensive: if FPU exception still escapes Patch 7, CPU reaches 0000:0002
# (bytes FF FF) and this prevents an Abort() there.
patch(run,
    '\t\t\tcase 7:\n'
    '\t\t\t\tAbort("Undefined REG for "+cpputil::Ustox(inst.RealOpCode()));\n'
    '\t\t\t\treturn 0;\n'
    '\t\t\tdefault:\n'
    '\t\t\t\tstd_unreachable;\n'
    '\t\t\t}',
    '\t\t\tcase 7:\n'
    '\t\t\t\tRaiseException(EXCEPTION_UD,0); // #UD for real i486\n'
    '\t\t\t\tEIPIncrement=0;\n'
    '\t\t\t\tclocksPassed=ClocksForHandlingException();\n'
    '\t\t\t\tbreak;\n'
    '\t\t\tdefault:\n'
    '\t\t\t\tstd_unreachable;\n'
    '\t\t\t}',
    '0xFF REG=7 → RaiseException #UD')

# ── Patch 7: fpuState.FNINIT() in CPU Reset ──────────────────────────────────
# ROOT FIX for the Fujitsu BIOS crash at T≈1.57s:
# The FPUState class initialises statusWord=0xFFFF (all bits set, including
# STATUS_ES=0x80 = Error Summary). i486DXCommon::Reset() never calls
# fpuState.Reset() or fpuState.FNINIT(), so STATUS_ES stays set.
# This makes ExceptionPending() return true from boot onwards.
# When the BIOS eventually executes its first FPU instruction (FLD at 0050:8CBF),
# the pending error fires FERR# → IRQ13 → INT 75H. INT 75H's vector is
# 0000:0000 (IVT not yet initialised) → CPU jumps to IVT start → crash.
# FNINIT resets statusWord=0 and controlWord=0x037F (all exceptions masked),
# matching real i486 FPU-after-reset behaviour.
patch(i486,
    '\tstate.halt=false;\n'
    '\tstate.holdIRQ=false;\n'
    '\tstate.exception=false;\n'
    '}',
    '\tstate.halt=false;\n'
    '\tstate.holdIRQ=false;\n'
    '\tstate.exception=false;\n'
    '\tstate.fpuState.FNINIT(); // clear STATUS_ES; prevents spurious IRQ13→INT75H\n'
    '}',
    'fpuState.FNINIT() in CPU Reset')