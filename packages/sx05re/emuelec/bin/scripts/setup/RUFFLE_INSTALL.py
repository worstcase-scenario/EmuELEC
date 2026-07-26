#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# MADE WITH THE HELP OF CLAUDE.AI
#
# EmuELEC edition: the "flash" system entry ships with the image
# (es_systems.json), so this installer only fetches the player itself.

import os, glob, re, shutil, mmap, json, struct, time, sys
from typing import Dict, List, Tuple, Optional
from evdev import InputDevice, list_devices, ecodes as e


import ctypes, ctypes.util

_FONT_PATHS = [
    '/storage/.config/emulationstation/resources/ubuntu_condensed.ttf',
    '/usr/bin/resources/ubuntu_condensed.ttf',
    '/storage/.config/emulationstation/resources/opensans_hebrew_condensed_regular.ttf',
    '/usr/bin/resources/opensans_hebrew_condensed_regular.ttf',
    '/storage/.config/emulationstation/resources/Rubik-Regular.ttf',
    '/usr/bin/resources/Rubik-Regular.ttf',
    '/usr/share/kodi/media/Fonts/DejaVuSans.ttf',
]
_FONT_SIZE_PX = 28   
class _FTGeneric(ctypes.Structure):
    _fields_ = [('data', ctypes.c_void_p), ('finalizer', ctypes.c_void_p)]

class _FTBitmap(ctypes.Structure):
    _fields_ = [('rows', ctypes.c_uint), ('width', ctypes.c_uint),
                ('pitch', ctypes.c_int),
                ('buffer', ctypes.POINTER(ctypes.c_ubyte)),
                ('num_grays', ctypes.c_ushort), ('pixel_mode', ctypes.c_ubyte),
                ('palette_mode', ctypes.c_ubyte), ('palette', ctypes.c_void_p)]

