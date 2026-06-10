#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# THIS SCRIPT HAS BEEN MADE WITH THE HELP OF CLAUDE.AI

import os, glob, re, shutil, mmap, zlib, base64, json, struct, time, sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional
from evdev import InputDevice, list_devices, ecodes as e

# ---------------------------------------------------------------------------
# Embedded font (DejaVuSansMono 28pt, CELL 19x24, base64+zlib+json)
# ---------------------------------------------------------------------------
_FONT_B64 = "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"

def _load_font():
    raw = zlib.decompress(base64.b64decode(_FONT_B64))
    data = json.loads(raw)
    cw, ch = data['cell_w'], data['cell_h']
    glyphs = {int(k): bytes(v) for k, v in data['glyphs'].items()}
    return cw, ch, glyphs

CELL_W, CELL_H, GLYPHS = _load_font()  # 19x37 for size=28

# Glyph render cache: (char_code, fg_bytes, bg_bytes) -> rendered bytes (CELL_H*CELL_W*4)
_GLYPH_CACHE: dict = {}
_GLYPH_ROW   = CELL_W * 4

def _prerender(ch: int, fg: bytes, bg: bytes) -> bytes:
    key = (ch, fg, bg)
    cached = _GLYPH_CACHE.get(key)
    if cached: return cached
    glyph = GLYPHS.get(ch, GLYPHS[32])
    buf = bytearray(CELL_H * _GLYPH_ROW)
    for row_i in range(CELL_H):
        base = row_i * _GLYPH_ROW
        row_base = row_i * CELL_W
        for col_i in range(CELL_W):
            p = base + col_i * 4
            buf[p:p+4] = fg if glyph[row_base + col_i] > 128 else bg
    result = bytes(buf)
    _GLYPH_CACHE[key] = result
    return result

# ---------------------------------------------------------------------------
# Framebuffer renderer
# ---------------------------------------------------------------------------
FB_DEV    = '/dev/fb0'
FB_W      = 1920
FB_H      = 1080
FB_BPP    = 4          # BGRA32
FB_STRIDE = FB_W * FB_BPP

# Colour palette (BGRA bytes)
COL_BG      = bytes([0x18, 0x18, 0x18, 0xFF])   # dark grey
COL_FG      = bytes([0xFF, 0xFF, 0xFF, 0xFF])   # white
COL_SEL_BG  = bytes([0xFF, 0xFF, 0xFF, 0xFF])   # white background for selection
COL_SEL_FG  = bytes([0x18, 0x18, 0x18, 0xFF])   # dark text on white
COL_TITLE   = bytes([0x00, 0xD0, 0xD0, 0xFF])   # cyan
COL_DIM     = bytes([0x80, 0x80, 0x80, 0xFF])   # grey
COL_BORDER  = bytes([0x40, 0x40, 0x40, 0xFF])   # dark border

COLS = FB_W // CELL_W   # ~101
ROWS = FB_H // CELL_H   # ~45

_fb_file = None
_fb_map  = None
_bb      = None   # back-buffer (bytearray)
_bb_mv   = None   # memoryview into _bb for fast row writes

def fb_open():
    global _fb_file, _fb_map, _bb, _bb_mv
    _fb_file = open(FB_DEV, 'rb+')
    _fb_map  = mmap.mmap(_fb_file.fileno(), FB_W * FB_H * FB_BPP)
    _bb      = bytearray(FB_W * FB_H * FB_BPP)
    _bb_mv   = memoryview(_bb)

def fb_close():
    if _fb_map:  _fb_map.close()
    if _fb_file: _fb_file.close()

def fb_flip():
    """Blit back-buffer to framebuffer in one write — eliminates flicker."""
    _fb_map[0:FB_W * FB_H * FB_BPP] = _bb

def fb_fill(color: bytes):
    """Fill back-buffer with one colour."""
    row = color * FB_W
    for y in range(FB_H):
        off = y * FB_STRIDE
        _bb[off:off + FB_STRIDE] = row

def fb_rect(x: int, y: int, w: int, h: int, color: bytes):
    row = color * w
    x_off = x * FB_BPP
    row_bytes = w * FB_BPP
    for row_y in range(y, min(y + h, FB_H)):
        off = row_y * FB_STRIDE + x_off
        _bb[off:off + row_bytes] = row

