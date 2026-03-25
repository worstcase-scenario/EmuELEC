#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2025-present EmuELEC Team (https://github.com/EmuELEC/EmuELEC)

from evdev import InputDevice, list_devices, ecodes as e
import json
import os
import select
import time
import builtins
import functools
import sys

CONFIG_FILE   = "/storage/.config/emuelec/scripts/macro_config.json"
MAX_NAME_LEN  = 16
NAME_ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_")

# Normalized deadzone: fraction of full axis range that counts as "centre".
# 0.30 means the outer 70 % of travel triggers an action.
# Works for any controller regardless of raw value range (0-255, -32768-32767…)
AXIS_DEADZONE_NORM = 0.30

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    except (ValueError, OSError):
        pass

print = functools.partial(builtins.print, flush=True)


# ---------------------------------------------------------------------------
# Axis normalization  (device-independent)
# ---------------------------------------------------------------------------

# Cache: axis_code -> (centre, half_range) per device path
_absinfo_cache: dict[tuple[str, int], tuple[float, float]] = {}


def _get_axis_centre_range(dev, code):
    """
    Return (centre, half_range) for an axis, reading AbsInfo once and caching.

    Works for any raw value range:
      PS3 / USB HID:  min=0,     max=255   → centre=127.5, half=127.5
      Standard Linux: min=-32768, max=32767 → centre=−0.5,  half=32767.5
    """
    key = (dev.path, code)
    if key not in _absinfo_cache:
        try:
            info = dev.absinfo(code)
            centre     = (info.min + info.max) / 2.0
            half_range = (info.max - info.min) / 2.0
            if half_range == 0:
                half_range = 1.0   # avoid division by zero
        except Exception:
            centre, half_range = 0.0, 32767.0  # safe fallback
        _absinfo_cache[key] = (centre, half_range)
    return _absinfo_cache[key]


def _normalize(dev, code, value):
    """
    Normalize a raw axis value to the range -1.0 … +1.0.
    Returns 0.0 for axes whose AbsInfo is unavailable.
    """
    centre, half_range = _get_axis_centre_range(dev, code)
    return (value - centre) / half_range


# ---------------------------------------------------------------------------
# Analog helpers  (shared by all navigation functions)
# ---------------------------------------------------------------------------

def _axis_to_dpad(dev, code, value):
    """
    Translate an EV_ABS event into a virtual D-Pad direction.

    Returns one of: 'up', 'down', 'left', 'right', or None.
    Uses normalized values so it works regardless of raw axis range.
    """
    norm = _normalize(dev, code, value)
    if abs(norm) < AXIS_DEADZONE_NORM:
        return None

    pos = norm > 0

    nav_map = {
        e.ABS_X:     ("left",  "right"),   # left stick horizontal
        e.ABS_Y:     ("up",    "down"),     # left stick vertical  (up = negative norm)
        e.ABS_RX:    ("left",  "right"),    # right stick horizontal
        e.ABS_RY:    ("up",    "down"),     # right stick vertical
        e.ABS_HAT0X: ("left",  "right"),    # d-pad hat horizontal
        e.ABS_HAT0Y: ("up",    "down"),     # d-pad hat vertical
    }

    pair = nav_map.get(code)
    if pair is None:
        return None
    return pair[1] if pos else pair[0]


def _axis_confirm(dev, code, value):
    """Return True when an analog trigger (L2/R2) is pressed past the deadzone."""
    if code not in (e.ABS_Z, e.ABS_RZ):
        return False
    norm = _normalize(dev, code, value)
    # Triggers start at minimum (fully released); pressed = high positive norm
    return norm > AXIS_DEADZONE_NORM


def _axis_active(dev, code, value):
    """Return True when any axis is outside the deadzone (used for edge detection)."""
    return abs(_normalize(dev, code, value)) >= AXIS_DEADZONE_NORM


# ---------------------------------------------------------------------------
# Button / axis mappings
# ---------------------------------------------------------------------------