class _FTVector(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

class _FTGlyphMetrics(ctypes.Structure):
    _fields_ = [(n, ctypes.c_long) for n in
                ('width', 'height', 'horiBearingX', 'horiBearingY',
                 'horiAdvance', 'vertBearingX', 'vertBearingY', 'vertAdvance')]

class _FTGlyphSlot(ctypes.Structure):
    _fields_ = [('library', ctypes.c_void_p), ('face', ctypes.c_void_p),
                ('next', ctypes.c_void_p), ('glyph_index', ctypes.c_uint),
                ('generic', _FTGeneric), ('metrics', _FTGlyphMetrics),
                ('linearHoriAdvance', ctypes.c_long),
                ('linearVertAdvance', ctypes.c_long),
                ('advance', _FTVector), ('format', ctypes.c_int),
                ('bitmap', _FTBitmap),
                ('bitmap_left', ctypes.c_int), ('bitmap_top', ctypes.c_int)]
                # (trailing FT fields not needed)

class _FTBBox(ctypes.Structure):
    _fields_ = [(n, ctypes.c_long) for n in ('xMin', 'yMin', 'xMax', 'yMax')]

class _FTSizeMetrics(ctypes.Structure):
    _fields_ = [('x_ppem', ctypes.c_ushort), ('y_ppem', ctypes.c_ushort),
                ('x_scale', ctypes.c_long), ('y_scale', ctypes.c_long),
                ('ascender', ctypes.c_long), ('descender', ctypes.c_long),
                ('height', ctypes.c_long), ('max_advance', ctypes.c_long)]

class _FTSize(ctypes.Structure):
    _fields_ = [('face', ctypes.c_void_p), ('generic', _FTGeneric),
                ('metrics', _FTSizeMetrics), ('internal', ctypes.c_void_p)]

class _FTFace(ctypes.Structure):
    _fields_ = [('num_faces', ctypes.c_long), ('face_index', ctypes.c_long),
                ('face_flags', ctypes.c_long), ('style_flags', ctypes.c_long),
                ('num_glyphs', ctypes.c_long),
                ('family_name', ctypes.c_char_p), ('style_name', ctypes.c_char_p),
                ('num_fixed_sizes', ctypes.c_int), ('available_sizes', ctypes.c_void_p),
                ('num_charmaps', ctypes.c_int), ('charmaps', ctypes.c_void_p),
                ('generic', _FTGeneric), ('bbox', _FTBBox),
                ('units_per_EM', ctypes.c_ushort),
                ('ascender', ctypes.c_short), ('descender', ctypes.c_short),
                ('height', ctypes.c_short),
                ('max_advance_width', ctypes.c_short),
                ('max_advance_height', ctypes.c_short),
                ('underline_position', ctypes.c_short),
                ('underline_thickness', ctypes.c_short),
                ('glyph', ctypes.POINTER(_FTGlyphSlot)),
                ('size', ctypes.POINTER(_FTSize)),
                ('charmap', ctypes.c_void_p)]

def _load_font():
    font_path = next((p for p in _FONT_PATHS if os.path.isfile(p)), None)
    if not font_path:
        raise SystemExit("ERROR: no usable system TTF found "
                         "(EmulationStation resources / Kodi fonts)")
    ft = None
    for name in ('libfreetype.so.6', 'libfreetype.so',
                 ctypes.util.find_library('freetype')):
        if not name:
            continue
        try:
            ft = ctypes.CDLL(name)
            break
        except OSError:
            continue
    if ft is None:
        raise SystemExit("ERROR: libfreetype not found")

    lib = ctypes.c_void_p()
    if ft.FT_Init_FreeType(ctypes.byref(lib)):
        raise SystemExit("ERROR: FT_Init_FreeType failed")
    face = ctypes.POINTER(_FTFace)()
    if ft.FT_New_Face(lib, font_path.encode(), 0, ctypes.byref(face)):
        raise SystemExit(f"ERROR: cannot open font {font_path}")
    ft.FT_Set_Pixel_Sizes(face, 0, _FONT_SIZE_PX)

    m    = face.contents.size.contents.metrics       # 26.6 fixed point
    asc  = (m.ascender + 63) >> 6
    desc = (-m.descender + 63) >> 6
    ch_h = asc + desc

    FT_LOAD_RENDER = 4
    # Pass 1: widest advance over printable ASCII defines the cell width
    adv, ch_w = {}, 1
    for code in range(32, 127):
        if ft.FT_Load_Char(face, code, FT_LOAD_RENDER):
            continue
        a = face.contents.glyph.contents.advance.x >> 6
        adv[code] = a
        if a > ch_w:
            ch_w = a

    # Pass 2: render every glyph centered into a fixed cell (coverage 0-255)
    glyphs = {}
    for code in range(32, 127):
        cell = bytearray(ch_w * ch_h)
        if ft.FT_Load_Char(face, code, FT_LOAD_RENDER) == 0:
            g, bm = face.contents.glyph.contents, face.contents.glyph.contents.bitmap
            if bm.buffer and bm.pitch > 0:
                x0 = (ch_w - adv.get(code, ch_w)) // 2 + g.bitmap_left
                y0 = asc - g.bitmap_top
                for ry in range(bm.rows):
                    ty = y0 + ry
                    if ty < 0 or ty >= ch_h:
                        continue
                    src, dst = ry * bm.pitch, ty * ch_w
                    for rx in range(bm.width):
                        tx = x0 + rx
                        if 0 <= tx < ch_w and bm.buffer[src + rx] > cell[dst + tx]:
                            cell[dst + tx] = bm.buffer[src + rx]
        glyphs[code] = bytes(cell)

    ft.FT_Done_Face(face)
    ft.FT_Done_FreeType(lib)
    return ch_w, ch_h, glyphs

CELL_W, CELL_H, GLYPHS = _load_font()  # cell size derived from font metrics

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
COL_YELLOW  = bytes([0x00, 0xD0, 0xFF, 0xFF])   # yellow (BGRA)

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
MAX_CMD_LEN = 256
CMD_ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -_./\\()[]{}\"'=:,;")


