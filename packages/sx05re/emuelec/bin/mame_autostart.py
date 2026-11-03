#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Starts MAME games/systems without .cmd files, based on listmedia.txt (mame_libretro)
# Usage: mame_autostart.py /storage/roms/<system>/<game>.<ext>  -> prints path of the generated .cmd

import os, re, sys, gzip, json, shutil, struct, zipfile

TMPDIR    = "/tmp/mame_auto"
SAVEROOT  = "/storage/roms/savestates"
MAPFILE   = next((p for p in ("/storage/roms/mame_map.txt",
                              "/usr/bin/scripts/setup/mame_map.txt") if os.path.isfile(p)), None)
BOOT      = re.compile(r"program|boot|disk ?(1|a)\b|side ?(1|a)\b|1 of", re.I)
ROMPATH   = "/storage/roms/bios;/storage/roms"
LISTMEDIA = next((p for p in ("/storage/roms/listmedia.txt",
                              "/usr/bin/scripts/setup/listmedia.txt") if os.path.isfile(p)), None)

def parse_listmedia(path):
    with open(path, 'rb') as f: data = f.read()
    text = data.decode('utf-16', 'ignore') if b'\x00' in data[:4096] else data.decode('utf-8', 'ignore')
    systems, cur = {}, None
    for line in text.splitlines():
        t = line.split()
        if not t: continue
        if not line[0].isspace(): cur = t[0]
        b = next((i for i, x in enumerate(t) if x.startswith('(') and x.endswith(')') and x != '(none)'), None)
        if cur is None or b is None: continue
        systems.setdefault(cur, []).append((t[b].strip('()'), [x.lower() for x in t[b+1:] if x.startswith('.')]))
    return systems

def load_map():
    if not MAPFILE: return {}
    with open(MAPFILE) as f:
        return dict(l.strip().split('=', 1) for l in f if '=' in l and not l.startswith('#'))

# Tape: types pre (slowly, char by char), starts the tape, waits until it stops (or ~end), types post
LUA = """local nk, cas, state, last, still, buf, gap = manager.machine.natkeyboard, nil, 0, -1, 0, %s, 0
local post = %s
for _, c in pairs(manager.machine.cassettes) do cas = c end
local function typing()
    if buf == "" then return false end
    gap = gap + 1
    if gap >= 15 and nk.empty then nk:post(buf:sub(1, 1)); buf = buf:sub(2); gap = 0 end
    return true
end
sub = emu.add_machine_frame_notifier(function()
    if typing() then return end
    if state == 0 then cas:play(); state = 1
    elseif state == 1 then
        local p = cas.position
        still = (p == last and p > 0) and still + 1 or 0; last = p
        if still >= 30 or p >= cas.length - 1 then state = 2; still = 0 end
    elseif state == 2 then still = still + 1
        if still == 120 then buf = post; state = 3 end
    else sub:unsubscribe() end
end)
"""

def t77_type(data):
    """FM-7 .t77: decode pulses (2400 Hz = 0, 1200 Hz = 1, 8N2) up to the header block 01 3C 00, return file type"""
    pulses = struct.iter_unpack('>H', data[16:len(data) & ~1])
    bits, buf = [], bytearray()
    for (a,), (b,) in zip(pulses, pulses):
        a, b = a & 0x7fff, b & 0x7fff
        if not (16 <= a <= 60 and 16 <= b <= 60): bits.clear(); continue
        bits.append(1 if a + b >= 76 else 0)
        if len(bits) == 11:
            if bits[0] == 0 and bits[9] == bits[10] == 1:
                buf.append(sum(bits[1 + k] << k for k in range(8))); bits.clear()
                if buf[-13:-10] == b'\x01\x3c\x00': return buf[-1]
            else: bits.pop(0)
    return None

# Acorn Atom disk: *DOS, *RUN"<name>"; lowercase letters are pressed with SHIFT held
ATOM_LUA = """local nk, f, name, i, t = manager.machine.natkeyboard, {}, %s, 1, 0
for _, p in pairs(manager.machine.ioport.ports) do
    for n, fld in pairs(p.fields) do
        local k = n:match("^(%%a)$") or n:match("^(%%a) ") or (n:upper():find("SHIFT") and "SH")
        if k and not f[k] then f[k] = fld end
    end
end
nk:post('*DOS\\n*RUN"')
sub = emu.add_machine_frame_notifier(function()
    if not nk.empty then return end
    t = t + 1
    if i > #name then nk:post('"\\n'); sub:unsubscribe() return end
    local c = name:sub(i, i)
    if not c:match("%%l") then nk:post(c); i = i + 1; t = 0
    elseif t == 1 then f.SH:set_value(1); f[c:upper()]:set_value(1)
    elseif t == 10 then f[c:upper()]:clear_value(); f.SH:clear_value()
    elseif t == 20 then i = i + 1; t = 0 end
end)
"""