def map_controller_to_key(code):
    mapping = {
        e.BTN_DPAD_UP:    e.KEY_UP,
        e.BTN_DPAD_DOWN:  e.KEY_DOWN,
        e.BTN_DPAD_LEFT:  e.KEY_LEFT,
        e.BTN_DPAD_RIGHT: e.KEY_RIGHT,
        e.BTN_SOUTH:      e.KEY_Z,
        e.BTN_EAST:       e.KEY_X,
        e.BTN_NORTH:      e.KEY_A,
        e.BTN_WEST:       e.KEY_S,
        e.BTN_TL:         e.KEY_Q,
        e.BTN_TR:         e.KEY_W,
        e.BTN_TL2:        e.KEY_E,
        e.BTN_TR2:        e.KEY_R,
    }
    return mapping.get(code)


def map_axis_to_key(dev, code, value):
    """
    Map an EV_ABS event to a keyboard key using normalized axis values.
    Returns None when the axis is inside the deadzone.
    """
    norm = _normalize(dev, code, value)
    if abs(norm) < AXIS_DEADZONE_NORM:
        return None

    direction = +1 if norm > 0 else -1

    axis_mapping = {
        e.ABS_X:     {+1: e.KEY_RIGHT, -1: e.KEY_LEFT},
        e.ABS_Y:     {+1: e.KEY_DOWN,  -1: e.KEY_UP},
        e.ABS_RX:    {+1: e.KEY_D,     -1: e.KEY_A},
        e.ABS_RY:    {+1: e.KEY_S,     -1: e.KEY_W},
        e.ABS_Z:     {+1: e.KEY_E,     -1: None},
        e.ABS_RZ:    {+1: e.KEY_R,     -1: None},
        e.ABS_HAT0X: {+1: e.KEY_RIGHT, -1: e.KEY_LEFT},
        e.ABS_HAT0Y: {+1: e.KEY_DOWN,  -1: e.KEY_UP},
    }

    axis = axis_mapping.get(code)
    if axis is None:
        return None
    return axis.get(direction)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def ensure_config_dir():
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"macros": []}
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
    if "macros" not in data:
        macro = {
            "name": "DEFAULT MACRO",
            "trigger_code": data.get("trigger_code"),
            "macro_events": _upgrade_legacy_keys(data.get("macro_keys", [])),
        }
        return {"device_path": data.get("device_path"), "macros": [macro]}
    for macro in data["macros"]:
        if "macro_keys" in macro and "macro_events" not in macro:
            macro["macro_events"] = _upgrade_legacy_keys(macro.pop("macro_keys"))
    return data


def _upgrade_legacy_keys(keys):
    return [{"type": "key", "code": k} for k in keys]


def save_config(data):
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nConfiguration saved to {CONFIG_FILE}.")


# ---------------------------------------------------------------------------
# Controller detection  (multi-node aware)
# ---------------------------------------------------------------------------

_GAMEPAD_BUTTONS = [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST]

def _is_gamepad(dev):
    """Return True if device has the standard face buttons."""
    caps = dev.capabilities()
    keys = caps.get(e.EV_KEY, [])
    return any(btn in keys for btn in _GAMEPAD_BUTTONS)

def _find_all_controller_nodes(preferred_path=None):
    """
    Return a list of InputDevice objects that together cover one gamepad.

    Strategy
    --------
    1.  If preferred_path is given, open it and collect all nodes whose
        *name* matches – this catches the split button/axis nodes that many
        ARM SoC kernels expose (e.g. event0 = buttons, event1 = axes).
    2.  Otherwise find the first device with face buttons and collect
        siblings with the same name.
    3.  Always return at least the anchor device even if no siblings exist.
    """
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

    # Collect every node whose name starts with the same prefix as anchor.
    # Trim trailing numbers/whitespace so "Gamepad 0" matches "Gamepad 1".
    anchor_base = anchor.name.rstrip(" 0123456789")
    siblings = [anchor]
    for d in all_devs:
        if d.path == anchor.path:
            continue
        if d.name.startswith(anchor_base):
            caps = d.capabilities()
            # Only include nodes with EV_KEY or EV_ABS – ignore e.g. LED nodes
            if caps.get(e.EV_KEY) or caps.get(e.EV_ABS):
                siblings.append(d)

    return siblings