class UserQuit(Exception): pass
class GoBack(Exception):   pass


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
    # Info lines — dynamic height, max half the screen
    info_lines = info.split('\n') if info else []
    max_info = (ROWS - 8) // 2  # never use more than half the screen for info
    info_lines = info_lines[:max_info]
    for i, line in enumerate(info_lines):
        # First line cyan, rest white (for cmd content block)
        col = COL_TITLE if i == 0 else (COL_DIM if not line.strip() else COL_FG)
        fb_text(2, INFO_START + i, line[:COLS-4], col, COL_BG)
    # Dynamic list start: below info block
    list_start = INFO_START + max(len(info_lines), 1) + 1
    list_rows  = SEP2_ROW - list_start
    # List items
    end = min(offset + list_rows, len(items))
    for i in range(offset, end):
        row = list_start + (i - offset)
        text = items[i]
        is_confirm = text.startswith('--- ') and text.endswith(' ---')
        is_sep     = text.startswith('--- ') and not text.endswith(' ---')
        if len(text) > COLS - 4:
            text = text[:COLS - 7] + '...'
        if is_confirm:
            # Green separator line above confirm entry
            if row > list_start:
                sep_color = bytes([0x00, 0x80, 0x00, 0xFF])
                fb_rect(0, (row - 1) * CELL_H + CELL_H - 2, FB_W, 2, sep_color)
            if i == selected:
                fb_fill_row(row, bytes([0x00, 0x90, 0x00, 0xFF]))
                fb_text_centered(row, f"> {text} <", bytes([0xE0, 0xFF, 0xE0, 0xFF]), bytes([0x00, 0x90, 0x00, 0xFF]))
            else:
                fb_fill_row(row, COL_BG)
                fb_text_centered(row, text, bytes([0x00, 0xD0, 0x00, 0xFF]), COL_BG)
        elif is_sep:
            fb_fill_row(row, COL_BG)
            fb_text(2, row, text, COL_DIM, COL_BG, COLS - 2)
        elif i == selected:
            fb_fill_row(row, COL_SEL_BG)
            fb_text(2, row, f"> {text}", COL_SEL_FG, COL_SEL_BG, COLS - 2)
        else:
            fb_text(2, row, f"  {text}", COL_FG, COL_BG, COLS - 2)
    # Scroll indicator
    if end < len(items):
        fb_text(COLS - 5, list_start + list_rows - 1, " ... ", COL_DIM, COL_BG)
    # Bottom bar
    fb_hline(SEP2_ROW)
    hint = "D-Pad:Navigate  A:Select  B:Back  Select:Quit  L/R:Page"
    fb_text_centered(HINT_ROW, hint, COL_DIM, COL_BG)
    fb_hline(SEP3_ROW)
    fb_flip()
    return list_rows

def select_from_list(title: str, items: List[str], info: str = "", initial_selected: int = 0) -> Optional[int]:
    if not items: return None
    total = len(items)
    selected = max(0, min(initial_selected, total - 1))
    offset = 0
    cur_list_rows = LIST_ROWS  # initial estimate, updated after first draw
    while True:
        # Only adjust offset when selected is out of view — never reset it
        if selected < offset:
            offset = selected
        elif selected >= offset + cur_list_rows:
            offset = selected - cur_list_rows + 1
        offset = max(0, offset)
        cur_list_rows = draw_screen(title, items, selected, offset, info, total)
        key = controller.wait_for_input()
        if key == 'select': raise UserQuit()
        elif key == 'up':
            selected = (selected - 1) % total
        elif key == 'down':
            selected = (selected + 1) % total
        elif key == 'left':
            selected = max(0, selected - cur_list_rows)
        elif key == 'right':
            selected = min(total - 1, selected + cur_list_rows)
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


# ---------------------------------------------------------------------------
# Command line editor (fbdev version)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Ruffle installer
# ---------------------------------------------------------------------------
REPO       = "worstcase-scenario/qtruffle"
PORT_URL   = f"https://github.com/{REPO}/releases/latest/download/flash-ruffle-emuelec.tar.gz"
API_URL    = f"https://api.github.com/repos/{REPO}/releases/latest"
PORTDIR    = "/storage/roms/ports/qtwebbrowser"
SCRIPTS    = "/storage/roms/ports_scripts"
CACHE      = "/storage/roms/flash-ruffle-emuelec.tar.gz"
RUFFLE_LOG = "/emuelec/logs/ruffle-install.log"
TITLE      = "Install Flash (Ruffle)"