# Types text slowly, char by char (disk autoboot)
TYPE_LUA = """local nk, buf, gap = manager.machine.natkeyboard, %s, 0
sub = emu.add_machine_frame_notifier(function()
    gap = gap + 1
    if buf == "" then sub:unsubscribe() return end
    if gap >= 15 and nk.empty then nk:post(buf:sub(1, 1)); buf = buf:sub(2); gap = 0 end
end)
"""

def bbc_boot(dsk):
    """BBC Micro DFS disk: command for the catalogue boot option (1 LOAD, 2 RUN, 3 EXEC !BOOT)"""
    with open(dsk, 'rb') as f: opt = f.read(512)[256 + 6] >> 4 & 3
    return {1: '*LOAD !BOOT\n', 2: '*RUN !BOOT\n', 3: '*EXEC !BOOT\n'}.get(opt)

def atom_start(dsk):
    """Acorn Atom DFS disk: pick start file from the catalogue (known names first, else first BASIC file)"""
    with open(dsk, 'rb') as f: s0, s1 = f.read(256), f.read(256)
    files = [(s0[8 + 8 * k:15 + 8 * k].decode('latin1').rstrip(), s1[10 + 8 * k:12 + 8 * k]) for k in range(s1[5] // 8)]
    for want in ('runme', 'loader', 'boot', 'start', 'run', 'go', 'menu'):
        for n, ex in files:
            if n.lower() == want and ex == b'\x86\xce': return n
    return next((n for n, ex in files if ex == b'\x86\xce'), None)

def tape_autoboot(data, system=''):
    """Input before/after loading, from the tape header: Acorn UEF (Electron/BBC), Oric, FM-7, Colour Genie, MS-BASIC (D3), Lynx, CoCo/MC-10"""
    if data[:2] == b'\x1f\x8b': data = gzip.decompress(data)
    if system.startswith(('hec2hr', 'hec2mdhrx', 'hec2mx')):   # Hector HRX/MX menu: 5 = Hector 1 mode, 1 = cassette, then play
        return "51", ""
    if data[:9] == b'UEF File!' and system.startswith(('electron', 'bbc')):
        return '*TAPE\nCHAIN""\n', ""
    if data[:2] == b'\x66\x55':
        return "\n        SYSTEM\n" + data[2:8].decode('ascii', 'ignore').strip() + "\n", "/\n"
    if data[:1] == b'\x66' and data[1:2].isalpha():           # Colour Genie BASIC
        return "\n        CLOAD\n", "RUN\n"
    i = data.find(b'\x16\x16\x16\x24')                           # Oric .tap: sync, 24, ?, ?, type, autorun
    if 0 <= i < 64:
        return 'CLOAD""\n', "RUN\n" if data[i + 6] == 0 and data[i + 7] not in (0x80, 0xc7) else ""
    if data[:14] == b'XM7 TAPE IMAGE':                         # Fujitsu FM-7 .t77
        return ('LOADM"",,R\n', "") if t77_type(data) == 2 else ('RUN""\n', "")
    if b'\xd3' * 10 in data[:64]:                               # Microsoft BASIC (VG5000, SVI/MSX)
        return "CLOAD\n", "RUN\n"
    if b'\xd0' * 10 in data[:64]:                               # SVI/MSX machine code
        return 'BLOAD"CAS:",R\n', ""
    m = re.match(rb'"([^"]+)"([MB])', data)                     # Camputers Lynx .tap
    if m:
        name = m.group(1).decode('ascii', 'ignore')
        return (f'MLOAD "{name}"\n', "") if m.group(2) == b'M' else (f'LOAD "{name}"\n', "RUN\n")
    i = data.find(b'\x55\x3c\x00')
    if i < 0 or len(data) <= i + 12: return None
    return {0: ("CLOAD\n", "RUN\n"), 2: ("CLOADM:EXEC\n", "")}.get(data[i + 12])

def cass_lua(head, system=''):
    """Lua autoboot for tapes; without a recognized command only the tape is started"""
    ab = tape_autoboot(head or b'', system) or ("", "")
    lua = os.path.join(TMPDIR, "autoboot.lua")
    with open(lua, 'w') as f: f.write(LUA % (json.dumps(ab[0]), json.dumps(ab[1])))
    return f'-autoboot_delay 5 -autoboot_script {lua}'

def resolve_cmd(cmd):
    """Existing .cmd: use a same-named file next to it, else the quoted file it references"""
    stem = os.path.splitext(cmd)[0]
    for f in sorted(os.listdir(os.path.dirname(cmd))):
        p = os.path.join(os.path.dirname(cmd), f)
        if os.path.splitext(p)[0] == stem and not f.lower().endswith('.cmd'): return p
    with open(cmd, errors='ignore') as f:
        for path in re.findall(r'"([^"]+)"', f.read()):
            if os.path.isfile(path) and not path.lower().endswith('.cmd'): return path
    sys.exit(f"No game file found for {cmd}")

def build_cmd(rom, systems):
    folder = os.path.basename(os.path.dirname(rom))
    system, _, extra = load_map().get(folder, folder).partition(' ')
    if system == '*':                                          # file name is the machine (e.g. tvgames)
        return f'{os.path.splitext(os.path.basename(rom))[0]} -rp "{ROMPATH};{os.path.dirname(rom)}" -skip_gameinfo -noreadconfig {extra}'.strip()
    ext = os.path.splitext(rom)[1].lower()
    if system not in systems:
        sys.exit(f"{system} is not a MAME system in listmedia.txt")
    files, head = [rom], None
    forced = extra.split()[-1] if extra.split() and extra.split()[-1].startswith('-') else None
    if forced:                                                 # map ends with "-<media>": put file there
        extra = extra[:extra.rindex(forced)].strip()
        if forced == '-cass': extra = f'{extra} {cass_lua(b"", system)}'
        return f'{system} -rp "{ROMPATH}" -skip_gameinfo -noreadconfig {extra} {forced} "{rom}"'
    if ext == ".zip":
        z = zipfile.ZipFile(rom)
        names = [n for n in z.namelist() if not n.endswith('/')]
    for brief, exts in systems[system]:
        if ext != ".zip":
            if ext in exts:
                if brief == 'cass': head = open(rom, 'rb').read()
                break
            continue
        hits = sorted(n for n in names if os.path.splitext(n)[1].lower() in exts)
        if not hits and len(systems[system]) == 1: hits = sorted(names)   # only media type, extension irrelevant
        if not hits: continue
        hits.sort(key=lambda n: not BOOT.search(os.path.basename(n)))
        if brief == 'cass': head = z.read(hits[0])
        if len(hits) == 1 and not brief.startswith(('flop', 'cass')):   # neutral name, avoids softlist match
            files = [os.path.join(TMPDIR, "_media.zip")]
            if os.path.lexists(files[0]): os.remove(files[0])
            os.symlink(rom, files[0])
        else:                                                  # floppies/tapes/multiple files: extract, boot disk first
            out = os.path.join(TMPDIR, "_media")
            shutil.rmtree(out, ignore_errors=True)
            files = [z.extract(n, out) for n in hits]
        break
    else:
        sys.exit(f"No matching media type in {system} for {rom}")
    if system.startswith('atom') and brief.startswith('flop') and files[0].lower().endswith('.dsk') and '-autoboot' not in extra:
        name = atom_start(files[0])
        if name:
            lua = os.path.join(TMPDIR, "autoboot.lua")
            with open(lua, 'w') as f: f.write(ATOM_LUA % json.dumps(name))
            extra = f'{extra} -autoboot_delay 3 -autoboot_script {lua}'.strip()
    if system.startswith('bbc') and brief.startswith('flop') and files[0].lower().endswith(('.ssd', '.dsd')) and '-autoboot' not in extra:
        cmd = bbc_boot(files[0])
        if cmd:
            lua = os.path.join(TMPDIR, "autoboot.lua")
            with open(lua, 'w') as f: f.write(TYPE_LUA % json.dumps(cmd))
            extra = f'{extra} -autoboot_delay 3 -autoboot_script {lua}'.strip()
    slots = [b for b, x in systems[system] if b.rstrip('0123456789') == brief.rstrip('0123456789') and set(x) == set(exts)]
    args = ' '.join(f'-{b} "{f}"' for b, f in zip(slots or [brief], files))
    if brief == 'cass' and '-autoboot' not in extra:
        extra = f'{extra} {cass_lua(head, system)}'.strip()
    return f'{system} -rp "{ROMPATH}" -skip_gameinfo -noreadconfig {extra} {args}'.replace('  ', ' ')

if __name__ == "__main__":
    if len(sys.argv) != 2 or not LISTMEDIA:
        sys.exit("Usage: mame_autostart.py <rom>  (requires listmedia.txt)")
    rom = os.path.abspath(sys.argv[1])
    if rom.lower().endswith('.cmd'): rom = resolve_cmd(rom)
    os.makedirs(TMPDIR, exist_ok=True)
    cmd = build_cmd(rom, parse_listmedia(LISTMEDIA))
    content = os.path.join(TMPDIR, os.path.splitext(os.path.basename(rom))[0] + ".cmd")
    with open(content, 'w') as f: f.write(cmd + "\n")
    savedir = os.path.join(SAVEROOT, os.path.basename(os.path.dirname(rom)))
    os.makedirs(savedir, exist_ok=True)
    with open(os.path.join(TMPDIR, "append.cfg"), 'w') as f:
        f.write(f'config_save_on_exit = "false"\nsavefiles_in_content_dir = "false"\n'
                f'savefile_directory = "{savedir}"\nsavestate_directory = "{savedir}"\n')
    print(content)
