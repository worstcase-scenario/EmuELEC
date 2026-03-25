#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)

import sys, os, json, time, select
from evdev import InputDevice, list_devices, ecodes as e
from evdev import UInput

CONFIG_FILE = "/storage/.config/emuelec/scripts/macro_config.json"
PID_FILE    = "/tmp/macrorun.pid"
LOG_FILE    = "/tmp/macrorun.log"

# Normalized deadzone: fraction of full axis range that counts as "centre".
# Matches the value used in macrosetup.py.
AXIS_DEADZONE_NORM = 0.30


# ---------------------------------------------------------------------------
# Axis normalization  (device-independent, same as macrosetup.py)
# ---------------------------------------------------------------------------

_absinfo_cache: dict[tuple[str, int], tuple[float, float]] = {}


def _get_axis_centre_range(dev, code):
    """Return (centre, half_range) for an axis, reading AbsInfo once."""
    key = (dev.path, code)
    if key not in _absinfo_cache:
        try:
            info       = dev.absinfo(code)
            centre     = (info.min + info.max) / 2.0
            half_range = (info.max - info.min) / 2.0
            if half_range == 0:
                half_range = 1.0
        except Exception:
            centre, half_range = 0.0, 32767.0
        _absinfo_cache[key] = (centre, half_range)
    return _absinfo_cache[key]


def _normalize(dev, code, value):
    """Normalize a raw axis value to -1.0 … +1.0."""
    centre, half_range = _get_axis_centre_range(dev, code)
    return (value - centre) / half_range


def _axis_active(dev, code, value):
    """True when the axis is outside the deadzone."""
    return abs(_normalize(dev, code, value)) >= AXIS_DEADZONE_NORM


def _axis_to_dpad(dev, code, value):
    """Translate EV_ABS into 'up'/'down'/'left'/'right' or None."""
    norm = _normalize(dev, code, value)
    if abs(norm) < AXIS_DEADZONE_NORM:
        return None
    pos = norm > 0
    nav_map = {
        e.ABS_X:     ("left",  "right"),
        e.ABS_Y:     ("up",    "down"),
        e.ABS_RX:    ("left",  "right"),
        e.ABS_RY:    ("up",    "down"),
        e.ABS_HAT0X: ("left",  "right"),
        e.ABS_HAT0Y: ("up",    "down"),
    }
    pair = nav_map.get(code)
    if pair is None:
        return None
    return pair[1] if pos else pair[0]


def _axis_confirm(dev, code, value):
    """True when an analog trigger (L2/R2) is pressed past the deadzone."""
    if code not in (e.ABS_Z, e.ABS_RZ):
        return False
    return _normalize(dev, code, value) > AXIS_DEADZONE_NORM


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _upgrade_legacy_keys(keys):
    return [{"type": "key", "code": k} for k in keys]


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("No saved configuration found. Please run Macro Setup first!")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)

    if "macros" not in data:
        data = {
            "device_path": data.get("device_path"),
            "macros": [{
                "name":         "DEFAULT MACRO",
                "trigger_code": data.get("trigger_code"),
                "macro_events": _upgrade_legacy_keys(data.get("macro_keys", [])),
            }],
        }

    for macro in data.get("macros", []):
        if "macro_keys" in macro and "macro_events" not in macro:
            macro["macro_events"] = _upgrade_legacy_keys(macro.pop("macro_keys"))

    macros = [m for m in data.get("macros", []) if m.get("macro_events")]
    if not macros:
        print("No macros stored in configuration. Please create one first with Macro Setup!")
        sys.exit(1)

    data["macros"] = macros
    return data


# ---------------------------------------------------------------------------
# Controller detection  (multi-node aware, same strategy as macrosetup.py)
# ---------------------------------------------------------------------------

_GAMEPAD_BUTTONS = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST]


def _is_gamepad(dev):
    caps = dev.capabilities()
    keys = caps.get(e.EV_KEY, [])
    return any(btn in keys for btn in _GAMEPAD_BUTTONS)


def _find_all_controller_nodes(preferred_path=None):
    all_devs = []
    for path in list_devices():
        try:
            all_devs.append(InputDevice(path))
        except OSError:
            pass

    anchor = None
    if preferred_path:
        for d in all_devs:
            if d.path == preferred_path:
                anchor = d
                break
    if anchor is None:
        for d in all_devs:
            if _is_gamepad(d):
                anchor = d
                break
    if anchor is None:
        return []

    anchor_base = anchor.name.rstrip(" 0123456789")
    siblings = [anchor]
    for d in all_devs:
        if d.path == anchor.path:
            continue
        if d.name.startswith(anchor_base):
            caps = d.capabilities()
            if caps.get(e.EV_KEY) or caps.get(e.EV_ABS):
                siblings.append(d)
    return siblings


