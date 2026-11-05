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

# Tape: types pre (slowly, char by char, "~" = 1 s pause), starts the tape, waits until it stops (or ~end, or the end of the signal),
# inserts and plays the next tape if given, types post
LUA = """local nk, cas, state, last, still, buf, gap = manager.machine.natkeyboard, nil, 0, -1, 0, %s, 0
local post, stop, nxt = %s, %s, %s
for _, c in pairs(manager.machine.cassettes) do cas = c end
local function typing()
    if buf == "" then return false end
    gap = gap + 1
    if gap >= 15 and nk.empty then
        if buf:sub(1, 1) == "~" then gap = -45 else nk:post(buf:sub(1, 1)); gap = 0 end
        buf = buf:sub(2)
    end
    return true
end
sub = emu.add_machine_frame_notifier(function()
    if typing() then return end
    if state == 0 then cas:play(); state = 1
    elseif state == 1 then
        local p = cas.position
        still = (p == last and p > 0) and still + 1 or 0; last = p
        if still >= 30 or p >= cas.length - 1 or (stop > 0 and p >= stop) then state = 2; still = 0 end
    elseif state == 2 then still = still + 1
        if still == 120 and nxt ~= "" then
            for _, i in pairs(manager.machine.images) do if i.device.tag:find("cass") then i:load(nxt) end end
            nxt = ""; state = 0; last = -1; still = 0
        elseif still == 120 then buf = post; state = 3 end
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

# Aquarius: RETURN at the start screen, CLOAD the _BAS loader, RUN, then insert the _A data tape for the loader's CLOAD*
# (every CLOAD waits for RETURN after "Press <PLAY>"; the tape has no motor control)
AQUARIUS_LUA = """local nk, cas, img, data = manager.machine.natkeyboard, nil, nil, %s
for _, c in pairs(manager.machine.cassettes) do cas = c end
for _, i in pairs(manager.machine.images) do if i.device.tag:find("cass") then img = i end end
local steps, n, t = {"\\n", "wait", "CLOAD\\n", "\\n", "play", "end", "RUN\\n"}, 1, 0
if data ~= "" then for _, x in ipairs({"load", "wait", "wait", "\\n", "play"}) do steps[#steps + 1] = x end end
sub = emu.add_machine_frame_notifier(function()
    t = t + 1
    local s = steps[n]
    if not s then sub:unsubscribe() return end
    if s == "play" then cas:play(); n = n + 1; t = 0
    elseif s == "load" then img:load(data); n = n + 1; t = 0
    elseif s == "end" then if t > 60 and cas.position >= cas.length - 0.1 then n = n + 1; t = 0 end
    elseif s == "wait" then if t >= 180 then n = n + 1; t = 0 end
    elseif t >= 60 and nk.empty then nk:post(s); n = n + 1; t = 0 end
end)
"""

# Steps of {frames to wait, text to type slowly}; {NAME} presses the input field NAME (e.g. {RETURN}), {PLAY} starts the tape
SEQ_LUA = """local nk, steps, n, t, buf, hold, f = manager.machine.natkeyboard, %s, 1, 0, "", nil, {}
for _, p in pairs(manager.machine.ioport.ports) do for k, x in pairs(p.fields) do f[k] = x end end
sub = emu.add_machine_frame_notifier(function()
    t = t + 1
    if hold then if t >= 10 then hold:clear_value(); hold = nil; t = 0 end
    elseif buf ~= "" then
        if t >= 15 and nk.empty then
            local name = buf:match("^{(.-)}")
            if name == "PLAY" then for _, c in pairs(manager.machine.cassettes) do c:play() end; buf = buf:sub(7)
            elseif name then hold = f[name]; hold:set_value(1); buf = buf:sub(#name + 3)
            else nk:post(buf:sub(1, 1)); buf = buf:sub(2) end
            t = 0
        end
    elseif not steps[n] then sub:unsubscribe()
    elseif t >= steps[n][1] then buf = steps[n][2]; n = n + 1; t = 0 end
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
    if system.startswith('trs80'):                             # Level II: MEMORY SIZE?, SYSTEM tapes (A5 55 name) or BASIC (A5 D3)
        i = data.find(b'\xa5')
        if 0 <= i < 1024 and data[i + 1:i + 2] == b'\x55':
            return "\n~~SYSTEM\n~" + data[i + 2:i + 8].decode('ascii', 'ignore').strip() + "\n", "/\n"
        if 0 <= i < 1024 and data[i + 1:i + 4] == b'\xd3' * 3:
            return "\n~~CLOAD\n", "RUN\n"
    if system.startswith(('laser', 'vz')):                     # VTech BASIC: CRUN loads and starts
        return "CRUN\n", ""
    if system.startswith('mz700'):                             # monitor: L loads and starts machine code
        return "L\n", ""
    if system.startswith('mz800'):                             # boot menu: C loads and starts from cassette
        return "C", ""
    if system.startswith('mz80k'):                             # monitor SP-1002: LOAD loads and starts machine code
        return "LOAD\n", ""
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
    if i < 0 or len(data) <= i + 12:
        return ("CLOAD\n", "RUN\n") if system.startswith(('alice', 'mc10')) else None   # e.g. .wav: no header to read
    return {0: ("CLOAD\n", "RUN\n"), 2: ("CLOADM:EXEC\n", "")}.get(data[i + 12])

def mc10_first_end(data):
    """Tape time (s) right after the first file's EOF block, as MAME's alice32 cassette format lays it out
    (1 s lead, 15 s silence + 128 sync bytes before name blocks and after name/EOF blocks), 0 if not found"""
    bt = lambda bs: sum(1 / 2400 if b >> i & 1 else 1 / 1200 for b in bs for i in range(8))
    off, t, last, t55 = 0, 1.0, 0, bt(b'\x55')
    while True:
        k = data.find(b'\x55\x3c', off)
        if k < 0 or k + 4 > len(data): return 0
        typ, ln = data[k + 2], data[k + 3]
        blk = data[k + 2:k + 5 + ln]
        if len(blk) < ln + 3 or sum(blk[:-1]) & 0xff != blk[-1]: off = k + 1; continue
        sync = len(data[off:k + 1]) - len(data[off:k + 1].lstrip(b'\x55'))
        t += 15 + 128 * t55 if last in (0, 0xff) or typ == 0 else 4 * sync * t55
        t += bt(b'\x55\x3c') + bt(blk) + t55
        if typ == 0xff: return round(t + 1, 1)
        last, off = typ, k + 5 + ln

def cass_lua(head, system='', nxt=''):
    """Lua autoboot for tapes; without a recognized command only the tape is started"""
    ab = tape_autoboot(head or b'', system) or ("", "")
    lua = os.path.join(TMPDIR, "autoboot.lua")
    stop = mc10_first_end(head) if system.startswith(('alice', 'mc10')) else 0   # type post in the silence after the first file
    with open(lua, 'w') as f: f.write(LUA % (json.dumps(ab[0]), json.dumps(ab[1]), stop, json.dumps(nxt)))
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
        p6 = system.startswith('pc6001') and brief == 'dump'    # PC-6001 tapes: snapshot device, needs a real file
        if brief.startswith('cdrm'):                          # CD images: extract all (.cue needs its .bin)
            out = os.path.join(TMPDIR, "_media")
            shutil.rmtree(out, ignore_errors=True)
            z.extractall(out)
            files = [os.path.join(out, n) for n in hits]
        elif len(hits) == 1 and not brief.startswith(('flop', 'cass')) and not p6:   # neutral name, avoids softlist match
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
    if system.startswith('aquarius') and brief == 'cass' and '-autoboot' not in extra:
        top = [f for f in files if os.path.dirname(f) == os.path.join(TMPDIR, "_media")] or files
        top.sort(key=lambda f: not f.upper().endswith('_BAS.CAQ'))   # loader first, data tape second
        files = top[:1]
        lua = os.path.join(TMPDIR, "autoboot.lua")
        with open(lua, 'w') as f: f.write(AQUARIUS_LUA % json.dumps(top[1] if len(top) > 1 else ""))
        extra = f'{extra} -autoboot_delay 3 -autoboot_script {lua}'.strip()
    if system.startswith('pc6001') and brief == 'dump' and '-autoboot' not in extra:   # answer "How Many Pages?", CLOAD, RUN after ~600 baud
        page = re.search(r'Page (\d)', os.path.basename(rom))
        wait = int(os.path.getsize(files[0]) / 60 * 60) + 600
        lua = os.path.join(TMPDIR, "autoboot.lua")
        with open(lua, 'w') as f: f.write(SEQ_LUA % ('{{60, "%s{RETURN}"}, {300, "cload{RETURN}"}, {%d, "run{RETURN}"}}' % (page.group(1) if page else "", wait)))
        extra = f'{extra} -autoboot_delay 3 -autoboot_script {lua}'.strip()
    slots = [b for b, x in systems[system] if b.rstrip('0123456789') == brief.rstrip('0123456789') and set(x) == set(exts)]
    args = ' '.join(f'-{b} "{f}"' for b, f in zip(slots or [brief], files))
    if system.startswith('mz2000') and brief == 'cass' and '-autoboot' not in extra:
        lua = os.path.join(TMPDIR, "autoboot.lua")                 # IPL: C boots from cassette
        with open(lua, 'w') as f: f.write(SEQ_LUA % '{{1, "C"}, {180, "{PLAY}"}}')   # press PLAY once "Make ready CMT" shows
        extra = f'{extra} -autoboot_delay 3 -autoboot_script {lua}'.strip()
    if brief == 'cass' and '-autoboot' not in extra:
        nxt = files[0].replace('(Loader)', '(Program)')               # two-part tapes: loader, then program
        extra = f'{extra} {cass_lua(head, system, nxt if nxt != files[0] and os.path.exists(nxt) else "")}'.strip()
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
