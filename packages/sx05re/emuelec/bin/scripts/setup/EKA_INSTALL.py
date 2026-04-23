#!/usr/bin/env python3
"""EmuELEC eka2l1 firmware installer, SIS game installer, device manager, UID launcher creator & gamelist generator (controller UI)."""
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# Created with Claude.ai

import os, glob, sys, time, subprocess, shutil, re, datetime, xml.etree.ElementTree as ET, struct, zipfile
from typing import List, Optional, Tuple, Dict, Set
from evdev import InputDevice, list_devices, ecodes as e

# === PATHS ===
EKA_EXE = "/usr/bin/eka2l1/eka2l1_sdl2"
EKA_CONFIG = "/storage/.config/eka2l1"
EKA_BIOS = "/storage/roms/bios/eka2l1"
EKA_ROMS = "/storage/roms/ngage"
EKA_LOG = "/emuelec/logs/eka2l1-install.log"
EKA_YML = os.path.join(EKA_CONFIG, "config.yml")
MEDIA_IMG = os.path.join(EKA_ROMS, "media", "images")
MEDIA_VID = os.path.join(EKA_ROMS, "media", "videos")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
VID_EXTS = (".mp4", ".avi", ".mkv", ".mov", ".wmv")

class UserQuit(Exception): pass
class GoBack(Exception): pass

controller = None

class ControllerInput:
    def __init__(self, pref: Optional[str] = None):
        self.dev = self._wait(pref)
        self.path = getattr(self.dev, "path", pref)
        self.hat = [0, 0]

    def _wait(self, pref: Optional[str]) -> InputDevice:
        print("\nWaiting for controller...", flush=True)
        if pref:
            try: return InputDevice(pref)
            except OSError: pass
        while True:
            for p in list_devices():
                try:
                    dev = InputDevice(p)
                    caps = dev.capabilities()
                    keys = caps.get(e.EV_KEY, [])
                    absv = caps.get(e.EV_ABS, [])
                    if any(b in keys for b in (e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST, e.BTN_DPAD_UP, e.BTN_DPAD_DOWN, e.BTN_DPAD_LEFT, e.BTN_DPAD_RIGHT)) or any(a in absv for a in (e.ABS_HAT0X, e.ABS_HAT0Y)):
                        print(f"Controller: {dev.name}", flush=True)
                        return dev
                except OSError: continue
            time.sleep(1)

    def reconnect(self):
        old = self.path
        self.close()
        self.hat = [0, 0]
        print("\nController disconnected. Reconnecting...", flush=True)
        self.dev = self._wait(old)
        self.path = getattr(self.dev, "path", old)

    def read(self) -> str:
        while True:
            try:
                for ev in self.dev.read_loop():
                    if ev.type == e.EV_KEY and ev.value == 1:
                        c = ev.code
                        if c in (e.BTN_DPAD_UP, e.KEY_UP): return 'up'
                        if c in (e.BTN_DPAD_DOWN, e.KEY_DOWN): return 'down'
                        if c in (e.BTN_DPAD_LEFT, e.KEY_LEFT): return 'left'
                        if c in (e.BTN_DPAD_RIGHT, e.KEY_RIGHT): return 'right'
                        if c in (e.BTN_SOUTH, e.BTN_START, e.KEY_ENTER): return 'a'
                        if c in (e.BTN_EAST, e.KEY_ESC, e.KEY_BACKSPACE): return 'b'
                        if c == e.BTN_NORTH: return 'y'
                        if c == e.BTN_WEST: return 'x'
                        if c in (e.BTN_SELECT, e.BTN_MODE): return 'select'
                    if ev.type == e.EV_ABS:
                        if ev.code == e.ABS_HAT0Y:
                            v = ev.value
                            if v < 0 and self.hat[1] >= 0: self.hat[1] = v; return 'up'
                            if v > 0 and self.hat[1] <= 0: self.hat[1] = v; return 'down'
                            if v == 0: self.hat[1] = 0
                        if ev.code == e.ABS_HAT0X:
                            v = ev.value
                            if v < 0 and self.hat[0] >= 0: self.hat[0] = v; return 'left'
                            if v > 0 and self.hat[0] <= 0: self.hat[0] = v; return 'right'
                            if v == 0: self.hat[0] = 0
            except OSError as ex:
                if getattr(ex, "errno", None) == 19:
                    self.reconnect()
                    continue
                raise

    def close(self):
        try: self.dev.close()
        except: pass

def init_controller(p: Optional[str] = None):
    global controller
    controller = ControllerInput(p)

def unblank():
    for p in ("/sys/class/graphics/fb0/blank", "/sys/class/graphics/fb1/blank"):
        try:
            with open(p, "w") as f: f.write("0")
        except: pass

def cls():
    unblank()
    print("\033[2J\033[H", end='', flush=True)

MENU_WIDTH = 100

def _fit(line: str, width: int) -> str:
    return line[:width].ljust(width)

def _frame(text: str, char: str = "-", width: int = MENU_WIDTH) -> int:
    print(char * width)
    print(text[:width].center(width))
    print(char * width)
    return width

def menu(title: str, opts: List[str], sel: int = 0, info: str = "", off: int = 0, vis: int = 20, checks: Optional[Set[int]] = None):
    cls()
    width = MENU_WIDTH

    _frame(f"E K A 2 L 1   C O M M A N D E R  -  {title}", "=", width)

    if info:
        for line in info.split('\n'):
            if len(line) > width:
                line = line[:width-3] + "..."
            print(_fit(line, width))
        print()

    end = min(off + vis, len(opts))
    for i in range(off, end):
        marker = "  > " if i == sel else "    "
        mark = f"{'[x]' if i in checks else '[ ]'} " if checks is not None else ""
        line = marker + mark + opts[i]
        if len(line) > width:
            line = line[:width-3] + "..."
        print(_fit(line, width))

    if end < len(opts):
        print(_fit("    ...", width))

    footer = "D-Pad: Navigate | A: Select | B: Back | Select: Quit" if checks is None else \
             "D-Pad: Navigate | A: Toggle | X: Toggle All | Y: Confirm | B: Back | Select: Quit"

    _frame(footer, "-", width)
    sys.stdout.flush()

def select(title: str, items: List[str], info: str = "", vis: int = 20) -> Optional[int]:
    if not items: return None
    sel, off, tot = 0, 0, len(items)
    while True:
        off = max(0, min(max(0, tot - vis), sel - vis + 1 if sel >= off + vis else sel if sel < off else off))
        menu(title, items, sel, info, off, vis)
        k = controller.read()
        if k == 'select': raise UserQuit()
        elif k == 'up': sel = max(0, sel - 1)
        elif k == 'down': sel = min(tot - 1, sel + 1)
        elif k == 'left': sel = max(0, sel - vis)
        elif k == 'right': sel = min(tot - 1, sel + vis)
        elif k == 'a': return sel
        elif k == 'b': raise GoBack()

def ok(title: str, msg: str) -> None:
    while True:
        menu(title, ["OK"], 0, msg)
        k = controller.read()
        if k == 'select': raise UserQuit()
        if k in ('a', 'b'): return

def confirm(title: str, msg: str, yes: bool = True) -> bool:
    opts, sel = ["Yes", "No"], 0 if yes else 1
    while True:
        menu(title, opts, sel, msg)
        k = controller.read()
        if k == 'select': raise UserQuit()
        elif k in ('up', 'down'): sel = 1 - sel
        elif k == 'a': return sel == 0
        elif k == 'b': return False