def fb_char(cx: int, cy: int, ch: int, fg: bytes, bg: bytes):
    """Draw one character cell — uses pre-rendered cache + memoryview slices."""
    rendered = _prerender(ch, fg, bg)
    src = memoryview(rendered)
    base = cy * FB_STRIDE + cx * FB_BPP
    for row_i in range(CELL_H):
        dst = base + row_i * FB_STRIDE
        _bb_mv[dst:dst + _GLYPH_ROW] = src[row_i * _GLYPH_ROW:(row_i + 1) * _GLYPH_ROW]

def fb_text(col: int, row: int, text: str, fg: bytes, bg: bytes, max_cols: int = 0):
    """Draw text at grid position (col, row) into back-buffer."""
    if max_cols > 0:
        text = text[:max_cols]
    x = col * CELL_W
    y = row * CELL_H
    for i, ch in enumerate(text):
        if col + i >= COLS:
            break
        fb_char(x + i * CELL_W, y, ord(ch), fg, bg)

def fb_text_centered(row: int, text: str, fg: bytes, bg: bytes, fill_row: bool = False):
    if fill_row:
        fb_rect(0, row * CELL_H, FB_W, CELL_H, bg)
    col = max(0, (COLS - len(text)) // 2)
    fb_text(col, row, text, fg, bg)

def fb_fill_row(row: int, color: bytes):
    fb_rect(0, row * CELL_H, FB_W, CELL_H, color)

def fb_hline(row: int, char: str = '─'):
    fb_text(0, row, char * COLS, COL_BORDER, COL_BG)

# ---------------------------------------------------------------------------
# Input constants / classes  (unchanged from original)
# ---------------------------------------------------------------------------
ROM_PLACEHOLDER = "<ROM_PATH>"
MAX_CMD_LEN = 256
CMD_ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -_./\\()[]{}\"'=:,;")

DEFAULT_LISTMEDIA_FILE = "/storage/roms/listmedia.txt"
SYSTEM_LISTMEDIA_FILE  = "/usr/bin/scripts/setup/listmedia.txt"

class UserQuit(Exception): pass
class GoBack(Exception):   pass

class MediaEntry:
    def __init__(self, system, media_name, brief, exts):
        self.system = system; self.media_name = media_name
        self.brief = brief;   self.exts = exts

# ---------------------------------------------------------------------------
# Controller input (unchanged)
# ---------------------------------------------------------------------------
def wait_for_controller(preferred_path=None):
    print("Waiting for controller...", flush=True)
    if preferred_path:
        try:
            dev = InputDevice(preferred_path)
            return dev
        except OSError:
            pass
    while True:
        for path in list_devices():
            try: dev = InputDevice(path)
            except OSError: continue
            caps = dev.capabilities()
            keys = caps.get(e.EV_KEY, [])
            abs_caps = caps.get(e.EV_ABS, [])
            has_face = any(b in keys for b in (e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST))
            has_dpad = any(b in keys for b in (e.BTN_DPAD_UP, e.BTN_DPAD_DOWN, e.BTN_DPAD_LEFT, e.BTN_DPAD_RIGHT))
            has_hat  = any(a in abs_caps for a in (e.ABS_HAT0X, e.ABS_HAT0Y))
            if has_face or has_dpad or has_hat:
                return dev
        time.sleep(1.0)

# Keys that auto-repeat when held
_REPEAT_KEYS   = {'left', 'right', 'up', 'down'}
_REPEAT_DELAY  = 0.4   # seconds before repeat starts
_REPEAT_RATE   = 0.08  # seconds between repeats