def wait_for_controller(preferred_path=None):
    print("\nWaiting for controller...")
    while True:
        nodes = _find_all_controller_nodes(preferred_path)
        if nodes:
            for n in nodes:
                caps    = n.capabilities()
                has_key = bool(caps.get(e.EV_KEY))
                has_abs = bool(caps.get(e.EV_ABS))
                print(f"  {n.path}  {n.name}  "
                      f"EV_KEY={'yes' if has_key else 'no'}  "
                      f"EV_ABS={'yes' if has_abs else 'no'}")
            return nodes
        time.sleep(1)


def read_events(devices, timeout=None):
    """Yield (InputDevice, event) from any of the given devices via select()."""
    fd_map   = {dev.fd: dev for dev in devices}
    deadline = (time.monotonic() + timeout) if timeout is not None else None

    while True:
        remaining = None
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return

        ready, _, _ = select.select(fd_map.keys(), [], [], remaining)
        if not ready:
            return

        for fd in ready:
            dev = fd_map[fd]
            try:
                for event in dev.read():
                    yield dev, event
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

def clear_console():
    print("\033[2J\033[H", end="")


# ---------------------------------------------------------------------------
# Welcome / confirmation screen
# ---------------------------------------------------------------------------

def confirm_screen(devices, macro_count):
    """Ask Yes / No with D-Pad, left stick, and analog trigger support."""
    selected = 0
    options  = ["YES", "NO"]
    axis_active: dict[int, bool] = {}

    while True:
        clear_console()
        print("=" * 46)
        print("       M A C R O   E N A B L E R")
        print("=" * 46)
        print()
        print(f"Found {macro_count} saved macro(s).")
        print()
        print("Select and activate a macro. Once active,")
        print("pressing the trigger button replays the")
        print("recorded button and axis sequence.")
        print()
        print("Hold trigger 3 s inside macro mode to exit.")
        print()
        print("Navigation:")
        print("  D-Pad / Left Stick  : navigate")
        print("  A / L2 / R2         : confirm")
        print("  B                   : cancel")
        print()
        print("-" * 46)
        print()

        buttons = []
        for i, label in enumerate(options):
            buttons.append(f"[ {label} ]" if i == selected else f"  {label}  ")
        print("  Start Macro Enabler?    " + "   ".join(buttons))
        print()

        for dev, event in read_events(devices):

            if event.type == e.EV_KEY and event.value == 1:
                if event.code == e.BTN_DPAD_LEFT:
                    selected = (selected - 1) % len(options); break
                if event.code == e.BTN_DPAD_RIGHT:
                    selected = (selected + 1) % len(options); break
                if event.code == e.BTN_SOUTH:
                    return selected == 0
                if event.code == e.BTN_EAST:
                    return False

            elif event.type == e.EV_ABS:
                was_active = axis_active.get(event.code, False)
                now_active = _axis_active(dev, event.code, event.value)

                if now_active and not was_active:
                    direction = _axis_to_dpad(dev, event.code, event.value)
                    if direction == "left":
                        selected = (selected - 1) % len(options)
                        axis_active[event.code] = True; break
                    if direction == "right":
                        selected = (selected + 1) % len(options)
                        axis_active[event.code] = True; break
                    if _axis_confirm(dev, event.code, event.value):
                        axis_active[event.code] = True
                        return selected == 0

                if not now_active:
                    axis_active[event.code] = False


# ---------------------------------------------------------------------------
# Event sequence formatter
# ---------------------------------------------------------------------------

# Human-readable names for the button codes used in map_controller_to_key()
_BTN_NAMES: dict[int, str] = {
    e.BTN_DPAD_UP:    "D-Up",
    e.BTN_DPAD_DOWN:  "D-Down",
    e.BTN_DPAD_LEFT:  "D-Left",
    e.BTN_DPAD_RIGHT: "D-Right",
    e.BTN_SOUTH:      "A",
    e.BTN_EAST:       "B",
    e.BTN_NORTH:      "X",
    e.BTN_WEST:       "Y",
    e.BTN_TL:         "L1",
    e.BTN_TR:         "R1",
    e.BTN_TL2:        "L2",
    e.BTN_TR2:        "R2",
    e.BTN_THUMBL:     "L3",
    e.BTN_THUMBR:     "R3",
    e.BTN_START:      "Start",
    e.BTN_SELECT:     "Select",
}