DOWNLOAD_MB  = 200
EXTRACTED_MB = 450


BROWSER_ENTRY = """\t<game>
\t\t<path>./qtwebbrowser.sh</path>
\t\t<name>Qt Web Browser</name>
\t\t<desc>Full web browser (Qt WebEngine / Chromium) by Snowram. Browse with the gamepad: left stick moves the mouse, A clicks, B is Escape, Start is Enter. An on-screen keyboard opens for text input.</desc>
\t\t<image>/storage/roms/ports/qtwebbrowser/cover.jpg</image>
\t</game>
"""


class InstallError(Exception):
    pass


def installed_version() -> str:
    try:
        return open(os.path.join(PORTDIR, "VERSION"), encoding="utf-8").read().strip()
    except OSError:
        return ""


def latest_version() -> str:
    """Newest release tag from GitHub ("" if offline or unavailable)."""
    import urllib.request
    try:
        req = urllib.request.Request(API_URL, headers={
            "User-Agent": "qtruffle-installer",
            "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("tag_name", "").strip()
    except Exception as exc:
        log(f"Version check failed: {exc}")
        return ""


def log(msg: str) -> None:
    try:
        with open(RUFFLE_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def screen(title: str, headline: str, pct: int = -1, detail: str = "") -> None:
    """Full-screen status display; draws a progress bar when pct >= 0."""
    fb_fill(COL_BG)
    fb_fill_row(TITLE_ROW, COL_SEL_BG)
    fb_text_centered(TITLE_ROW, f"  {title}  ", COL_SEL_FG, COL_SEL_BG)
    fb_text_centered(TITLE_ROW + 3, headline, COL_FG, COL_BG)
    if pct >= 0:
        bar_w, bar_h = int(FB_W * 0.6), CELL_H
        bar_x, bar_y = (FB_W - bar_w) // 2, (TITLE_ROW + 6) * CELL_H
        fb_rect(bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4, COL_BORDER)
        fb_rect(bar_x, bar_y, bar_w, bar_h, COL_BG)
        fb_rect(bar_x, bar_y, int(bar_w * max(0, min(100, pct)) / 100), bar_h, COL_TITLE)
        fb_text_centered(TITLE_ROW + 8, f"{pct}%", COL_YELLOW, COL_BG)
    if detail:
        fb_text_centered(TITLE_ROW + 10, detail, COL_DIM, COL_BG)
    fb_flip()


# --- free space -------------------------------------------------------------
def _existing_dir(path: str) -> str:
    while path and not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return path or "/"


def free_mb(path: str) -> int:
    st = os.statvfs(_existing_dir(path))
    return int(st.f_bavail * st.f_frsize / 1048576)


def same_filesystem(a: str, b: str) -> bool:
    try:
        return os.stat(_existing_dir(a)).st_dev == os.stat(_existing_dir(b)).st_dev
    except OSError:
        return False


def check_free_space() -> bool:
    """Hard error if the port would not fit, warning if /storage is tight."""
    dl, ex = os.path.dirname(CACHE), os.path.dirname(PORTDIR)
    need_dl = 0 if os.path.isfile(CACHE) else DOWNLOAD_MB

    if same_filesystem(dl, ex):
        checks = [(ex, need_dl + EXTRACTED_MB)]
    else:
        checks = [(dl, need_dl), (ex, EXTRACTED_MB)]
    for path, need in checks:
        have = free_mb(path)
        if have < need:
            raise InstallError(f"Not enough free space on {_existing_dir(path)}:\n"
                               f"{have} MB free, about {need} MB needed.")

    sysfree = free_mb("/storage/.emulationstation")
    if sysfree < 100 and not same_filesystem("/storage/.emulationstation", ex):
        return confirm_dialog("Low space on /storage",
                              f"Only {sysfree} MB free on /storage, where\n"
                              f"EmulationStation keeps its settings and gamelists.\n\n"
                              f"The player itself has enough room, but a nearly\n"
                              f"full /storage can cause problems.\n\n"
                              f"Install anyway?")
    return True


# --- install steps ----------------------------------------------------------
def download_port() -> None:
    import urllib.request
    if os.path.isfile(CACHE):
        log("Using existing archive: " + CACHE)
        return
    log("Downloading " + PORT_URL)
    screen(TITLE, "Connecting...")
    req = urllib.request.Request(PORT_URL, headers={"User-Agent": "qtruffle-installer"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except Exception as exc:
        raise InstallError(f"Download failed: {exc}")
    total = int(resp.headers.get("Content-Length", 0))
    done = 0
    last_pct = -1
    tmp = CACHE + ".part"
    try:
        with open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                pct = int(done * 100 / total) if total else 0
                if pct != last_pct:
                    last_pct = pct
                    screen(TITLE, "Downloading player...", pct,
                           f"{done / 1048576:.1f} / {total / 1048576:.1f} MB")
    except Exception as exc:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise InstallError(f"Download failed: {exc}")
    os.rename(tmp, CACHE)


def extract_port() -> None:
    import subprocess
    screen(TITLE, "Checking archive integrity...")
    if subprocess.run(["gzip", "-t", CACHE]).returncode != 0:
        try:
            os.remove(CACHE)
        except OSError:
            pass
        raise InstallError("Archive corrupted - removed, please retry")
    screen(TITLE, "Extracting files...", -1, "This takes a minute, please wait.")
    os.makedirs("/storage/roms/ports", exist_ok=True)
    os.makedirs(SCRIPTS, exist_ok=True)
    r = subprocess.run(["tar", "-xzf", CACHE, "-C", "/storage"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        log(r.stderr)
        raise InstallError("Extraction failed (see log)")
    try:
        os.remove(CACHE)
    except OSError:
        pass


def install_ruffle() -> None:
    have = installed_version() if os.path.isfile(
        os.path.join(PORTDIR, "qtwebbrowser.aarch64")) else ""

    if have:
        screen(TITLE, "Checking for updates...")
        newest = latest_version()
        if not newest:
            if not confirm_dialog("Version check failed",
                                  f"Could not reach GitHub to check for updates.\n\n"
                                  f"Installed version: {have}\n\n"
                                  f"Download and reinstall anyway?"):
                return
        elif newest == have:
            if not confirm_dialog("Already up to date",
                                  f"Installed version {have} is the newest release.\n\n"
                                  f"Reinstall anyway?"):
                return
        elif not confirm_dialog("Update available",
                                f"Installed: {have}\n"
                                f"Available: {newest}\n\n"
                                f"Download and install the new version?"):
            return
        # a forced reinstall must actually re-download
        try:
            os.remove(CACHE)
        except OSError:
            pass

    if not check_free_space():
        return
    download_port()
    extract_port()
    with open(os.path.join(PORTDIR, "VERSION"), "w", encoding="utf-8") as f:
        f.write((latest_version() or "unknown") + "\n")
    if not os.path.isfile(os.path.join(PORTDIR, "qtwebbrowser.aarch64")):
        raise InstallError("qtwebbrowser.aarch64 missing after extraction")
    if not os.path.isfile(os.path.join(PORTDIR, "ruffle", "ruffle.js")):
        raise InstallError("ruffle.js missing after extraction")
    for name in ("Flash-Ruffle.sh", "qtwebbrowser.sh"):
        p = os.path.join(SCRIPTS, name)
        os.path.isfile(p) and os.chmod(p, 0o755)
    os.makedirs("/storage/roms/flash", exist_ok=True)
    ok_dialog("Installation complete",
              "Flash (Ruffle) is installed.\n\n"
              "Put your .swf games into /storage/roms/flash\n"
              "and restart EmulationStation - the Flash system\n"
              "shows up once games are present.\n\n"
              "Per-game controls: place a <game>.gptk file\n"
              "next to the .swf. Exit games with Select+Start.")


def _drop_blocks(content: str, tag: str, needle: str) -> str:
    """Remove every <tag>...</tag> block that contains needle."""
    return re.sub(r"[ \t]*<%s>.*?</%s>\n" % (tag, tag),
                  lambda m: "" if needle in m.group(0) else m.group(0),
                  content, flags=re.DOTALL)


def uninstall_ruffle() -> None:
    if not confirm_dialog("Uninstall Flash (Ruffle)?",
                          "This removes the player, its launcher scripts\n"
                          "and the EmulationStation entries.\n\n"
                          "Your .swf games in /storage/roms/flash are\n"
                          "NOT touched.\n\n"
                          "Continue?"):
        return

    screen(TITLE, "Removing player...")
    shutil.rmtree(PORTDIR, ignore_errors=True)
    for name in ("Flash-Ruffle.sh", "qtwebbrowser.sh"):
        try:
            os.remove(os.path.join(SCRIPTS, name))
        except OSError:
            pass
    try:
        os.remove(CACHE)
    except OSError:
        pass

    gl = os.path.join(SCRIPTS, "gamelist.xml")
    if os.path.isfile(gl):
        content = open(gl, encoding="utf-8").read()
        if "qtwebbrowser.sh" in content:
            screen(TITLE, "Removing Ports list entry...")
            shutil.copy2(gl, gl + ".bak." + time.strftime("%Y%m%d%H%M%S"))
            with open(gl, "w", encoding="utf-8") as f:
                f.write(_drop_blocks(content, "game", "qtwebbrowser.sh"))

    ok_dialog("Uninstalled",
              "Flash (Ruffle) has been removed.\n\n"
              "Your games in /storage/roms/flash are still there.\n"
              "Restart EmulationStation to apply the changes.")


def add_browser_entry() -> None:
    gl = os.path.join(SCRIPTS, "gamelist.xml")
    if os.path.isfile(gl) and "qtwebbrowser.sh" in open(gl, encoding="utf-8").read():
        ok_dialog("Qt Web Browser", "The browser is already in the Ports list.")
        return
    if not confirm_dialog("Add Qt Web Browser?",
                          "The Flash player is built on a full Qt Web Browser.\n\n"
                          "Add the browser itself to the Ports list for\n"
                          "regular web browsing?"):
        return
    if os.path.isfile(gl):
        content = open(gl, encoding="utf-8").read()
        shutil.copy2(gl, gl + ".bak." + time.strftime("%Y%m%d%H%M%S"))
    else:
        content = '<?xml version="1.0"?>\n<gameList>\n</gameList>\n'
    if "</gameList>" not in content:
        raise InstallError("no </gameList> in " + gl)
    content = content.replace("</gameList>", BROWSER_ENTRY + "</gameList>")
    with open(gl + ".tmp", "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(gl + ".tmp", gl)
    ok_dialog("Qt Web Browser added",
              "The Qt Web Browser will show up in the Ports\n"
              "list after restarting EmulationStation.")


def main():
    try:
        with open(RUFFLE_LOG, "w", encoding="utf-8") as f:
            f.write("EmuELEC Flash (Ruffle) Installer Log\n")
    except Exception:
        pass

    installed = os.path.isfile(os.path.join(PORTDIR, "qtwebbrowser.aarch64"))

    fb_open()
    try:
        init_controller()
        while True:
            try:
                idx = select_from_list(
                    "F L A S H   ( R U F F L E )",
                    ["Install / update Flash (Ruffle)",
                     "Add Qt Web Browser to the Ports list",
                     "Uninstall Flash (Ruffle)",
                     "Quit"],
                    f"Player installed ({installed_version() or chr(63)})"
                    if installed else "Player not installed yet"
                )
                if idx is None or idx == 3:
                    fb_fill(COL_BG); break
                elif idx == 0:
                    install_ruffle()
                elif idx == 1:
                    add_browser_entry()
                elif idx == 2:
                    uninstall_ruffle()
                installed = os.path.isfile(os.path.join(PORTDIR, "qtwebbrowser.aarch64"))
            except GoBack:
                continue
            except UserQuit:
                fb_fill(COL_BG); break
            except InstallError as exc:
                log(f"ERROR: {exc}")
                ok_dialog("Installation FAILED", f"{exc}\n\nSee {RUFFLE_LOG}")
    finally:
        fb_close()


if __name__ == '__main__':
    main()