def _map_event(event, last_hat_x, last_hat_y):
    """Map a single evdev event to an action string, or None."""
    if event.type == e.EV_KEY and event.value == 1:
        code = event.code
        if code == e.BTN_DPAD_UP:    return 'up',   last_hat_x, last_hat_y
        if code == e.BTN_DPAD_DOWN:  return 'down', last_hat_x, last_hat_y
        if code == e.BTN_DPAD_LEFT:  return 'left', last_hat_x, last_hat_y
        if code == e.BTN_DPAD_RIGHT: return 'right',last_hat_x, last_hat_y
        if code in (e.BTN_SOUTH, e.BTN_START): return 'a', last_hat_x, last_hat_y
        if code == e.BTN_EAST:   return 'b',      last_hat_x, last_hat_y
        if code == e.BTN_NORTH:  return 'y',      last_hat_x, last_hat_y
        if code == e.BTN_WEST:   return 'x',      last_hat_x, last_hat_y
        if code == e.BTN_TL:     return 'l1',     last_hat_x, last_hat_y
        if code == e.BTN_TR:     return 'r1',     last_hat_x, last_hat_y
        if code in (e.BTN_SELECT, e.BTN_MODE): return 'select', last_hat_x, last_hat_y
        if code == e.KEY_UP:    return 'up',    last_hat_x, last_hat_y
        if code == e.KEY_DOWN:  return 'down',  last_hat_x, last_hat_y
        if code == e.KEY_LEFT:  return 'left',  last_hat_x, last_hat_y
        if code == e.KEY_RIGHT: return 'right', last_hat_x, last_hat_y
        if code == e.KEY_ENTER: return 'a',     last_hat_x, last_hat_y
        if code in (e.KEY_ESC, e.KEY_BACKSPACE): return 'b', last_hat_x, last_hat_y
    if event.type == e.EV_ABS:
        if event.code == e.ABS_HAT0Y:
            if event.value < 0 and last_hat_y >= 0:
                return 'up',   last_hat_x, event.value
            if event.value > 0 and last_hat_y <= 0:
                return 'down', last_hat_x, event.value
            return None, last_hat_x, 0
        if event.code == e.ABS_HAT0X:
            if event.value < 0 and last_hat_x >= 0:
                return 'left',  event.value, last_hat_y
            if event.value > 0 and last_hat_x <= 0:
                return 'right', event.value, last_hat_y
            return None, 0, last_hat_y
    return None, last_hat_x, last_hat_y

class ControllerInput:
    def __init__(self, preferred_path=None):
        self.dev         = wait_for_controller(preferred_path)
        self.last_hat_x  = 0
        self.last_hat_y  = 0
        self._held       = None   # currently held repeatable key
        self._held_since = 0.0
        self._next_rep   = 0.0

    def wait_for_input(self) -> str:
        import select as _select
        fd = self.dev.fd
        while True:
            now = time.monotonic()
            # If a repeatable key is held, compute how long to wait
            if self._held:
                wait = max(0.0, self._next_rep - now)
            else:
                wait = 5.0  # no key held — block until event

            ready = _select.select([fd], [], [], wait)[0]

            if ready:
                # Drain all pending events
                action = None
                for event in self.dev.read():
                    # Track key releases to cancel repeat
                    if event.type == e.EV_KEY and event.value == 0:
                        code = event.code
                        released = None
                        if code in (e.BTN_DPAD_LEFT, e.KEY_LEFT):   released = 'left'
                        elif code in (e.BTN_DPAD_RIGHT, e.KEY_RIGHT): released = 'right'
                        elif code in (e.BTN_DPAD_UP, e.KEY_UP):       released = 'up'
                        elif code in (e.BTN_DPAD_DOWN, e.KEY_DOWN):   released = 'down'
                        if released and released == self._held:
                            self._held = None
                    # Hat axis release
                    if event.type == e.EV_ABS:
                        if event.code == e.ABS_HAT0Y and event.value == 0:
                            self.last_hat_y = 0
                            if self._held in ('up', 'down'): self._held = None
                        if event.code == e.ABS_HAT0X and event.value == 0:
                            self.last_hat_x = 0
                            if self._held in ('left', 'right'): self._held = None
                    mapped, self.last_hat_x, self.last_hat_y = _map_event(
                        event, self.last_hat_x, self.last_hat_y)
                    if mapped:
                        action = mapped
                        if mapped in _REPEAT_KEYS:
                            self._held      = mapped
                            self._held_since = time.monotonic()
                            self._next_rep   = self._held_since + _REPEAT_DELAY
                        else:
                            self._held = None
                if action:
                    return action
            else:
                # Timeout — fire repeat if key still held
                if self._held:
                    now = time.monotonic()
                    if now >= self._next_rep:
                        self._next_rep = now + _REPEAT_RATE
                        return self._held

    def close(self):
        try: self.dev.close()
        except: pass

controller = None
def init_controller(preferred_path=None):
    global controller
    controller = ControllerInput(preferred_path)