def wait_for_controller(preferred_path=None):
    """
    Wait until at least one gamepad node is available.

    Returns a *list* of InputDevice objects (usually 1, sometimes 2 when
    buttons and axes live on separate nodes).
    """
    print("\nWaiting for controller...")
    while True:
        nodes = _find_all_controller_nodes(preferred_path)
        if nodes:
            for n in nodes:
                caps = n.capabilities()
                has_key = bool(caps.get(e.EV_KEY))
                has_abs = bool(caps.get(e.EV_ABS))
                print(f"  Node: {n.name} ({n.path})  "
                      f"EV_KEY={'yes' if has_key else 'no'}  "
                      f"EV_ABS={'yes' if has_abs else 'no'}")
            return nodes
        time.sleep(1)


def read_events(devices, timeout=None):
    """
    Yield (InputDevice, event) tuples from any of the given devices.

    Uses select() so it works with multiple nodes simultaneously.
    If *timeout* is given (seconds), yields nothing and returns when
    the timeout expires with no events.
    """
    fd_map = {dev.fd: dev for dev in devices}
    deadline = (time.monotonic() + timeout) if timeout is not None else None

    while True:
        remaining = None
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return

        ready, _, _ = select.select(fd_map.keys(), [], [], remaining)
        if not ready:
            return  # timeout

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
# Welcome / confirmation screen  (analog + digital)
# ---------------------------------------------------------------------------

def confirm_screen(devices):
    """
    Show a welcome message and ask Yes / No.

    Navigation:
      D-Pad Left/Right  OR  Left-stick left/right  → switch between YES / NO
      A / Start         OR  analog trigger          → confirm selection
      B                                             → cancel (same as NO + confirm)

    Returns True if the user selected YES, False otherwise.
    """
    selected = 0   # 0 = YES, 1 = NO
    options  = ["YES", "NO"]
    axis_active: dict[int, bool] = {}

    while True:
        clear_console()
        print("=" * 46)
        print("         M A C R O   S E T U P")
        print("=" * 46)
        print()
        print("Welcome to Macro Setup.")
        print()
        print("Record controller macros with button presses")
        print("and analog stick / trigger movements.")
        print("Trigger a full sequence with a single button.")
        print()
        print("Navigation:")
        print("  D-Pad / Left Stick  : navigate menus")
        print("  A / Trigger         : confirm")
        print("  B                   : cancel / back")
        print("  Y                   : erase character")
        print()
        print("-" * 46)
        print()

        buttons = []
        for i, label in enumerate(options):
            buttons.append(f"[ {label} ]" if i == selected else f"  {label}  ")
        print("  Continue?    " + "   ".join(buttons))
        print()

        action = None
        for dev, event in read_events(devices):

            # ── Digital buttons ─────────────────────────────────────────────
            if event.type == e.EV_KEY and event.value == 1:
                if event.code == e.BTN_DPAD_LEFT:
                    selected = (selected - 1) % len(options); action = "redraw"; break
                if event.code == e.BTN_DPAD_RIGHT:
                    selected = (selected + 1) % len(options); action = "redraw"; break
                if event.code == e.BTN_SOUTH:
                    return selected == 0
                if event.code == e.BTN_EAST:
                    return False

            # ── Analog axes  ────────────────────────────────────────────────
            elif event.type == e.EV_ABS:
                axis_key = (dev.path, event.code)
                was_active = axis_active.get(axis_key, False)
                now_active = _axis_active(dev, event.code, event.value)

                if now_active and not was_active:
                    direction = _axis_to_dpad(dev, event.code, event.value)
                    if direction == "left":
                        selected = (selected - 1) % len(options)
                        axis_active[axis_key] = True; action = "redraw"; break
                    if direction == "right":
                        selected = (selected + 1) % len(options)
                        axis_active[axis_key] = True; action = "redraw"; break
                    if _axis_confirm(dev, event.code, event.value):
                        axis_active[axis_key] = True
                        return selected == 0

                if not now_active:
                    axis_active[axis_key] = False


# ---------------------------------------------------------------------------
# Controller menu  (analog + digital)
# ---------------------------------------------------------------------------