def multi_select(title: str, items: List[str], info: str = "", vis: int = 16) -> Optional[List[int]]:
    if not items: return []
    sel, off, tot, chk = 0, 0, len(items), set()
    while True:
        off = max(0, min(max(0, tot - vis), sel - vis + 1 if sel >= off + vis else sel if sel < off else off))
        menu(title, items, sel, info, off, vis, chk)
        k = controller.read()
        if k == 'select': raise UserQuit()
        elif k == 'up': sel = max(0, sel - 1)
        elif k == 'down': sel = min(tot - 1, sel + 1)
        elif k == 'left': sel = max(0, sel - vis)
        elif k == 'right': sel = min(tot - 1, sel + vis)
        elif k == 'a': chk.discard(sel) if sel in chk else chk.add(sel)
        elif k == 'x': chk.clear() if len(chk) == tot else chk.update(range(tot))
        elif k == 'y': return sorted(chk)
        elif k == 'b': raise GoBack()

def browse(prompt: str, start: str, exts: Optional[List[str]] = None) -> str:
    cur = os.path.abspath(start)
    while True:
        try:
            dirs = sorted(d for d in os.listdir(cur) if os.path.isdir(os.path.join(cur, d)) and not d.startswith('.'))
        except: dirs = []
        opts = []
        if exts is None:
            opts.append("[Use This Directory]")
        else:
            has = any(f.lower().endswith(tuple(exts)) for f in os.listdir(cur) if os.path.isfile(os.path.join(cur, f)))
            if has:
                opts.append(f"[Use This Directory]  ({'/'.join(e.lstrip('.').upper() for e in exts)} found)")
        if cur != "/":
            opts.append("[.. Parent]")
        opts.extend(dirs)
        idx = select(prompt, opts, f"Current: {cur}")
        if idx is None: raise GoBack()
        sel = opts[idx]
        if sel.startswith("[Use"):
            return cur
        elif sel == "[.. Parent]":
            parent = os.path.dirname(cur)
            if parent and parent != cur:
                cur = parent
        else:
            cur = os.path.join(cur, sel)

def log(msg: str):
    try:
        with open(EKA_LOG, "a") as f:
            f.write(msg + "\n")
    except:
        pass

def run_eka(args: List[str], timeout: int = 120) -> int:
    import threading
    cmd = [EKA_EXE] + args
    log("Run: " + " ".join(cmd))
    stop = threading.Event()

    spinner = "|/-\\"

    def _spin():
        i = 0
        while not stop.wait(2.0):
            unblank()
            print(f"\r  {spinner[i % 4]} Working...", end='', flush=True)
            i += 1

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        with open(EKA_LOG, "a") as logf:
            r = subprocess.run(cmd, cwd=EKA_CONFIG, timeout=timeout, stdout=logf, stderr=logf)
        return r.returncode
    except subprocess.TimeoutExpired:
        log("Timeout")
        return 124
    except Exception as ex:
        log(f"Err: {ex}")
        return 1
    finally:
        stop.set()
        t.join(timeout=3)
        print("\r" + " " * 20 + "\r", end='', flush=True)
        