# ---------------------------------------------------------------------------
# UI rendering
# ---------------------------------------------------------------------------
TITLE_ROW    = 0
SUBTITLE_ROW = 1
SEP1_ROW     = 2
INFO_START   = 3
LIST_START   = 5
LIST_ROWS    = ROWS - LIST_START - 3   # visible list items
SEP2_ROW     = ROWS - 3
HINT_ROW     = ROWS - 2
SEP3_ROW     = ROWS - 1

def draw_screen(title: str, items: List[str], selected: int, offset: int,
                info: str = "", total: int = 0):
    fb_fill(COL_BG)
    # Title bar
    fb_fill_row(TITLE_ROW, COL_SEL_BG)
    fb_text_centered(TITLE_ROW, f"  {title}  ", COL_SEL_FG, COL_SEL_BG)
    # Subtitle / counter
    if total > 0:
        sub = f"{selected+1}/{total}"
        fb_text(COLS - len(sub) - 2, SUBTITLE_ROW, sub, COL_DIM, COL_BG)
    # Separator
    fb_hline(SEP1_ROW)
    # Info lines (up to 2 lines)
    if info:
        lines = info.split('\n')
        for i, line in enumerate(lines[:2]):
            fb_text(2, INFO_START + i, line[:COLS-4], COL_TITLE, COL_BG)
    # List items
    end = min(offset + LIST_ROWS, len(items))
    for i in range(offset, end):
        row = LIST_START + (i - offset)
        text = items[i]
        if len(text) > COLS - 4:
            text = text[:COLS - 7] + '...'
        if i == selected:
            fb_fill_row(row, COL_SEL_BG)
            fb_text(2, row, f"> {text}", COL_SEL_FG, COL_SEL_BG, COLS - 2)
        else:
            fb_text(2, row, f"  {text}", COL_FG, COL_BG, COLS - 2)
    # Scroll indicator
    if end < len(items):
        fb_text(COLS - 5, LIST_START + LIST_ROWS - 1, " ... ", COL_DIM, COL_BG)
    # Bottom bar
    fb_hline(SEP2_ROW)
    hint = "D-Pad:Navigate  A:Select  B:Back  Select:Quit  L/R:Page"
    fb_text_centered(HINT_ROW, hint, COL_DIM, COL_BG)
    fb_hline(SEP3_ROW)
    fb_flip()

def select_from_list(title: str, items: List[str], info: str = "") -> Optional[int]:
    if not items: return None
    total = len(items)
    selected = 0
    offset = 0
    while True:
        if selected < offset: offset = selected
        elif selected >= offset + LIST_ROWS: offset = selected - LIST_ROWS + 1
        offset = max(0, min(offset, max(0, total - LIST_ROWS)))
        draw_screen(title, items, selected, offset, info, total)
        key = controller.wait_for_input()
        if key == 'select': raise UserQuit()
        elif key == 'up':
            if selected > 0: selected -= 1
        elif key == 'down':
            if selected < total - 1: selected += 1
        elif key == 'left':
            selected = max(0, selected - LIST_ROWS)
        elif key == 'right':
            selected = min(total - 1, selected + LIST_ROWS)
        elif key == 'a': return selected
        elif key == 'b': raise GoBack()

def _simple_dialog(title: str, message: str, options: List[str], selected_init: int = 0) -> int:
    selected = selected_init
    while True:
        fb_fill(COL_BG)
        fb_fill_row(TITLE_ROW, COL_SEL_BG)
        fb_text_centered(TITLE_ROW, f"  {title}  ", COL_SEL_FG, COL_SEL_BG)
        fb_hline(SEP1_ROW)
        # Message
        lines = message.split('\n')
        for i, line in enumerate(lines[:ROWS - 10]):
            fb_text(2, 3 + i, line[:COLS - 4], COL_FG, COL_BG)
        # Options
        opt_row = 3 + len(lines) + 2
        for i, opt in enumerate(options):
            if i == selected:
                fb_fill_row(opt_row + i, COL_SEL_BG)
                fb_text_centered(opt_row + i, f"> {opt} <", COL_SEL_FG, COL_SEL_BG)
            else:
                fb_text_centered(opt_row + i, f"  {opt}  ", COL_FG, COL_BG)
        fb_hline(SEP2_ROW)
        fb_text_centered(HINT_ROW, "D-Pad:Navigate  A:Confirm  B:Back", COL_DIM, COL_BG)
        fb_flip()
        key = controller.wait_for_input()
        if key == 'select': raise UserQuit()
        elif key in ('up', 'down'): selected = 1 - selected if len(options) == 2 else (selected - 1 if key == 'up' else selected + 1) % len(options)
        elif key == 'a': return selected
        elif key == 'b': return -1

