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
    '\t\t\t\tclocksPassed=2; // undefined: NOP, advance past instruction\n'
    '\t\t\t\tbreak;',
    '0xFE undefined REG=2..7 → NOP/INC/NOP')

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
    '\t\t\t\tclocksPassed=1; // undefined: NOP, advance past instruction\n'
    '\t\t\t\tbreak;\n'
    '\t\t\tdefault:\n'
    '\t\t\t\tstd_unreachable;\n'
    '\t\t\t}',
    '0xFF REG=7 → NOP advance')

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


# ── Patch 8: one-shot INT 75H stub via RunFastDevicePollingInternal ───────────
# BIOS clears all RAM in physMem.State::Reset() → anything we write in Reset()
# is wiped. The BIOS never initializes IVT[75H] (INT 0x75 = FPU error via IRQ13).
# At T≈1.54s the BIOS hits FLD at 0050:8CBF, FERR# fires → INT 75H → IVT[75H]=0:0
# → CPU slides through IVT bytes.
# Fix: in RunFastDevicePollingInternal(), once townsTime crosses 1.2s, write a
# FNINIT(DB E3)+IRET(CF) stub into low RAM and point IVT[75H] there.
# By 1.2s the BIOS has already finished clearing RAM, so the entry survives.
towns_cpp = f'{build}/src/towns/towns.cpp'
patch(towns_cpp,
    'void FMTownsCommon::RunFastDevicePollingInternal(void)\n'
    '{\n'
    '\ttimer.TimerPolling(state.townsTime);\n'
    '\tmidi.TimerPolling(state.townsTime);\n'
    '\tsound.SoundPolling(state.townsTime);\n'
    '\tcrtc.ProcessVSYNCIRQ(state.townsTime);\n'
    '\tstate.nextFastDevicePollingTime=state.townsTime+FAST_DEVICE_POLLING_INTERVAL;\n'
    '}',
    'void FMTownsCommon::RunFastDevicePollingInternal(void)\n'
    '{\n'
    '\ttimer.TimerPolling(state.townsTime);\n'
    '\tmidi.TimerPolling(state.townsTime);\n'
    '\tsound.SoundPolling(state.townsTime);\n'
    '\tcrtc.ProcessVSYNCIRQ(state.townsTime);\n'
    '\tstate.nextFastDevicePollingTime=state.townsTime+FAST_DEVICE_POLLING_INTERVAL;\n'
    '\t// Patch 8: one-shot INT 75H (FPU error) stub — installed after BIOS RAM-clear\n'
    '\tif(state.townsTime>=1200000000ULL &&\n'
    '\t   physMem.state.RAM.size()>0x9200 &&\n'
    '\t   physMem.state.RAM[0x01D5]==0x00 &&\n'
    '\t   physMem.state.RAM[0x01D7]==0x00 &&\n'
    '\t   physMem.state.RAM[0x01D4]==0x00 &&\n'
    '\t   physMem.state.RAM[0x6000]==0x00)\n'
    '\t{\n'
    '\t\tphysMem.state.RAM[0x6000]=0xDB; // FNINIT\n'
    '\t\tphysMem.state.RAM[0x6001]=0xE3;\n'
    '\t\tphysMem.state.RAM[0x6002]=0xCF; // IRET\n'
    '\t\tphysMem.state.RAM[0x01D4]=0x00; // INT 75H: IP low = 0x00\n'
    '\t\tphysMem.state.RAM[0x01D5]=0x60; // IP high = 0x60 → 0x6000\n'
    '\t\tphysMem.state.RAM[0x01D6]=0x00; // CS low = 0x00\n'
    '\t\tphysMem.state.RAM[0x01D7]=0x00; // CS high = 0x00\n'
    '\t\t// Also write IRET at 0:0002 so INT6 dispatch (INC[BX+SI]+IRET) works\n'
    '\t\t// without sliding through IVT bytes that contain PUSH-like opcodes.\n'
    '\t\t// IVT[6]=0:0000; at 0:0: FE 00=INC[BX+SI]; at 0:0002: CF=IRET.\n'
    '\t\tphysMem.state.RAM[0x0002]=0xCF; // IRET — stops NOP sled stack leak\n'
    '\t}\n'
    '}',
    'INT 75H stub at 0x6000 + INT6 IRET at 0:0002 at T=1.2s')


# ── Patch 9: enable FPU by default ───────────────────────────────────────────
# useFPU=false means every FPU instruction fires INT 7 (Device Not Available)
# → INT 7 handler at 0:0 (uninitialized dispatch trampoline) → BIOS loops.
# The FM Towns i486DX has an integrated FPU. Enable it by default.
townsparam = f'{build}/src/towns/townsparam/townsparam.h'
patch(townsparam,
    '\tbool useFPU=false;',
    '\tbool useFPU=true; // Patch 9: FM Towns i486DX has integrated FPU',
    'useFPU=true by default')


# ── Patch 10: implement SETALC (0xD6) ────────────────────────────────────────
# 0xD6 = SETALC (undocumented i486 instruction: Set AL from Carry flag).
# The FreeTOWNS free BIOS uses 0xD6 in its dispatch stubs.
# Currently handled as I486_RENUMBER_REALLY_UNDEFINED → prints error, fires INT6.
# With SETALC: AL = 0xFF if CF=1, else AL = 0x00. No flags changed. 1-byte, ~3 clocks.
run_h = f'{build}/src/cpu/i486runinstruction.h'
patch(run_h,
    '\tcase I486_RENUMBER_REALLY_UNDEFINED:\n'
    '\t\tstd::cout << "Undefined instruction (" << cpputil::Ustox(inst.RealOpCode()) << ") at " << cpputil::Ustox(state.CS().value) << ":" << cpputil::Uitox(state.EIP) << "\\n";\n'
    '\t\tInterrupt(INT_INVALID_OPCODE,mem,0,0,false);\n'
    '\t\tEIPIncrement=0;\n'
    '\t\tclocksPassed=ClocksForHandlingException();\n'
    '\t\t// clocksPassed=0; // Uncomment this line to abort on undefined instruction.\n'
    '\t\tbreak;',
    '\tcase I486_RENUMBER_REALLY_UNDEFINED:\n'
    '\t\tif(0xD6==inst.RealOpCode())\n'
    '\t\t{\n'
    '\t\t\t// SETALC: AL = CF ? 0xFF : 0x00 (undocumented on i486, used by FreeTOWNS BIOS)\n'
    '\t\t\tstate.EAX()=(state.EAX()&0xFFFFFF00)|(GetCF() ? 0xFF : 0x00);\n'
    '\t\t\tclocksPassed=3;\n'
    '\t\t}\n'
    '\t\telse\n'
    '\t\t{\n'
    '\t\t\tstd::cout << "Undefined instruction (" << cpputil::Ustox(inst.RealOpCode()) << ") at " << cpputil::Ustox(state.CS().value) << ":" << cpputil::Uitox(state.EIP) << "\\n";\n'
    '\t\t\tInterrupt(INT_INVALID_OPCODE,mem,0,0,false);\n'
    '\t\t\tEIPIncrement=0;\n'
    '\t\t\tclocksPassed=ClocksForHandlingException();\n'
    '\t\t\t// clocksPassed=0; // Uncomment this line to abort on undefined instruction.\n'
    '\t\t}\n'
    '\t\tbreak;',
    '0xD6 SETALC (AL=CF?0xFF:0x00)')