def controller_menu(devices, title, options, allow_cancel=False):
    index = 0 if options else -1
    axis_active: dict[int, bool] = {}

    while True:
        clear_console()
        print(title)
        print("\nD-Pad / Left Stick: navigate   A / Trigger: confirm", end="")
        if allow_cancel:
            print("   B: cancel", end="")
        print("\n")
        for i, option in enumerate(options):
            prefix = "->" if i == index else "  "
            print(f"{prefix} {option}")
        if not options:
            print("\nNo options available.")

        for dev, event in read_events(devices):

            # ── Digital buttons ─────────────────────────────────────────────
            if event.type == e.EV_KEY and event.value == 1:
                if event.code == e.BTN_DPAD_DOWN and options:
                    index = (index + 1) % len(options); break
                if event.code == e.BTN_DPAD_UP and options:
                    index = (index - 1) % len(options); break
                if event.code == e.BTN_SOUTH and options:
                    return index
                if allow_cancel and event.code == e.BTN_EAST:
                    return None

            # ── Analog axes  ────────────────────────────────────────────────
            elif event.type == e.EV_ABS and options:
                axis_key = (dev.path, event.code)
                was_active = axis_active.get(axis_key, False)
                now_active = _axis_active(dev, event.code, event.value)

                if now_active and not was_active:
                    direction = _axis_to_dpad(dev, event.code, event.value)
                    if direction == "down":
                        index = (index + 1) % len(options)
                        axis_active[event.code] = True; break
                    if direction == "up":
                        index = (index - 1) % len(options)
                        axis_active[event.code] = True; break
                    if _axis_confirm(dev, event.code, event.value):
                        axis_active[event.code] = True
                        return index

                if not now_active:
                    axis_active[axis_key] = False


# ---------------------------------------------------------------------------
# Name entry
# ---------------------------------------------------------------------------

def enter_macro_name(devices, default_name):
    name = list(default_name.upper()[:MAX_NAME_LEN])
    if not name:
        name = list("MACRO")
    while len(name) < MAX_NAME_LEN:
        name.append(" ")
    position = 0
    axis_active: dict[int, bool] = {}

    while True:
        clear_console()
        print("Name your macro")
        print("\nLEFT / RIGHT : move cursor")
        print("UP / DOWN    : change character   (also: left stick)")
        print("A / Trigger  : accept   B: cancel   Y: erase")
        print()
        display = []
        for idx, char in enumerate(name):
            display.append(f"[{char}]" if idx == position else f" {char} ")
        print("".join(display))

        for dev, event in read_events(devices):

            # ── Digital buttons ─────────────────────────────────────────────
            if event.type == e.EV_KEY and event.value == 1:
                if event.code == e.BTN_DPAD_RIGHT:
                    position = min(position + 1, MAX_NAME_LEN - 1); break
                if event.code == e.BTN_DPAD_LEFT:
                    position = max(position - 1, 0); break
                if event.code == e.BTN_DPAD_UP:
                    _name_cycle(name, position, +1); break
                if event.code == e.BTN_DPAD_DOWN:
                    _name_cycle(name, position, -1); break
                if event.code == e.BTN_WEST:
                    name[position] = " "; break
                if event.code == e.BTN_SOUTH:
                    return ("".join(name).strip() or default_name.upper())
                if event.code == e.BTN_EAST:
                    return None

            # ── Analog axes  ────────────────────────────────────────────────
            elif event.type == e.EV_ABS:
                axis_key = (dev.path, event.code)
                was_active = axis_active.get(axis_key, False)
                now_active = _axis_active(dev, event.code, event.value)

                if now_active and not was_active:
                    direction = _axis_to_dpad(dev, event.code, event.value)
                    if direction == "right":
                        position = min(position + 1, MAX_NAME_LEN - 1)
                        axis_active[event.code] = True; break
                    if direction == "left":
                        position = max(position - 1, 0)
                        axis_active[event.code] = True; break
                    if direction == "up":
                        _name_cycle(name, position, +1)
                        axis_active[event.code] = True; break
                    if direction == "down":
                        _name_cycle(name, position, -1)
                        axis_active[event.code] = True; break
                    if _axis_confirm(dev, event.code, event.value):
                        axis_active[event.code] = True
                        return ("".join(name).strip() or default_name.upper())

                if not now_active:
                    axis_active[axis_key] = False


def _name_cycle(name, position, step):
    current = name[position]
    try:
        idx = NAME_ALPHABET.index(current)
    except ValueError:
        idx = 0
    name[position] = NAME_ALPHABET[(idx + step) % len(NAME_ALPHABET)]


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

def record_trigger_button(devices):
    print("\nPress the button that will later trigger the macro...")
    for dev, event in read_events(devices):
        if event.type == e.EV_KEY and event.value == 1 and event.code != e.BTN_MODE:
            print(f"Trigger button: Code {event.code}")
            time.sleep(0.5)
            return event.code