def confirm_dialog(title: str, message: str, default_yes: bool = True) -> bool:
    sel = _simple_dialog(title, message, ["Yes", "No"], 0 if default_yes else 1)
    return sel == 0

def ok_dialog(title: str, message: str):
    _simple_dialog(title, message, ["OK"], 0)

def back_exit_dialog(title: str, message: str) -> str:
    sel = _simple_dialog(title, message, ["BACK", "EXIT"], 0)
    if sel == 1: return "exit"
    return "back"

# ---------------------------------------------------------------------------
# Command line editor (fbdev version)
# ---------------------------------------------------------------------------
def edit_command_line(default_cmd: str) -> Optional[str]:
    cmd = list(default_cmd[:MAX_CMD_LEN])
    while len(cmd) < 20: cmd.append(' ')
    position = 0
    view_offset = 0
    view_width = COLS - 6

    while True:
        fb_fill(COL_BG)
        fb_fill_row(TITLE_ROW, COL_SEL_BG)
        fb_text_centered(TITLE_ROW, "  Edit Command Line  ", COL_SEL_FG, COL_SEL_BG)
        fb_hline(SEP1_ROW)
        fb_text(2, 3, "L/R:Move  Up/Dn:Char  L1/R1:Jump10  X:Insert  Y:Delete  A:OK  B:Cancel", COL_DIM, COL_BG)
        fb_hline(4)
        # Scroll view
        if position < view_offset: view_offset = position
        elif position >= view_offset + view_width: view_offset = position - view_width + 1
        vis_start = view_offset
        vis_end   = min(view_offset + view_width, len(cmd))
        # Draw cmd chars
        draw_row = 6
        fb_fill_row(draw_row, bytes([0x10, 0x10, 0x30, 0xFF]))
        left_ind  = "<" if view_offset > 0 else " "
        right_ind = ">" if vis_end < len(cmd) else " "
        fb_text(0, draw_row, left_ind, COL_DIM, bytes([0x10,0x10,0x30,0xFF]))
        fb_text(COLS-1, draw_row, right_ind, COL_DIM, bytes([0x10,0x10,0x30,0xFF]))
        for idx in range(vis_start, vis_end):
            ch = cmd[idx] if idx < len(cmd) else ' '
            screen_col = 1 + (idx - vis_start)
            if idx == position:
                fb_char(screen_col * CELL_W, draw_row * CELL_H, ord(ch), COL_SEL_FG, COL_SEL_BG)
            else:
                fb_char(screen_col * CELL_W, draw_row * CELL_H, ord(ch), COL_FG, bytes([0x10,0x10,0x30,0xFF]))
        # Status
        pos_info = f"Pos:{position+1}/{len(cmd)}  Len:{len(cmd)}/{MAX_CMD_LEN}"
        fb_text(2, 8, pos_info, COL_DIM, COL_BG)
        # Preview
        preview = ''.join(cmd).rstrip()
        if len(preview) > COLS - 12: preview = preview[:COLS-15] + "..."
        fb_text(2, 10, f"Preview: {preview}", COL_TITLE, COL_BG)
        fb_hline(SEP2_ROW)
        fb_text_centered(HINT_ROW, "A:Accept  B:Cancel  Select:Quit", COL_DIM, COL_BG)
        fb_flip()

        key = controller.wait_for_input()
        if key == 'select': raise UserQuit()
        elif key == 'right':
            if position < len(cmd) - 1: position += 1
        elif key == 'left':
            if position > 0: position -= 1
        elif key == 'r1': position = min(position + 10, len(cmd) - 1)
        elif key == 'l1': position = max(position - 10, 0)
        elif key == 'up':
            cur = cmd[position]
            try: idx = CMD_ALPHABET.index(cur)
            except ValueError: idx = 0
            cmd[position] = CMD_ALPHABET[(idx + 1) % len(CMD_ALPHABET)]
        elif key == 'down':
            cur = cmd[position]
            try: idx = CMD_ALPHABET.index(cur)
            except ValueError: idx = 0
            cmd[position] = CMD_ALPHABET[(idx - 1) % len(CMD_ALPHABET)]
        elif key == 'x':
            if len(cmd) < MAX_CMD_LEN: cmd.insert(position, ' ')
        elif key == 'y':
            if len(cmd) > 1:
                cmd.pop(position)
                if position >= len(cmd): position = len(cmd) - 1
        elif key == 'a':
            final = ''.join(cmd).strip()
            if not final: continue
            if ROM_PLACEHOLDER not in final:
                ok_dialog("Missing Placeholder", f"Command must contain {ROM_PLACEHOLDER}")
                continue
            return final
        elif key == 'b':
            return None