# Reverse map: keyboard key code → original button name
_KEY_TO_BTN: dict[int, str] = {
    e.KEY_UP:    "D-Up",
    e.KEY_DOWN:  "D-Down",
    e.KEY_LEFT:  "D-Left",
    e.KEY_RIGHT: "D-Right",
    e.KEY_Z:     "A",
    e.KEY_X:     "B",
    e.KEY_A:     "X",
    e.KEY_S:     "Y",
    e.KEY_Q:     "L1",
    e.KEY_W:     "R1",
    e.KEY_E:     "L2",
    e.KEY_R:     "R2",
    e.KEY_D:     "RS-Right",
    e.KEY_W:     "RS-Down",
}

# Readable axis + direction labels
_AXIS_LABELS: dict[tuple[int, int], str] = {
    (e.ABS_X,     +1): "LS-Right",
    (e.ABS_X,     -1): "LS-Left",
    (e.ABS_Y,     +1): "LS-Down",
    (e.ABS_Y,     -1): "LS-Up",
    (e.ABS_RX,    +1): "RS-Right",
    (e.ABS_RX,    -1): "RS-Left",
    (e.ABS_RY,    +1): "RS-Down",
    (e.ABS_RY,    -1): "RS-Up",
    (e.ABS_Z,     +1): "L2",
    (e.ABS_RZ,    +1): "R2",
    (e.ABS_HAT0X, +1): "D-Right",
    (e.ABS_HAT0X, -1): "D-Left",
    (e.ABS_HAT0Y, +1): "D-Down",
    (e.ABS_HAT0Y, -1): "D-Up",
}

# Button code → readable controller label
_TRIGGER_NAMES: dict[int, str] = {
    e.BTN_SOUTH:      "A",
    e.BTN_EAST:       "B",
    e.BTN_NORTH:      "X",
    e.BTN_WEST:       "Y",
    e.BTN_TL:         "L1",
    e.BTN_TR:         "R1",
    e.BTN_TL2:        "L2",
    e.BTN_TR2:        "R2",
    e.BTN_THUMBL:     "L3",
    e.BTN_THUMBR:     "R3",
    e.BTN_START:      "START",
    e.BTN_SELECT:     "SELECT",
    e.BTN_MODE:       "HOME",
    e.BTN_DPAD_UP:    "D-Up",
    e.BTN_DPAD_DOWN:  "D-Down",
    e.BTN_DPAD_LEFT:  "D-Left",
    e.BTN_DPAD_RIGHT: "D-Right",
}


def _trigger_name(code: int) -> str:
    """Return a human-readable button name for a trigger code."""
    return _TRIGGER_NAMES.get(code, f"BTN-{code}")


def _format_event_sequence(macro_events) -> list[str]:
    """
    Convert a macro's event list into short, readable token strings.

    Examples: ["A", "LS-Right", "B", "L2"]
    """
    tokens = []
    for ev in macro_events:
        if ev["type"] == "key":
            # mapped_key is a keyboard scancode – look up the original button name
            name = _KEY_TO_BTN.get(ev["code"], f"key{ev['code']}")
            tokens.append(name)
        elif ev["type"] == "axis":
            # Use the stored raw value to determine direction sign
            direction = +1 if ev.get("value", 1) > 0 else -1
            label = _AXIS_LABELS.get((ev["code"], direction))
            if label is None:
                label = f"ABS{ev['code']}{'+' if direction > 0 else '-'}"
            tokens.append(label)
    return tokens


def _render_sequence(tokens: list[str], width: int = 42) -> list[str]:
    """
    Wrap tokens into lines that fit within *width* characters.
    Tokens are joined with " → " and lines are indented with "    ".
    """
    sep   = " → "
    lines = []
    line  = "    "
    for i, tok in enumerate(tokens):
        part = tok if i == 0 else sep + tok
        if len(line) + len(part) > width and line.strip():
            lines.append(line)
            line = "    " + tok
        else:
            line += part
    if line.strip():
        lines.append(line)
    return lines if lines else ["    (empty)"]


# ---------------------------------------------------------------------------
# Macro selection menu  (with inline event preview)
# ---------------------------------------------------------------------------