def run_cap(args: List[str], timeout: int = 120) -> Tuple[int, str]:
    cmd = [EKA_EXE] + args
    log("Cap: " + " ".join(cmd))
    try:
        r = subprocess.run(cmd, cwd=EKA_CONFIG, timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        out = r.stdout or ""
        if out: log(out.rstrip())
        return r.returncode, out
    except subprocess.TimeoutExpired as ex:
        out = (ex.stdout or "") if isinstance(ex.stdout, str) else ""
        if out: log(out.rstrip())
        log("Timeout")
        return 124, out  # BUGFIX: Return timeout code
    except Exception as ex:
        log(f"Err: {ex}")
        return 1, ""

def ok_ret(ret: int) -> bool:
    return ret in (0, -6, -11, 245)

# === DEVICE ===
def get_dev_idx() -> Optional[int]:
    if not os.path.exists(EKA_YML): return None
    try:
        with open(EKA_YML, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r'^\s*device\s*:\s*([0-9]+)\s*$', line)
                if m: return int(m.group(1))
    except Exception as ex: log(f"cfg read err: {ex}")
    return None

def get_dev_name() -> Optional[str]:
    idx = get_dev_idx()
    if idx is None: return None
    dy = os.path.join(EKA_CONFIG, "data", "devices.yml")
    if not os.path.isfile(dy): return None
    try:
        with open(dy) as f:
            i = 0
            for line in f:
                s = line.rstrip()
                if s and not s.startswith(" ") and s.endswith(":"):
                    if i == idx: return s[:-1]
                    i += 1
    except: pass
    return None

def set_dev_idx(index: int) -> None:
    os.makedirs(EKA_CONFIG, exist_ok=True)
    lines = []
    if os.path.exists(EKA_YML):
        try:
            with open(EKA_YML, "r", encoding="utf-8") as f: lines = f.readlines()
        except Exception as ex:
            log(f"cfg read err: {ex}")
            lines = []
    replaced = False
    new_lines = []
    for line in lines:
        if re.match(r'^\s*device\s*:\s*[0-9]+\s*$', line):
            new_lines.append(f"device: {index}\n")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        if new_lines and not new_lines[-1].endswith("\n"): new_lines[-1] += "\n"
        new_lines.append(f"device: {index}\n")
    with open(EKA_YML, "w", encoding="utf-8") as f: f.writelines(new_lines)
    log(f"Set device: {index}")

def get_valid_devs() -> List[Tuple[int, str]]:
    z_base = os.path.join(EKA_CONFIG, "data", "drives", "z")
    if not os.path.isdir(z_base): return []
    try:
        z_dirs = {d.lower(): d for d in os.listdir(z_base) if os.path.isdir(os.path.join(z_base, d))}
    except Exception as ex: log(f"z read err: {ex}"); return []
    if not z_dirs: return []
    devices = []
    dy = os.path.join(EKA_CONFIG, "data", "devices.yml")
    if os.path.isfile(dy):
        try:
            with open(dy) as f:
                i = 0
                for line in f:
                    s = line.rstrip()
                    if s and not s.startswith(" ") and s.endswith(":"):
                        name = s[:-1]
                        if name.lower() in z_dirs:
                            devices.append((i, name))
                            log(f"Valid dev {i}: {name}")
                        i += 1
        except Exception as ex: log(f"dev.yml err: {ex}")
    log(f"Valid devs: {len(devices)}")
    return devices

def pick_dev(action: str) -> bool:
    cls(); print("Loading devices...", flush=True)
    devs = get_valid_devs()
    if not devs:
        ok("Error", f"No devices found.\nInstall firmware first.\n\nLog: {EKA_LOG}")
        return False
    cur = get_dev_idx()
    opts = [f"{n} : {name}{'  [CURRENT]' if cur == n else ''}" for n, name in devs]
    idx = select("Select Device", opts, f"For: {action}", 16)
    if idx is None: return False
    n, name = devs[idx]
    if not confirm("Confirm", f"Use for: {action}\n\n{n} : {name}"): return False
    try:
        set_dev_idx(n)
        log(f"Set dev {n} for: {action}")
        return True
    except Exception as ex:
        log(f"Set dev err: {ex}")
        ok("Error", f"Could not set device\n\nLog: {EKA_LOG}")
        return False

def change_dev():
    cls(); print("Loading devices...", flush=True)
    devs = get_valid_devs()
    if not devs:
        ok("Error", f"No devices found.\nInstall firmware first.\n\nLog: {EKA_LOG}")
        return
    cur = get_dev_idx()
    opts = [f"{n} : {name}{'  [CURRENT]' if cur == n else ''}" for n, name in devs]
    idx = select("Change Device", opts, "Select device for config.yml", 16)
    if idx is None: return
    n, name = devs[idx]
    if not confirm("Confirm", f"Set device?\n\n{n} : {name}"): return
    try:
        set_dev_idx(n)
        ok("Done", f"Device changed.\n\ndevice: {n}")
    except Exception as ex:
        log(f"cfg write err: {ex}")
        ok("Error", f"Could not write config.yml\n\nLog: {EKA_LOG}")

# === LOWERCASE ===
def lower_tree(root: str):
    root = os.path.abspath(root)
    final = root
    def tmp_name(p):
        b = p + ".__tmp__"
        i = 1
        while os.path.exists(b):
            b = f"{p}.__tmp__{i}"; i += 1
        return b
    def ren(src, dst):
        if src == dst: return src
        sa, da = os.path.abspath(src), os.path.abspath(dst)
        if sa.lower() == da.lower():
            t = tmp_name(sa)
            os.rename(sa, t)
            os.rename(t, da)
            return da
        if os.path.exists(da): raise FileExistsError(f"Exists: {da}")
        os.rename(sa, da)
        return da
    renamed, errors = [], []
    for cr, ds, fs in os.walk(root, topdown=False):
        for n in fs:
            s, d = os.path.join(cr, n), os.path.join(cr, n.lower())
            if s != d:
                try: renamed.append((s, ren(s, d)))
                except Exception as ex: errors.append(f"File: {s}\n-> {d}\n{ex}"); log(f"ERR file: {s} -> {d}: {ex}")
        for n in ds:
            s, d = os.path.join(cr, n), os.path.join(cr, n.lower())
            if s != d:
                try: renamed.append((s, ren(s, d)))
                except Exception as ex: errors.append(f"Dir: {s}\n-> {d}\n{ex}"); log(f"ERR dir: {s} -> {d}: {ex}")
    p, b = os.path.dirname(root), os.path.basename(root)
    lb = b.lower()
    if b != lb:
        try:
            final = ren(root, os.path.join(p, lb))
            renamed.append((root, final))
        except Exception as ex: errors.append(f"Root: {root}\n-> {os.path.join(p, lb)}\n{ex}"); log(f"ERR root: {root}: {ex}")
    return renamed, errors, final

def conv_lower():
    try:
        td = browse("Lowercase: Select Folder", os.path.join(EKA_CONFIG, "data"))
    except GoBack: return
    warn = ""
    at = os.path.abspath(td)
    if at == "/": warn = "\n\nWARNING: Will rename from root!"
    elif at == "/storage": warn = "\n\nWARNING: Will rename all of /storage!"
    if not confirm("Confirm", f"Lowercase recursively?\n\n{td}{warn}"): return
    cls(); print("Converting...", flush=True)
    renamed, errors, final = lower_tree(td)
    if errors:
        ok("Result", f"Errors occurred.\n\nRenamed: {len(renamed)}\nErrors: {len(errors)}\n\n" + "\n\n".join(errors[:3]) + (f"\n\n... +{len(errors)-3}" if len(errors) > 3 else "") + f"\n\nLog: {EKA_LOG}")
        return
    if not renamed:
        ok("Result", f"Nothing to rename.\nAll lowercase in:\n{td}")
        return
    ok("Result", f"Converted: {len(renamed)} items\n\nFinal: {final}\n\nLog: {EKA_LOG}")

# === FIRMWARE ===
def install_fw():
    try:
        bd = browse("Firmware: Select Dir", EKA_BIOS)
    except GoBack: return
    rp = sorted(glob.glob(os.path.join(bd, "*.rpkg")) + glob.glob(os.path.join(bd, "*.RPKG")))
    rm = sorted(glob.glob(os.path.join(bd, "*.rom")) + glob.glob(os.path.join(bd, "*.ROM")))
    if not rp: ok("Error", f"No .rpkg in:\n{bd}"); return
    if not rm: ok("Error", f"No .rom in:\n{bd}"); return
    rpkg = rp[0]
    if len(rp) > 1:
        try:
            i = select("Select RPKG", [os.path.basename(f) for f in rp])
            if i is None: return
            rpkg = rp[i]
        except GoBack: return
    rom = rm[0]
    if len(rm) > 1:
        try:
            i = select("Select ROM", [os.path.basename(f) for f in rm])
            if i is None: return
            rom = rm[i]
        except GoBack: return
    if not confirm("Install", f"RPKG: {os.path.basename(rpkg)}\nROM:  {os.path.basename(rom)}\n\nInstall?"): return
    sd = os.path.join(EKA_CONFIG, "data", "roms", "rm-409")
    os.makedirs(sd, exist_ok=True)
    try: shutil.copy2(rom, os.path.join(sd, os.path.basename(rom)))
    except: pass
    cls(); print("Installing firmware...", flush=True)
    print(f"  {os.path.basename(rpkg)}\n  {os.path.basename(rom)}\n\nThis may take a few minutes...", flush=True)
    ret = run_eka(["--installdevice", rpkg, rom], timeout=1800)
    if ok_ret(ret):
        _autoset_dev()
        ok("Done", "Firmware installed!\n\n(Non-zero exit is normal)\n\nDevice auto-set.")
    else:
        ok("Error", f"Failed (code {ret})\n\nLog: {EKA_LOG}")

# === SIS DETECTION ===
_SIS_V2 = b'\x7a\x1a\x20\x10'
_ZIP = b'\x50\x4b\x03\x04'
_SISV1_UIDS: Set[int] = {0x1000006D, 0x10003A12}

_SIS_PLAT_UIDS: List[Tuple[bytes, str]] = [
    (b'\x5f\x31\x28\x10', "s60v5"), (b'\x90\x30\x28\x10', "s60v5"), (b'\x0b\x6b\x28\x10', "s60v5"),
    (b'\x61\x79\x1f\x10', "s60v3"), (b'\xbe\x32\x20\x10', "s60v3"), (b'\xae\x52\x27\x10', "s60v3"), (b'\x13\x35\x28\x10', "s60v3"),
    (b'\x78\x3b\x00\x20', "s60v3"), (b'\x79\x3b\x00\x20', "s60v3"), (b'\x7a\x3b\x00\x20', "s60v3"), (b'\x7b\x3b\x00\x20', "s60v3"),
    (b'\xd2\x8e\x1f\x10', "s60v2"),
    (b'\x88\x6f\x1f\x10', "s60v1"),
    (b'\x00\x63\x1f\x10', "uiq3"), (b'\xdf\x63\x1f\x10', "uiq3"),
]

_PLAT_INFO: Dict[str, Tuple[str, str]] = {
    "s60v1": ("S60 1st Edition", "N-Gage 1 (NEM-4 / RM-26)"),
    "s60v2": ("S60 2nd Edition", "N-Gage 1 (NEM-4 / RM-26)"),
    "s60v3": ("S60 3rd Edition", "N-Gage 2.0 (RM-409)"),
    "s60v5": ("S60 5th Edition", "S60v5 (RM-356)"),
    "uiq3": ("UIQ3", "UIQ3 Device"),
    "sisv1": ("S60 1st/2nd Edition", "N-Gage 1 (NEM-4 / RM-26)"),
    "unknown": ("Unknown Format", "—"),
}
_PLAT_ORD = ["s60v1", "s60v2", "s60v3", "s60v5", "uiq3", "sisv1", "unknown"]
_UID3_RNG = [(0x20000000, 0x2FFFFFFF, "s60v3"), (0xA0000000, 0xAFFFFFFF, "s60v3"), (0x10000000, 0x1FFFFFFF, "s60v1")]

def _det_sisv2(data: bytes) -> str:
    if len(data) < 12: return "unknown"
    chunk, max_scan, scanned, offset, overlap = 262144, 4 * 1024 * 1024, 0, 0, b""
    while scanned < max_scan and offset < len(data):
        c = data[offset:offset + chunk]
        w = overlap + c
        for sig, key in _SIS_PLAT_UIDS:
            if sig in w:
                log(f"Detected {key} via {sig.hex()}")
                return key
        overlap = w[-3:] if len(w) >= 3 else w
        scanned += len(c); offset += chunk
    uid3 = struct.unpack_from("<I", data, 8)[0]
    for lo, hi, key in _UID3_RNG:
        if lo <= uid3 <= hi:
            log(f"Detected {key} via UID3 0x{uid3:08X}")
            return key
    log(f"Default s60v3 (UID3 0x{uid3:08X})")
    return "s60v3"

def _det_sis(data: bytes) -> str:
    if len(data) < 4: return "unknown"
    h = data[:12]
    if len(h) >= 8:
        uid2 = struct.unpack_from("<I", h, 4)[0]
        if uid2 in _SISV1_UIDS:
            log(f"sisv1 UID2 0x{uid2:08X}")
            return "sisv1"
    if h[:4] != _SIS_V2:
        log(f"Unknown magic {h[:4].hex()}")
        return "unknown"
    return _det_sisv2(data)

def det_plat(path: str) -> str:
    try:
        with open(path, "rb") as f: magic = f.read(4)
    except Exception as ex:
        log(f"Cannot read {path}: {ex}")
        return "unknown"
    if len(magic) < 4: return "unknown"
    if magic == _ZIP:
        log(f"SISX: {path}")
        try:
            with zipfile.ZipFile(path, "r") as zf:
                sn = next((n for n in zf.namelist() if n.lower() == "content.sis"), None)
                if sn is None: sn = next((n for n in zf.namelist() if n.lower().endswith(".sis")), None)
                if sn:
                    log(f"Extracted {sn}")
                    return _det_sis(zf.read(sn))
                log("No .sis in SISX")
        except Exception as ex: log(f"SISX err: {ex}")
        return "unknown"
    log(f"SIS: {path}")
    try:
        with open(path, "rb") as f: return _det_sis(f.read(4 * 1024 * 1024))
    except Exception as ex: log(f"SIS err: {ex}"); return "unknown"

def plat_hint(path: str) -> str:
    k = det_plat(path)
    p = _PLAT_INFO.get(k, _PLAT_INFO["unknown"])
    return f"{p[0]}  →  {p[1]}"

def find_sis(root: str, recursive: bool = True) -> List[str]:
    if recursive:
        return sorted(
            (os.path.join(cr, n) for cr, _, fs in os.walk(root)
             for n in fs if n.lower().endswith(('.sis', '.sisx'))),
            key=str.lower
        )
    else:
        return sorted(
            (os.path.join(root, n) for n in os.listdir(root)
             if os.path.isfile(os.path.join(root, n))
             and n.lower().endswith(('.sis', '.sisx'))),
            key=str.lower
        )



def rel_path(path: str, base: str) -> str:
    try: return os.path.relpath(path, base).replace("\\", "/")
    except: return os.path.basename(path)

# === SYSTEM APPS ===
def is_sys(name: str) -> bool:
    n = name.lower().strip()
    core = {'', 'sysap', 'starter', 'installer', 'applications', 'app. manager', 'app manager', 'settings',
            'configuration', 'sysstart', 'sysinit', 'system', 'system apps', 'system programs', 'programs'}
    phone = {'telephone', 'phone', 'dialer', 'call divert', 'call transfer', 'voice mailbox', 'voicemail',
             'speed dial', 'fixed dialling', 'auto lock', 'autolock', 'device lock', 'pin', 'sim services',
             'sim directory', 'sim toolkit', 'ussd', 'cell broadcast', 'push viewer', 'pushviewer', 'messaging',
             'sms', 'mms', 'email', 'e-mail', 'mail', 'nokia messaging'}
    pim = {'contacts', 'phonebook', 'address book', 'calendar', 'scheduler', 'to-do', 'todo', 'tasks', 'notes',
           'notepad', 'memo', 'memos', 'clock', 'alarm clock', 'world clock', 'calculator', 'converter',
           'unit converter', 'currency converter'}
    media = {'realone player', 'realplayer', 'music player', 'audio player', 'video player', 'videoui', 'gallery',
             'images', 'photos', 'radio', 'visual radio', 'internet radio', 'fm radio', 'recorder', 'sound recorder',
             'voice recorder', 'camera', 'camcorder', 'video recorder', 'multimedia', 'media player', 'music',
             'videos', 'podcasts', 'ovi music', 'nokia music'}
    conn = {'bluetooth', 'irda', 'infrared', 'usb', 'wlan', 'wi-fi', 'wifi', 'connections', 'connectivity',
            'data call', 'gprs', 'edge', '3g', 'network', 'sync', 'synchronization', 'pc suite', 'ovi suite'}
    web = {'web', 'browser', 'internet', 'services', 'download', 'downloads', 'ovi store', 'nokia store',
           'download!', 'get it now', 'ovi music store', 'nokia music store', 'search', 'search online'}
    files = {'file manager', 'files', 'memory', 'memory card', 'mmc', 'mass storage', 'memory manager',
             'application manager', 'sw update', 'software update', 'firmware update'}
    help_a = {'help', 'user guide', 'tutorial', 'about', 'about product', 'about phone', 'device info',
              'phone info', 'license', 'activation', 'register', 'registration'}
    ngage = {'discover n-gage', 'n-gage', 'ngage', 'n-gage app', 'ngage app', 'game launcher', 'my games',
             'games', 'play', 'arena', 'n-gage arena', 'ngage arena', 'friends', 'n-gage friends', 'profile',
             'n-gage profile', 'shop', 'n-gage shop', 'ngage shop'}
    display = {'screensaver', 'screen saver', 'themes', 'wallpaper', 'background', 'display', 'home screen',
               'active idle', 'active standby', 'today', 'dashboard', 'widgets'}
    utils = {'zip manager', 'zip', 'compress', 'decompress', 'backup', 'restore', 'device manager', 'task manager',
             'processes', 'logs', 'call log', 'call logs', 'message log', 'data counter', 'packet data',
             'connection manager', 'net monitor'}
    nokia = {'ovi', 'nokia', 'ovi maps', 'maps', 'gps', 'navigation', 'ovi contacts', 'ovi share', 'ovi sync',
             'nokia maps', 'nokia email', 'nokia messaging', 'nokia internet radio', 'nokia photo browser',
             'nokia custom dictionary', 'quickoffice', 'adobe reader', 'pdf reader'}
    return n in (core | phone | pim | media | conn | web | files | help_a | ngage | display | utils | nokia)

# === APP HELPERS ===
def parse_apps(out: str) -> List[Tuple[str, str]]:
    apps = []
    for line in out.splitlines():
        line = line.strip()
        m = re.match(r'^\d+\s*:\s*(.*?)\s*\(UID:\s*(0x[0-9a-fA-F]+)\)\s*$', line)
        if m:
            apps.append((m.group(1).strip(), m.group(2).strip().lower()))
    return apps

def get_apps() -> dict:
    ret, out = run_cap(["--listapp"])
    if ret != 0 and not out.strip(): return {}
    return {uid: name.strip() for name, uid in parse_apps(out)}

def find_new_app(before: dict, after: dict) -> Optional[Tuple[str, str]]:
    new = [u for u in after if u not in before]
    if len(new) == 1: return after[new[0]], new[0]
    cands = [(after[u], u) for u in new if not is_sys(after[u])]
    return cands[0] if cands else None

def sanitize(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', '_', name).replace("'", "_")
    name = re.sub(r'\s+', ' ', name).strip()
    while name.startswith('.'): name = '_' + name[1:]
    return name or 'unnamed'

# === MEDIA ===
def _media_cache(media_dir: str) -> Dict[str, str]:
    if not os.path.isdir(media_dir): return {}
    try:
        return {os.path.splitext(f)[0].lower(): f for f in os.listdir(media_dir)
                if os.path.isfile(os.path.join(media_dir, f))}
    except Exception as ex: log(f"Media cache err: {ex}"); return {}

def _find_media(name: str, cache: Dict[str, str], media_dir: str, out_dir: str) -> str:
    sn = sanitize(name).lower()
    if sn in cache:
        full = os.path.join(media_dir, cache[sn])
        try:
            r = os.path.relpath(full, out_dir).replace("\\", "/")
            return f"./{r}" if not r.startswith(("./", "/")) else r
        except: pass
    fb = "ngage.png" if media_dir == MEDIA_IMG else "ngage.mp4"
    fb_path = os.path.join(media_dir, fb)
    if os.path.exists(fb_path):
        try:
            r = os.path.relpath(fb_path, out_dir).replace("\\", "/")
            return f"./{r}" if not r.startswith(("./", "/")) else r
        except: pass
    return f"./media/{'images' if media_dir == MEDIA_IMG else 'videos'}/{fb}"

def _copy_media(src_folder: str, app_name: str, media_dir: str, exts: Tuple[str, ...]) -> bool:
    try:
        cands = sorted([os.path.join(src_folder, n) for n in os.listdir(src_folder)
                       if os.path.isfile(os.path.join(src_folder, n)) and n.lower().endswith(exts)],
                      key=lambda p: os.path.basename(p).lower())
    except: return False
    if not cands: return False
    os.makedirs(media_dir, exist_ok=True)
    src = cands[0]
    ext = os.path.splitext(src)[1].lower()
    target = os.path.join(media_dir, f"{sanitize(app_name)}{ext}")
    try:
        shutil.copy2(src, target)
        log(f"Media: {src} -> {target}")
        return True
    except Exception as ex: log(f"Media err: {ex}"); return False

# === GAMELIST ===
def _parse_gamelist(path: str) -> Dict[str, List[str]]:
    entries = {}
    if not os.path.exists(path): return entries
    try:
        tree = ET.parse(path)
        for game in tree.getroot().findall('game'):
            pe = game.find('path')
            if pe is not None and pe.text:
                key = pe.text.strip().lower()
                xml_str = ET.tostring(game, encoding='unicode')
                entries[key] = ['\t' + line for line in xml_str.strip().split('\n')]
    except Exception as ex: log(f"Parse gamelist err: {ex}")
    return entries

def _update_entry(lines: List[str], name: str, dev: str, img: str, vid: str) -> List[str]:
    updated = []
    for line in lines:
        if '<name>' in line and '</name>' in line:
            line = f'\t\t<name>{xml_esc(name)}</name>'
        elif '<desc>' in line and '</desc>' in line:
            d = f"[{dev.upper()}] {name}" if dev else name
            line = f'\t\t<desc>{xml_esc(d)}</desc>'
        elif '<image>' in line and '</image>' in line:
            line = f'\t\t<image>{xml_esc(img)}</image>'
        elif '<video>' in line and '</video>' in line:
            line = f'\t\t<video>{xml_esc(vid)}</video>'
        updated.append(line)
    return updated

def xml_esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def create_gamelist():
    try:
        uid_dir = browse("Gamelist: Select UID Dir", EKA_ROMS)
    except GoBack: return

    uid_files = sorted(glob.glob(os.path.join(uid_dir, "*.uid")) + glob.glob(os.path.join(uid_dir, "*.UID")))
    if not uid_files:
        ok("Error", f"No .uid files in:\n{uid_dir}")
        return

    out_file = os.path.join(EKA_ROMS, "gamelist.xml")
    backup = None

    existing = {}
    if os.path.exists(out_file):
        if not confirm("Overwrite?", f"gamelist.xml exists.\n\nOverwrite? Backup will be created."): return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{out_file}.{ts}.bak"
        try:
            shutil.copy2(out_file, backup)
            log(f"Backup: {backup}")
        except Exception as ex: log(f"Backup err: {ex}")
        existing = _parse_gamelist(out_file)
        log(f"Loaded {len(existing)} existing entries")

    img_cache = _media_cache(MEDIA_IMG)
    vid_cache = _media_cache(MEDIA_VID)
    log(f"Media: {len(img_cache)} imgs, {len(vid_cache)} vids")

    lines = ['<?xml version="1.0"?>', '<gameList>']
    processed = set()

    for uf in uid_files:
        base = os.path.basename(uf)
        name = os.path.splitext(base)[0]

        try:
            rp = os.path.relpath(uf, EKA_ROMS).replace("\\", "/")
        except: rp = base
        if not rp.startswith(("./", "/")): rp = "./" + rp

        dev = ""
        try:
            with open(uf, encoding="utf-8") as f:
                fl = f.read().splitlines()
                if len(fl) >= 2 and fl[1].strip(): dev = fl[1].strip()
        except: pass

        key = rp.lower()
        processed.add(key)

        img = _find_media(name, img_cache, MEDIA_IMG, EKA_ROMS)
        vid = _find_media(name, vid_cache, MEDIA_VID, EKA_ROMS)

        if key in existing:
            lines.extend(_update_entry(existing[key], name, dev, img, vid))
            log(f"Updated: {name}")
            continue

        desc = f"[{dev.upper()}] {name}" if dev else name
        lines.append('\t<game>')
        lines.append(f'\t\t<path>{xml_esc(rp)}</path>')
        lines.append(f'\t\t<name>{xml_esc(name)}</name>')
        lines.append(f'\t\t<desc>{xml_esc(desc)}</desc>')
        lines.append(f'\t\t<image>{xml_esc(img)}</image>')
        lines.append(f'\t\t<video>{xml_esc(vid)}</video>')
        lines.append('\t</game>')

    kept = 0
    for k, v in existing.items():
        if k not in processed:
            lines.extend(v)
            kept += 1

    lines.append('</gameList>')

    try:
        with open(out_file, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as ex:
        log(f"Write err: {ex}")
        ok("Error", f"Failed to write gamelist.xml:\n{ex}")
        return

    bm = f"\nBackup: {backup}" if backup else ""
    ok("Done", f"gamelist.xml created.\n\nUIDs: {len(uid_files)}\nKept existing: {kept}\nImages: {len(img_cache)}\nVideos: {len(vid_cache)}{bm}")

# === INSTALLATION ===
def _install_files(files: List[str], sis_dir: str, info_plat: Tuple[str, str]):
    if not pick_dev(f"install {info_plat[0]} files"):
        return

    dev_name = get_dev_name() or ""
    success = fail = art_ok = art_fail = vid_ok = 0
    failed = []

    for pos, sf in enumerate(files, 1):
        cls()
        rn = rel_path(sf, sis_dir)
        plat_label = info_plat[0] if info_plat[0] != "Mixed" else "Mixed platforms (see per-file hints)"
        print(f"Installing {pos}/{len(files)}:\n  {rn}\n  Platform: {plat_label}", flush=True)

        before = get_apps()
        ret = run_eka(["--install", sf])
        after = get_apps()

        if ok_ret(ret):
            success += 1
            log(f"OK: {sf}")
            new = find_new_app(before, after)
            if new:
                app, uid = new
                write_uid([(app, uid)], EKA_ROMS, dev_name)
                if _copy_media(os.path.dirname(sf), app, MEDIA_IMG, IMG_EXTS): art_ok += 1
                else: art_fail += 1
                if _copy_media(os.path.dirname(sf), app, MEDIA_VID, VID_EXTS): vid_ok += 1
            else:
                art_fail += 1
        else:
            fail += 1
            failed.append(rn)
            log(f"FAIL {ret}: {sf}")

    res = (f"Platform: {info_plat[0]}\n\nInstalled: {success}\nFailed: {fail}\n"
           f"Artwork: {art_ok} OK, {art_fail} missing\nVideos: {vid_ok} copied")
    if failed:
        res += "\n\nFailed:\n" + "\n".join(failed[:8]) + (f"\n... +{len(failed)-8}" if len(failed) > 8 else "")
        res += f"\n\nLog: {EKA_LOG}"
    ok("Result", res)

def scan_sis():
    try:
        sd = browse("Scan SIS: Select Dir", EKA_ROMS)
    except GoBack: return

    cls(); print("Scanning...", flush=True)
    files = find_sis(sd)
    if not files:
        ok("Result", f"No .sis/.sisx in:\n{sd}")
        return

    groups = {}
    for f in files:
        plat = det_plat(f)
        groups.setdefault(plat, []).append(f)

    present = [k for k in _PLAT_ORD if k in groups]
    opts = [f"[{len(groups[k]):3d}]  {_PLAT_INFO[k][0]}  →  {_PLAT_INFO[k][1]}" for k in present]

    while True:
        try:
            idx = select("Scan: Select Platform", opts, f"Found {len(files)} file(s)", 10)
        except GoBack: return
        if idx is None: return

        key = present[idx]
        chosen = groups[key]
        info = _PLAT_INFO[key]

        fopts = [rel_path(f, sd) for f in chosen]
        try:
            sel = multi_select(f"Select: {info[0]}", fopts,
                              f"Platform: {info[0]} → {info[1]}\n\nA: Toggle, X: All, Y: Install", 14)
        except GoBack: continue
        if not sel:
            ok("Scan", "No files selected.")
            continue

        selected = [chosen[i] for i in sel]
        _install_files(selected, sd, info)

def install_sis():
    if not pick_dev("SIS/SISX installation"): return

    try:
        sd = browse("SIS: Select Dir", EKA_ROMS, [".sis", ".sisx"])
    except GoBack: return

    files = find_sis(sd, recursive=False)

    if not files:
        ok("Error", f"No .sis/.sisx in:\n{sd}")
        return

    hints = {}
    for f in files:
        h = plat_hint(f)
        hints[h] = hints.get(h, 0) + 1
    hl = "\n".join(f"  {v}x  {k}" for k, v in sorted(hints.items()))

    try:
        mode = select("SIS Installer", ["Install all (recursive)", "Select individually (recursive)"],
                     f"{len(files)} file(s)\n\nDetected:\n{hl}")
    except GoBack: return
    if mode is None: return

    if mode == 0:
        if not confirm("Install All", f"Install all {len(files)} files?\n\n{sd}"): return
        selected = files
    else:
        sopts = [f"{rel_path(f, sd)}  [{plat_hint(f)}]" for f in files]
        try:
            sel = multi_select("Select SIS/SISX", sopts, f"{sd}\n\nA: Toggle, Y: Install", 14)
        except GoBack: return
        if not sel:
            ok("SIS", "None selected.")
            return
        selected = [files[i] for i in sel]
        if not confirm("Install", f"Install {len(selected)} file(s)?"): return

    _install_files(selected, sd, ("Mixed", "See per-file hints"))

# === UID CREATOR ===
def build_cands(apps: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], int, int, int]:
    cands, seen = [], set()
    skipped_sys = skipped_blank = skipped_dup = 0
    for name, uid in apps:
        name = name.strip()
        uid = uid.strip().lower()
        if not name: skipped_blank += 1; continue
        if uid in seen: skipped_dup += 1; continue
        if is_sys(name): seen.add(uid); skipped_sys += 1; continue
        seen.add(uid); cands.append((name, uid))
    return cands, skipped_sys, skipped_blank, skipped_dup

def write_uid(apps: List[Tuple[str, str]], out_dir: str, dev_name: str = "") -> List[Tuple[str, str, str]]:
    created = []
    os.makedirs(out_dir, exist_ok=True)
    for name, uid in apps:
        sn = sanitize(name)
        target = os.path.join(out_dir, f"{sn}.uid")
        # BUGFIX: Check both possible filenames to avoid overwriting
        if os.path.exists(target):
            target = os.path.join(out_dir, f"{sn}_{uid}.uid")
            if os.path.exists(target):
                log(f"UID exists, skipping: {target}")
                continue
        try:
            with open(target, 'w', encoding='utf-8') as f:
                f.write(uid + '\n')
                if dev_name: f.write(dev_name.lower() + '\n')
            log(f"UID: {target} -> {uid}")
            created.append((name, uid, os.path.basename(target)))
        except Exception as ex: log(f"UID err: {ex}")
    return created

def create_uids():
    if not pick_dev("UID creation"): return

    try:
        od = browse("UID: Output Dir", "/storage/roms")
    except GoBack: return

    cls(); print("Loading apps...", flush=True)
    ret, out = run_cap(["--listapp"])
    apps = parse_apps(out)

    if ret != 0 and not apps:
        ok("Error", f"Could not get app list.\n\nLog: {EKA_LOG}")
        return
    if not apps:
        ok("Error", "No installed apps.")
        return

    cands, ss, sb, sd = build_cands(apps)
    cands = sorted(cands, key=lambda x: (x[0].lower(), x[1]))

    if not cands:
        ok("Error", "No launchable apps found.")
        return

    opts = [f"{n} ({u})" for n, u in cands]
    try:
        select("Available Apps", opts, f"Launchable apps: {len(cands)}\n\nA: Continue, B: Back", 14)
    except GoBack: return

    try:
        mode = select("UID Mode", ["Create all", "Select individually"],
                     f"Output: {od}\nApps: {len(cands)}")
    except GoBack: return
    if mode is None: return

    selected = []
    if mode == 0:
        if not confirm("Create All", f"Create {len(cands)} UID files in:\n\n{od}"): return
        selected = cands
    else:
        opts = [f"{n} ({u})" for n, u in cands]
        try:
            sel = multi_select("Select Apps", opts, f"Output: {od}\n\nA: Toggle, Y: Create", 14)
        except GoBack: return
        if not sel: ok("UID", "None selected."); return
        selected = [cands[i] for i in sel]
        if not confirm("Create", f"Create {len(selected)} UID files in:\n\n{od}"): return

    dev = get_dev_name() or ""
    created = write_uid(selected, od, dev)

    ok("Done", f"UID creation done.\n\nOutput: {od}\nRequested: {len(selected)}\nCreated: {len(created)}\nSkip sys: {ss}\nSkip blank: {sb}\nSkip dup: {sd}")

# === UNINSTALL ===
def uninstall_apps():
    if not pick_dev("app uninstall"): return

    cls(); print("Loading apps...", flush=True)
    ret, out = run_cap(["--listapp"])
    apps = parse_apps(out)

    if ret != 0 and not apps:
        ok("Error", f"Could not get app list.\n\nLog: {EKA_LOG}")
        return
    if not apps:
        ok("Error", "No installed apps.")
        return

    cands, _, _, _ = build_cands(apps)
    if not cands:
        ok("Error", "No removable apps found.")
        return

    opts = [f"{n}  ({u})" for n, u in cands]
    try:
        sel = multi_select("Uninstall Apps", opts, f"Toggle with A, Y to uninstall.\n\nApps: {len(cands)}", 14)
    except GoBack: return
    if not sel: ok("Uninstall", "None selected."); return

    selected = [cands[i] for i in sel]
    if not confirm("Confirm", f"Uninstall {len(selected)} app(s)?\n\n" + "\n".join(f"  {n} ({u})" for n, u in selected[:8]) + ("\n  ..." if len(selected) > 8 else "") + "\n\nAlso removes .uid files."): return

    success = fail = uid_rm = 0
    for name, uid in selected:
        cls(); print(f"Uninstalling: {name} ({uid})", flush=True)
        ret = run_eka(["--remove", uid])
        if ok_ret(ret):
            success += 1
            log(f"Uninstalled: {name} ({uid})")
            sn = sanitize(name)
            # BUGFIX: Search all .uid files recursively, not just in EKA_ROMS
            for root, _, files in os.walk(EKA_ROMS):
                for cand in (f"{sn}.uid", f"{sn}_{uid}.uid"):
                    up = os.path.join(root, cand)
                    if os.path.exists(up):
                        try:
                            os.remove(up)
                            uid_rm += 1
                            log(f"Removed UID: {up}")
                        except Exception as ex: log(f"UID rm err: {ex}")
        else:
            fail += 1
            log(f"Fail uninstall: {name} ({uid}) - {ret}")

    ok("Done", f"Uninstalled: {success}\nFailed: {fail}\nUIDs removed: {uid_rm}" + (f"\n\nLog: {EKA_LOG}" if fail else ""))

def uninstall_dev():
    cls(); print("Loading devices...", flush=True)
    devs = get_valid_devs()
    if not devs:
        ok("Uninstall", "No devices found.")
        return

    cur = get_dev_idx()
    opts = [f"{n} : {name}{'  [CURRENT]' if cur == n else ''}" for n, name in devs]
    try:
        idx = select("Uninstall Device", opts, "Select device to remove.", 16)
    except GoBack: return
    if idx is None: return

    n, name = devs[idx]
    if not confirm("Confirm", f"Remove {n} : {name}?\n\nDeletes:\n  - Z-drive\n  - C-drive (saves)\n  - ROMs\n  - devices.yml entry\n\nCannot be undone!"): return

    cls(); print(f"Removing: {name} ...", flush=True)
    log(f"Uninstall dev: {n} : {name}")

    removed, errors = [], []
    dk = name.lower()

    for base, label in [
        (os.path.join(EKA_CONFIG, "data", "drives", "z"), "Z"),
        (os.path.join(EKA_CONFIG, "data", "drives", "c"), "C"),
        (os.path.join(EKA_CONFIG, "data", "roms"), "ROM"),
    ]:
        if not os.path.isdir(base): continue
        for entry in os.listdir(base):
            if entry.lower() == dk:
                fp = os.path.join(base, entry)
                try:
                    shutil.rmtree(fp) if os.path.isdir(fp) else os.remove(fp)
                    removed.append(f"{label}: {fp}")
                    log(f"Removed {label}: {fp}")
                except Exception as ex:
                    errors.append(f"{label}: {fp}\n{ex}")
                    log(f"ERR rm {label} {fp}: {ex}")

    dy = os.path.join(EKA_CONFIG, "data", "devices.yml")
    if os.path.isfile(dy):
        try:
            with open(dy) as f: lines = f.readlines()
            new_lines, skip, found = [], False, False
            for line in lines:
                s = line.rstrip()
                if s and not s[0].isspace() and s.endswith(":"):
                    if s[:-1].strip().lower() == dk:
                        skip = True; found = True
                        log(f"Rm dev.yml: {s[:-1]}")
                        continue
                    else: skip = False
                if not skip: new_lines.append(line)
            if found:
                with open(dy, "w") as f: f.writelines(new_lines)
                removed.append("devices.yml entry")
            else: log(f"dev.yml: {name} not found")
        except Exception as ex: errors.append(f"devices.yml: {ex}"); log(f"dev.yml err: {ex}")

    _autoset_dev()

    if errors:
        ok("Result", f"Removed with errors.\n\nRemoved: {len(removed)}\nErrors: {len(errors)}\n\n" + "\n".join(errors[:3]) + f"\n\nLog: {EKA_LOG}")
    else:
        ok("Done", f"Device removed.\n\n{n} : {name}\n\nRemoved {len(removed)} item(s).\nDevice index auto-updated.")

def show_apps():
    if not pick_dev("show apps"): return
    cls(); print("Loading apps...", flush=True)
    ret, out = run_cap(["--listapp"])
    apps = parse_apps(out)
    if not apps:
        ok("Apps", "No installed apps.")
        return
    opts = [f"{n}  ({u})" for n, u in sorted(apps, key=lambda x: x[0].lower())]
    try: select("Installed Apps", opts, f"Total: {len(apps)}", 16)
    except GoBack: return

# === SETUP / RESET ===
DEFAULT_CFG = """bkg-path: ""
font: ""
log-read: false
log-write: false
log-ipc: false
log-svc: false
log-passed: false
log-exports: false
cpu: dynarmic
device: 0
language: 1
emulator-language: -1
enable-gdb-stub: false
data-storage: data
gdb-port: 24689
internet-bluetooth-port: 35689
enable-srv-rights: true
enable-srv-sa: true
enable-srv-drm: true
fbs-enable-compression-queue: false
enable-btrace: false
stop-warn-touchscreen-disabled: false
dump-imb-range-code: false
hide-mouse-in-screen-space: false
enable-nearest-neighbor-filter: true
integer-scaling: true
cpu-load-save: true
mime-detection: true
rtos-level: ""
ui-new-style: true
svg-icon-cache-reset: true
imei: 540806859904945
mmc-id: 00000000-00000000-00000000-00000000
audio-master-volume: 100
current-keybind-profile: default
screen-buffer-sync: preferred
report-mmfdev-underflow: false
disable-display-content-scale: false
device-display-name: EKA2L1
midi-backend: tsf
hsb-bank-path: resources/defaultbank.hsb
sf2-bank-path: resources/defaultbank.sf2
bt-central-server-url: btnetplay.12z1.com
background-image: ""
background-image-opacity: 255
enable-hw-gles1: true
log-filter: "*:trace"
hide-system-apps: true
btnet-port-offset: 15000
btnet-password: ""
btnet-discovery-mode: 0
enable-upnp: true
extensive-logging: false
internet-bluetooth-friends:
  []
"""

def _mk_default_cfg():
    cp = os.path.join(EKA_CONFIG, "config.yml")
    if not os.path.exists(cp):
        try:
            with open(cp, "w") as f: f.write(DEFAULT_CFG)
            log("Created default config.yml")
            return True
        except Exception as ex: log(f"cfg err: {ex}")
    return False

def _seed():
    inst = "/usr/bin/eka2l1"
    if not os.path.isdir(inst):
        ok("Error", f"eka2l1 not found:\n{inst}")
        return
    cls(); print("Seeding...", flush=True)
    seeded = []
    for item in os.listdir(inst):
        src, dst = os.path.join(inst, item), os.path.join(EKA_CONFIG, item)
        if not os.path.exists(dst):
            try:
                shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)
                seeded.append(item)
                log(f"Seeded: {item}")
                print(f"  {item}", flush=True)
            except Exception as ex: log(f"Seed err {item}: {ex}")
    if _mk_default_cfg():
        seeded.append("config.yml")
        print("  config.yml", flush=True)
    if seeded:
        ok("Done", f"Seeded {len(seeded)} item(s) to:\n{EKA_CONFIG}")
    else:
        ok("Done", "All files already present.")

def _autoset_dev():
    dy = os.path.join(EKA_CONFIG, "data", "devices.yml")
    zd = os.path.join(EKA_CONFIG, "data", "drives", "z")
    cp = os.path.join(EKA_CONFIG, "config.yml")
    if not os.path.isfile(dy) or not os.path.isdir(zd): return
    keys = []
    try:
        with open(dy) as f:
            for line in f:
                s = line.rstrip()
                if s and not s.startswith(" ") and s.endswith(":"):
                    keys.append(s[:-1])
    except Exception as ex: log(f"autoset read err: {ex}"); return
    avail = {d.lower(): d for d in os.listdir(zd) if os.path.isdir(os.path.join(zd, d))}
    mi = None
    for i, k in enumerate(keys):
        if k.lower() in avail:
            mi = i
            log(f"Autoset: {k} @ {i}")
            break
    if mi is None:
        log("Autoset: no match")
        return
    if not os.path.isfile(cp): _mk_default_cfg()
    try:
        with open(cp) as f: lines = f.readlines()
        nl = []
        for line in lines:
            nl.append(f"device: {mi}\n" if line.startswith("device:") else line)
        with open(cp, "w") as f: f.writelines(nl)
        log(f"Autoset: device {mi}")
    except Exception as ex: log(f"autoset write err: {ex}")

def _import_pre():
    try:
        src = browse("Import: Select Dir (needs 'data' folder)", EKA_BIOS)
    except GoBack: return
    ds = os.path.join(src, "data")
    if not os.path.isdir(ds):
        ok("Error", f"No 'data' folder in:\n{src}")
        return
    dd = os.path.join(EKA_CONFIG, "data")
    os.makedirs(dd, exist_ok=True)
    total = sum(len(fs) for _, _, fs in os.walk(ds))
    cls()
    print(f"Importing from:\n  {src}\nOnly adding new files.\n\nTotal: {total}\n", flush=True)
    log(f"Import: {src} ({total} files)")
    added = skipped = proc = 0
    last = time.time()
    for root, _, files in os.walk(ds):
        rel = os.path.relpath(root, ds)
        dr = os.path.join(dd, rel) if rel != "." else dd
        os.makedirs(dr, exist_ok=True)
        for fn in files:
            sf, df = os.path.join(root, fn), os.path.join(dr, fn)
            proc += 1
            if time.time() - last >= 2.0:
                unblank(); last = time.time()
                pct = int(proc * 100 / total) if total else 100
                bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                print(f"\r[{bar}] {pct:3d}%  {proc}/{total}  (+{added} added, ={skipped} skipped)    ", end='', flush=True)
            if fn == "devices.yml" and os.path.exists(df):
                try:
                    shutil.copy2(df, df + ".bak")
                    shutil.copy2(sf, df)
                    added += 1
                except Exception as ex: log(f"dev.yml err: {ex}"); skipped += 1
                continue
            if not os.path.exists(df):
                try: shutil.copy2(sf, df); added += 1
                except Exception as ex: log(f"copy err: {ex}"); skipped += 1
            else: skipped += 1
    print(f"\r[####################] 100%  {proc}/{total}  (+{added}, ={skipped})    ", flush=True)
    print("", flush=True)
    _autoset_dev()
    ok("Done", f"Import complete.\n\nAdded: {added}\nSkipped: {skipped}\n\ndevices.yml backed up & overwritten.\nDevice auto-set.")

def reset():
    if not confirm("Reset", f"DELETE all eka2l1 data?\n\n{EKA_CONFIG}\n\nIncludes firmware, games, saves, config."): return
    if not confirm("Confirm", "LAST WARNING!\n\nAll data will be PERMANENTLY deleted.\n\nContinue?"): return
    cls(); print(f"Deleting {EKA_CONFIG} ...", flush=True)
    log(f"Reset: delete {EKA_CONFIG}")
    try:
        if os.path.isdir(EKA_CONFIG):
            shutil.rmtree(EKA_CONFIG)
            log("Reset done")
            ok("Done", f"Deleted:\n{EKA_CONFIG}\n\nRun 'Setup' to reinitialize.")
        else:
            ok("Reset", f"Nothing to delete:\n{EKA_CONFIG}")
    except Exception as ex:
        log(f"Reset err: {ex}")
        ok("Error", f"Reset failed:\n{ex}\n\nLog: {EKA_LOG}")

# === MAIN ===
def main():
    preferred = sys.argv[1] if len(sys.argv) > 1 else None
    init_controller(preferred)
    os.makedirs(EKA_CONFIG, exist_ok=True)
    try:
        with open(EKA_LOG, "w") as f: f.write("EmuELEC eka2l1 Commander Log\n")
    except: pass
    cls(); print("Starting eka2l1 Commander...", flush=True)
    time.sleep(0.5)

    items = [
        "Install / set up eka2l1 (on FIRST RUN or AFTER COMPLETE RESET",
        "Import pre-configured devices",
        "Install firmware (.rpkg + .rom)",
        "Scan folders for .sis / .sisx files",
        "Install .sis / .sisx files",
        "Create .uid launcher files",
        "Create gamelist.xml from .uid files",
        "Show device list / change active device",
        "Convert paths and files to lowercase",
        "Show installed apps",
        "Uninstall apps / games",
        "Uninstall device",
        "Complete Reset",
        "Exit",
    ]

    try:
        while True:
            try:
                idx = select("Main Menu", items, "What would you like to do?")
                if idx is None or idx == 13: break
                try:
                    if idx == 0: _seed()
                    elif idx == 1: _import_pre()
                    elif idx == 2: install_fw()
                    elif idx == 3: scan_sis()
                    elif idx == 4: install_sis()
                    elif idx == 5: create_uids()
                    elif idx == 6: create_gamelist()
                    elif idx == 7: change_dev()
                    elif idx == 8: conv_lower()
                    elif idx == 9: show_apps()
                    elif idx == 10: uninstall_apps()
                    elif idx == 11: uninstall_dev()
                    elif idx == 12: reset()
                except GoBack: continue
            except GoBack: continue
    except UserQuit: pass
    except KeyboardInterrupt: pass
    finally:
        cls(); print("Exiting...", flush=True)
        time.sleep(0.5)
        if controller: controller.close()

if __name__ == "__main__":
    main()