# ---------------------------------------------------------------------------
# Listmedia parser (unchanged)
# ---------------------------------------------------------------------------
def _read_listmedia_text(path):
    with open(path, 'rb') as f: data = f.read()
    if b'\x00' in data[:4096]:
        try: return data.decode('utf-16')
        except: return data.decode('utf-16-le', errors='ignore')
    return data.decode('utf-8', errors='ignore')

def parse_listmedia(path):
    if not os.path.isfile(path): raise FileNotFoundError(path)
    text = _read_listmedia_text(path)
    systems = {}; current_system = None
    for line in text.splitlines():
        original = line.rstrip('\r\n'); stripped = original.strip()
        if not stripped: continue
        tokens = stripped.split()
        if len(tokens) == 2 and tokens[1].startswith('(none'): continue
        if len(tokens) < 3: continue
        brief_idx = next((i for i,t in enumerate(tokens) if t.startswith('(') and t.endswith(')')), None)
        if brief_idx is None or brief_idx == 0: continue
        is_cont = bool(original) and original[0].isspace()
        if is_cont:
            if current_system is None: continue
            system = current_system; media_name = tokens[0]
        else:
            system = tokens[0]; current_system = system
            if brief_idx >= 2: media_name = tokens[1]
            else: continue
        brief = tokens[brief_idx].strip('()')
        exts  = [t for t in tokens[brief_idx+1:] if t.startswith('.')]
        systems.setdefault(system, []).append(MediaEntry(system, media_name, brief, exts))
    return systems

# ---------------------------------------------------------------------------
# System / media / directory selection
# ---------------------------------------------------------------------------
def choose_system(systems):
    all_systems = sorted(systems.keys())
    while True:
        idx = select_from_list("Select System", all_systems, f"Total systems: {len(all_systems)}")
        if idx is None: raise GoBack()
        return all_systems[idx]

def choose_media(entries):
    options = [f"{e.media_name} ({e.brief}) {' '.join(e.exts[:3])}" for e in entries]
    idx = select_from_list("Select Media Type", options)
    if idx is None: raise GoBack()
    return entries[idx]

def choose_directory_interactive(prompt, start_dir='/storage/roms'):
    current = os.path.abspath(start_dir)
    while True:
        try:
            subdirs = sorted(d for d in os.listdir(current) if os.path.isdir(os.path.join(current, d)) and not d.startswith('.'))
        except: subdirs = []
        options = ['[Use This Directory]']
        if current != '/': options.append('[.. Parent Directory]')
        options.extend(subdirs)
        idx = select_from_list(prompt, options, f"Current: {current}")
        if idx is None: raise GoBack()
        sel = options[idx]
        if sel == '[Use This Directory]': return current
        elif sel == '[.. Parent Directory]':
            parent = os.path.dirname(current)
            if parent != current: current = parent
        else: current = os.path.join(current, sel)

def ask_file_filter(default_exts):
    exts = [x.lower() for x in (default_exts or [])]
    if '.zip' not in exts: exts.append('.zip')
    if not exts: return []
    ext_str = ' '.join(exts[:8]) + (f' (+{len(exts)-8})' if len(exts) > 8 else '')
    if confirm_dialog("File Filter", f"Filter by these file types?\n\n{ext_str}", True):
        return exts
    options = ['All files (no filter)'] + exts
    choice = select_from_list("Pick one file type", options)
    if choice is None: raise GoBack()
    return [] if choice == 0 else [exts[choice - 1]]