def controller_menu(devices, title, macros):
    """
    Navigate a list of macros.  The currently highlighted macro shows its
    full recorded event sequence below its name line.

    Returns the selected index.
    """
    index = 0
    axis_active: dict[int, bool] = {}

    while True:
        clear_console()
        print(title)
        print("\nD-Pad / Left Stick: navigate   A / L2 / R2: activate   B: cancel\n")

        for i, macro in enumerate(macros):
            events  = macro.get("macro_events", [])
            k       = sum(1 for ev in events if ev["type"] == "key")
            a       = sum(1 for ev in events if ev["type"] == "axis")
            summary = []
            if k: summary.append(f"{k} btn")
            if a: summary.append(f"{a} axis")
            counts  = ", ".join(summary) or "empty"

            if i == index:
                print(f"-> {macro['name']}  [{counts}]"
                      f"  (trigger: {_trigger_name(macro['trigger_code'])})")
                tokens = _format_event_sequence(events)
                for line in _render_sequence(tokens):
                    print(line)
                print()
            else:
                print(f"   {macro['name']}  [{counts}]"
                      f"  (trigger: {_trigger_name(macro['trigger_code'])})")

        for dev, event in read_events(devices):

            if event.type == e.EV_KEY and event.value == 1:
                if event.code == e.BTN_DPAD_DOWN:
                    index = (index + 1) % len(macros); break
                if event.code == e.BTN_DPAD_UP:
                    index = (index - 1) % len(macros); break
                if event.code == e.BTN_SOUTH:
                    return index
                if event.code == e.BTN_EAST:
                    print("\nMacro activation cancelled.")
                    sys.exit(0)

            elif event.type == e.EV_ABS:
                was_active = axis_active.get(event.code, False)
                now_active = _axis_active(dev, event.code, event.value)

                if now_active and not was_active:
                    direction = _axis_to_dpad(dev, event.code, event.value)
                    if direction == "down":
                        index = (index + 1) % len(macros)
                        axis_active[event.code] = True; break
                    if direction == "up":
                        index = (index - 1) % len(macros)
                        axis_active[event.code] = True; break
                    if _axis_confirm(dev, event.code, event.value):
                        axis_active[event.code] = True
                        return index

                if not now_active:
                    axis_active[event.code] = False


# ---------------------------------------------------------------------------
# UInput builder
# ---------------------------------------------------------------------------

def _build_uinput(macro_events):
    key_codes = set()
    for ev in macro_events:
        if ev["type"] == "key":
            key_codes.add(ev["code"])
        elif ev["type"] == "axis":
            mk = ev.get("mapped_key")
            if mk is not None:
                key_codes.add(mk)
    if not key_codes:
        raise ValueError("Macro contains no playable events.")
    return UInput({e.EV_KEY: list(key_codes)}, name="Virtual-Macro", bustype=e.BUS_USB)


def _describe_events(macro_events):
    lines = []
    for ev in macro_events:
        if ev["type"] == "key":
            lines.append(f"  key  code={ev['code']}")
        elif ev["type"] == "axis":
            axis_name = e.ABS.get(ev["code"], ev["code"])
            direction = "+" if ev["value"] > 0 else "-"
            mk = ev.get("mapped_key", "?")
            lines.append(f"  axis ABS_{axis_name} {direction} -> key {mk}")
    return "\n".join(lines) if lines else "  (empty)"


# ---------------------------------------------------------------------------
# Macro playback
# ---------------------------------------------------------------------------

def _play_macro(ui, macro_events, delay=0.05):
    for ev in macro_events:
        if ev["type"] == "key":
            key = ev["code"]
        elif ev["type"] == "axis":
            key = ev.get("mapped_key")
        else:
            continue
        if key is None:
            continue
        ui.write(e.EV_KEY, key, 1); ui.syn()
        time.sleep(delay)
        ui.write(e.EV_KEY, key, 0); ui.syn()


# ---------------------------------------------------------------------------
# Macro mode  (blocking – runs in daemon process)
# ---------------------------------------------------------------------------

def run_macro_mode(dev, macro):
    trigger_code = macro["trigger_code"]
    macro_events = macro["macro_events"]

    k = sum(1 for ev in macro_events if ev["type"] == "key")
    a = sum(1 for ev in macro_events if ev["type"] == "axis")
    print(f"\nMacro '{macro['name']}' active ({k} button(s), {a} axis event(s)).")
    print("Press trigger once to execute. Hold 3 s to exit.")
    print("\nEvent sequence:")
    print(_describe_events(macro_events))

    try:
        ui = _build_uinput(macro_events)
    except ValueError as exc:
        print(f"Cannot build virtual device: {exc}")
        return

    trigger_pressed = False
    macro_executed  = False
    press_start     = 0.0

    for event in dev.read_loop():
        if event.type == e.EV_KEY and event.code == trigger_code:
            if event.value == 1:
                trigger_pressed = True
                macro_executed  = False
                press_start     = time.time()
            elif event.value == 0 and trigger_pressed:
                hold_time       = time.time() - press_start
                trigger_pressed = False
                if hold_time >= 3:
                    print("Hold detected - exiting macro mode.")
                    ui.close()
                    return
                if not macro_executed:
                    print("Executing macro (short press)...")
                    _play_macro(ui, macro_events)

        if trigger_pressed and not macro_executed and time.time() - press_start >= 0.1:
            macro_executed = True
            print("Executing macro (quick trigger)...")
            _play_macro(ui, macro_events)


# ---------------------------------------------------------------------------
# Single-instance guard
# ----------------------