def record_macro_sequence(devices, trigger_code):
    print(
        "\nPress buttons / move sticks for your macro."
        "\nWait 3 seconds with no input to finish."
    )
    macro_events    = []
    last_press_time = time.monotonic()
    last_axis_value: dict[int, int] = {}

    while True:
        # Use a short timeout so the 3-second idle check fires promptly
        for dev, event in read_events(devices, timeout=0.2):

            # ── Digital button ───────────────────────────────────────────────
            if event.type == e.EV_KEY and event.value == 1:
                if event.code != trigger_code:
                    key_code = map_controller_to_key(event.code)
                    if key_code is not None:
                        macro_events.append({"type": "key", "code": key_code})
                        last_press_time = time.monotonic()
                        print(f"  button: code {event.code} -> key {key_code}")

            # ── Analog axis ──────────────────────────────────────────────────
            elif event.type == e.EV_ABS:
                norm = _normalize(dev, event.code, event.value)
                in_deadzone = abs(norm) < AXIS_DEADZONE_NORM

                if in_deadzone:
                    last_axis_value.pop((dev.path, event.code), None)
                else:
                    axis_key = (dev.path, event.code)
                    prev_norm = last_axis_value.get(axis_key)
                    # Record on first activation or direction change
                    if prev_norm is None or (prev_norm > 0) != (norm > 0):
                        key_code = map_axis_to_key(dev, event.code, event.value)
                        if key_code is not None:
                            macro_events.append({
                                "type":       "axis",
                                "code":       event.code,
                                "value":      event.value,
                                "mapped_key": key_code,
                            })
                            last_press_time = time.monotonic()
                            axis_name = e.ABS.get(event.code, event.code)
                            direction = "+" if norm > 0 else "-"
                            print(f"  axis:   ABS_{axis_name} {direction}"
                                  f"  raw={event.value}  norm={norm:.2f}"
                                  f" -> key {key_code}")
                    last_axis_value[axis_key] = norm

        if time.monotonic() - last_press_time > 3:
            break

    if not macro_events:
        print("No inputs recorded!")
        return None

    print(f"Macro recorded: {len(macro_events)} event(s)")
    return macro_events


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config  = load_config()
    devices = wait_for_controller(config.get("device_path"))

    # ── Welcome / confirmation screen ────────────────────────────────────────
    if not confirm_screen(devices):
        print("\nSetup cancelled.")
        return

    macros  = config.setdefault("macros", [])
    options = [f"Overwrite: {macro['name']}" for macro in macros]
    options.append("Create new macro")

    selection = controller_menu(devices, "  Choose macro slot", options, allow_cancel=True)
    if selection is None:
        print("\nSetup cancelled.")
        return

    creating_new = selection == len(macros)

    if creating_new:
        default_name = f"MACRO {len(macros) + 1}"
        macro_name   = enter_macro_name(devices, default_name)
        if macro_name is None:
            print("\nSetup cancelled.")
            return
    else:
        macro_name = macros[selection]["name"]
        print(f"\nOverwriting macro '{macro_name}'.")

    trigger_code = record_trigger_button(devices)
    macro_events = record_macro_sequence(devices, trigger_code)

    if macro_events:
        new_macro = {
            "name":         macro_name,
            "trigger_code": trigger_code,
            "macro_events": macro_events,
        }
        if creating_new:
            macros.append(new_macro)
        else:
            macros[selection] = new_macro

        # Save path of the button node (first device with EV_KEY)
        button_node = next(
            (d for d in devices if d.capabilities().get(e.EV_KEY)), devices[0]
        )
        config["device_path"] = button_node.path
        save_config(config)
        clear_console()
        print("=" * 46)
        print("         M A C R O   S E T U P")
        print("=" * 46)
        print()
        print(f"  Macro '{macro_name}' saved successfully.")
        print()
        k = sum(1 for ev in macro_events if ev["type"] == "key")
        a = sum(1 for ev in macro_events if ev["type"] == "axis")
        print(f"  {k} button event(s), {a} axis event(s) recorded.")
        print()
        print("  Activate your macros with Macro Enabler.")
        print()
    else:
        print("\nMacro recording aborted.")


if __name__ == "__main__":
    main()