def find_rom_files(rom_dir, exts):
    files = []

    try:
        for root, dirs, filenames in os.walk(rom_dir):
            # Ignore hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for name in filenames:
                if name.startswith("."):
                    continue

                if exts and os.path.splitext(name)[1].lower() not in exts:
                    continue

                if name.lower().endswith(".cmd"):
                    continue

                # Store the path relative to the selected ROM directory
                relpath = os.path.relpath(os.path.join(root, name), rom_dir)
                files.append(relpath)

    except Exception:
        pass

    return sorted(files)

# ---------------------------------------------------------------------------
# CMD building / writing
# ---------------------------------------------------------------------------
def build_default_template_preset(system, media, extra_options=''):
    parts = [system, '-rp /storage/roms/bios']
    if extra_options.strip(): parts.append(extra_options.strip())
    parts.append(f'-{media.brief} "{ROM_PLACEHOLDER}"')
    return ' '.join(parts)

def apply_template(template, rom_path):
    return template.replace(ROM_PLACEHOLDER, rom_path)

def write_cmd_file(cmd_path, cmd_line):
    os.makedirs(os.path.dirname(cmd_path), exist_ok=True)
    with open(cmd_path, 'w', encoding='utf-8') as f:
        f.write(cmd_line + '\n')

def review_cmd(cmd_path, cmd_line, accept_all):
    if accept_all: return cmd_line, True, True
    disp_path = cmd_path if len(cmd_path) <= 65 else '...' + cmd_path[-62:]
    disp_cmd  = cmd_line if len(cmd_line) <= 68 else cmd_line[:65] + '...'
    info = f"File: {disp_path}\n\nCommand: {disp_cmd}"
    idx = select_from_list("Create .cmd File",
        ["CREATE .CMD FOR THIS ROM", "SKIP THIS ROM",
         "CREATE FOR ALL SELECTED", "BACK"], info)
    if idx is None or idx == 3: raise GoBack()
    if idx == 0: return cmd_line, True, False
    if idx == 2: return cmd_line, True, True
    return None, False, False

# ---------------------------------------------------------------------------
# gamelist.xml update (unchanged)
# ---------------------------------------------------------------------------
def update_gamelist_paths(gamelist_path, rom_dir, rom_files):
    if not os.path.isfile(gamelist_path): return 0
    base_names = {os.path.splitext(n)[0] for n in rom_files}
    try: tree = ET.parse(gamelist_path); root = tree.getroot()
    except: return 0
    changed = 0
    for pe in root.iter('path'):
        text = (pe.text or '').strip()
        if not text: continue
        old_base = os.path.basename(text); base, ext = os.path.splitext(old_base)
        if base not in base_names or ext.lower() == '.cmd': continue
        pe.text = text[:-len(old_base)] + base + '.cmd'; changed += 1
    if changed:
        try: shutil.copy2(gamelist_path, gamelist_path + '.bak'); tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
        except: return 0
    return changed

def maybe_update_gamelist(rom_dir, rom_files):
    if not rom_files: return
    if not confirm_dialog("Update gamelist.xml", "Update gamelist.xml paths to use .cmd files?", False):
        ok_dialog("Gamelist.xml", "Gamelist.xml update was skipped."); return
    gl = os.path.join(rom_dir, 'gamelist.xml')
    if not os.path.isfile(gl):
        ok_dialog("Gamelist.xml", "gamelist.xml not found."); return
    changed = update_gamelist_paths(gl, rom_dir, rom_files)
    if changed > 0: ok_dialog("Success", f"Updated {changed} entries in gamelist.xml")
    else: ok_dialog("Gamelist.xml", "No matching entries were updated.")

# ---------------------------------------------------------------------------
# Preset mode
# ---------------------------------------------------------------------------
def run_preset_mode(systems):
    system = None; media = None; rom_dir = None; exts = []; rom_files = []
    step = 0
    while True:
        if step == 0:
            system = choose_system(systems)
            media = rom_dir = None; exts = []; rom_files = []; step = 1; continue
        if step == 1:
            try: media = choose_media(systems[system]); step = 2
            except GoBack: step = 0; continue
        if step == 2:
            try: rom_dir = choose_directory_interactive("Select ROM Directory"); step = 3
            except GoBack: step = 1; continue
        if step == 3:
            try:
                while True:
                    exts = ask_file_filter(media.exts)
                    rom_files = find_rom_files(rom_dir, exts)
                    if rom_files: break
                    action = back_exit_dialog("No Files Found", f"No ROM files found in:\n{rom_dir}")
                    if action == 'exit': raise UserQuit()
                ok_dialog("Files Found", f"Found {len(rom_files)} ROM file(s)."); step = 4
            except GoBack: step = 2; continue
        # step 4: process
        template = build_default_template_preset(system, media)
        accept_all = False; created = []; i = 0
        while i < len(rom_files):
            name = rom_files[i]
            rom_path = os.path.join(rom_dir, name)
            cmd_line = apply_template(template, rom_path)
            cmd_path = os.path.join(rom_dir, os.path.splitext(name)[0] + '.cmd')
            try:
                sel_cmd, accepted, accept_all = review_cmd(cmd_path, cmd_line, accept_all)
            except GoBack:
                step = 3; break
            if accepted and sel_cmd:
                write_cmd_file(cmd_path, sel_cmd); created.append(name)
            i += 1
        else:
            maybe_update_gamelist(rom_dir, created)
            ok_dialog("Done", f"Created {len(created)} .cmd file(s).")
            step = 0

# ---------------------------------------------------------------------------
# Custom mode
# ---------------------------------------------------------------------------
def run_custom_mode(systems):
    """Custom mode with step-based back navigation, identical to preset mode."""
    system = None; media = None; rom_dir = None; exts = []; rom_files = []
    step = 0  # 0=system, 1=media, 2=dir, 3=filter, 4=edit_cmd, 5=process
    while True:
        if step == 0:
            try:
                system = choose_system(systems)
                media = rom_dir = None; exts = []; rom_files = []
                step = 1
            except GoBack:
                raise  # propagate to main menu

        elif step == 1:
            try:
                media = choose_media(systems[system])
                step = 2
            except GoBack:
                step = 0

        elif step == 2:
            try:
                rom_dir = choose_directory_interactive("Select ROM Directory")
                step = 3
            except GoBack:
                step = 1

        elif step == 3:
            try:
                while True:
                    exts = ask_file_filter(media.exts)
                    rom_files = find_rom_files(rom_dir, exts)
                    if rom_files:
                        break
                    action = back_exit_dialog("No Files Found",
                        f"No ROM files found in:\n{rom_dir}")
                    if action == 'exit':
                        raise UserQuit()
                step = 4
            except GoBack:
                step = 2

        elif step == 4:
            try:
                default_tpl = build_default_template_preset(system, media)
                template = edit_command_line(default_tpl)
                if template is None:
                    step = 3  # B in editor → back to filter
                else:
                    step = 5
            except GoBack:
                step = 3

        elif step == 5:
            accept_all = False; created = []
            go_back = False
            for name in rom_files:
                rom_path = os.path.join(rom_dir, name)
                cmd_line = apply_template(template, rom_path)
                cmd_path = os.path.join(rom_dir, os.path.splitext(name)[0] + '.cmd')
                try:
                    sel_cmd, accepted, accept_all = review_cmd(cmd_path, cmd_line, accept_all)
                except GoBack:
                    go_back = True; break
                if accepted and sel_cmd:
                    write_cmd_file(cmd_path, sel_cmd); created.append(name)
            if go_back:
                step = 4
            else:
                maybe_update_gamelist(rom_dir, created)
                ok_dialog("Done", f"Created {len(created)} .cmd file(s).")
                step = 0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Load listmedia
    listmedia_path = DEFAULT_LISTMEDIA_FILE if os.path.isfile(DEFAULT_LISTMEDIA_FILE) else SYSTEM_LISTMEDIA_FILE
    try: systems = parse_listmedia(listmedia_path)
    except Exception as ex:
        print(f"ERROR loading listmedia: {ex}", file=sys.stderr); sys.exit(1)

    fb_open()
    try:
        init_controller()
        while True:
            try:
                idx = select_from_list(
                    "C M D  M A K E R",
                    ["Preset Mode (recommended)", "Custom Command Mode", "Quit"],
                    f"Loaded {len(systems)} MAME systems from {listmedia_path}"
                )
                if idx is None or idx == 2:
                    fb_fill(COL_BG); break
                elif idx == 0: run_preset_mode(systems)
                elif idx == 1: run_custom_mode(systems)
            except GoBack: continue
            except UserQuit: fb_fill(COL_BG); break
    finally:
        fb_close()

if __name__ == '__main__':
    main()