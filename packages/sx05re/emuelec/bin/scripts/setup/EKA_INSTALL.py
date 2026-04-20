#!/usr/bin/env python3
"""EmuELEC eka2l1 firmware, SIS installer, device selector, UID creator & lowercase converter (controller UI)."""
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)
# THIS FILE HAS BEEN CREATED BY CLAUDE.AI

import os
import glob
import sys
import time
import subprocess
import shutil
import re
from typing import List, Optional, Tuple
from evdev import InputDevice, list_devices, ecodes as e

# Paths
EKA_EXE         = "/usr/bin/eka2l1/eka2l1_sdl2"
EKA_CONFIG      = "/storage/.config/eka2l1"
EKA_BIOS_DIR    = "/storage/roms/bios/eka2l1"
EKA_ROMS_DIR    = "/storage/roms/ngage"
EKA_LOG         = "/emuelec/logs/eka2l1-install.log"
EKA_CONFIG_YML  = os.path.join(EKA_CONFIG, "config.yml")
EKA_Z_DRIVES    = os.path.join(EKA_CONFIG, "data", "drives", "z")

# Exceptions
class UserQuit(Exception):
    pass

class GoBack(Exception):
    pass

# Controller
controller = None

class ControllerInput:
    def __init__(self, preferred_path: Optional[str] = None):
        self.preferred_path = preferred_path
        self.dev = wait_for_controller(preferred_path)
        self.preferred_path = getattr(self.dev, "path", preferred_path)
        self.last_hat_x = 0
        self.last_hat_y = 0

    def reconnect(self):
        old_path = getattr(self.dev, "path", self.preferred_path)
        self.close()
        self.last_hat_x = 0
        self.last_hat_y = 0
        log(f"Controller disconnected, waiting for reconnect (last path: {old_path})")
        print("\nController disconnected. Waiting for reconnect...", flush=True)
        self.dev = wait_for_controller(old_path)
        self.preferred_path = getattr(self.dev, "path", old_path)
        log(f"Controller reconnected: {self.dev.name} ({self.dev.path})")

    def wait_for_input(self) -> str:
        while True:
            try:
                for event in self.dev.read_loop():
                    if event.type == e.EV_KEY and event.value == 1:
                        code = event.code
                        if code == e.BTN_DPAD_UP:    return 'up'
                        if code == e.BTN_DPAD_DOWN:  return 'down'
                        if code == e.BTN_DPAD_LEFT:  return 'left'
                        if code == e.BTN_DPAD_RIGHT: return 'right'
                        if code in (e.BTN_SOUTH, e.BTN_START): return 'a'
                        if code == e.BTN_EAST:       return 'b'
                        if code == e.BTN_NORTH:      return 'y'
                        if code == e.BTN_WEST:       return 'x'
                        if code in (e.BTN_SELECT, e.BTN_MODE): return 'select'
                        if code == e.KEY_UP:         return 'up'
                        if code == e.KEY_DOWN:       return 'down'
                        if code == e.KEY_LEFT:       return 'left'
                        if code == e.KEY_RIGHT:      return 'right'
                        if code == e.KEY_ENTER:      return 'a'
                        if code in (e.KEY_ESC, e.KEY_BACKSPACE): return 'b'

                    if event.type == e.EV_ABS:
                        if event.code == e.ABS_HAT0Y:
                            if event.value < 0 and self.last_hat_y >= 0:
                                self.last_hat_y = event.value
                                return 'up'
                            if event.value > 0 and self.last_hat_y <= 0:
                                self.last_hat_y = event.value
                                return 'down'
                            if event.value == 0:
                                self.last_hat_y = 0
                        if event.code == e.ABS_HAT0X:
                            if event.value < 0 and self.last_hat_x >= 0:
                                self.last_hat_x = event.value
                                return 'left'
                            if event.value > 0 and self.last_hat_x <= 0:
                                self.last_hat_x = event.value
                                return 'right'
                            if event.value == 0:
                                self.last_hat_x = 0
            except OSError as ex:
                if getattr(ex, "errno", None) == 19:
                    self.reconnect()
                    continue
                raise

    def close(self):
        try:
            self.dev.close()
        except Exception:
            pass

def wait_for_controller(preferred_path: Optional[str] = None) -> InputDevice:
    print("\nWaiting for controller...", flush=True)
    if preferred_path:
        try:
            dev = InputDevice(preferred_path)
            print(f"Controller found: {dev.name} ({dev.path})", flush=True)
            return dev
        except OSError:
            pass

    while True:
        for path in list_devices():
            try:
                dev = InputDevice(path)
            except OSError:
                continue

            caps = dev.capabilities()
            keys = caps.get(e.EV_KEY, [])
            abs_caps = caps.get(e.EV_ABS, [])

            has_face = any(btn in keys for btn in (
                e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST
            ))
            has_dpad = any(btn in keys for btn in (
                e.BTN_DPAD_UP, e.BTN_DPAD_DOWN, e.BTN_DPAD_LEFT, e.BTN_DPAD_RIGHT
            ))
            has_hat = any(ax in abs_caps for ax in (e.ABS_HAT0X, e.ABS_HAT0Y))

            if has_face or has_dpad or has_hat:
                print(f"Controller found: {dev.name} ({dev.path})", flush=True)
                return dev

        time.sleep(1.0)

def init_controller(preferred_path: Optional[str] = None):
    global controller
    controller = ControllerInput(preferred_path)

# Screen
def unblank_framebuffer():
    for p in ("/sys/class/graphics/fb0/blank", "/sys/class/graphics/fb1/blank"):
        try:
            with open(p, "w") as f:
                f.write("0")
        except Exception:
            pass

def clear_screen():
    unblank_framebuffer()
    print("\033[2J\033[H", end='', flush=True)

# UI Primitives
def show_menu(title: str, options: List[str], selected: int = 0,
              info: str = "", offset: int = 0, visible: int = 20) -> None:
    clear_screen()
    print("=" * 72)
    print(f"  E K A 2 L 1   C O M M A N D E R  -  {title}")
    print("=" * 72)
    if info:
        print(f"\n{info}\n")
    total = len(options)
    end = min(offset + visible, total)
    for i in range(offset, end):
        marker = "  > " if i == selected else "    "
        print(f"{marker}{options[i]}")
    if end < total:
        print("    ...")
    print("\n" + "-" * 72)
    print("D-Pad: Navigate | A: Select | B: Back | Select: Quit")
    print("-" * 72)
    sys.stdout.flush()

def select_from_list(title: str, items: List[str], info: str = "",
                     visible: int = 20) -> Optional[int]:
    if not items:
        return None

    total = len(items)
    selected = 0
    offset = 0

    while True:
        if selected < offset:
            offset = selected
        elif selected >= offset + visible:
            offset = selected - visible + 1

        offset = max(0, min(offset, max(0, total - visible)))
        show_menu(title, items, selected, info, offset, visible)

        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        elif key == 'up':
            selected = max(0, selected - 1)
        elif key == 'down':
            selected = min(total - 1, selected + 1)
        elif key == 'left':
            selected = max(0, selected - visible)
        elif key == 'right':
            selected = min(total - 1, selected + visible)
        elif key == 'a':
            return selected
        elif key == 'b':
            raise GoBack()

def ok_dialog(title: str, message: str) -> None:
    while True:
        show_menu(title, ["OK"], 0, message)
        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        if key in ('a', 'b'):
            return

def confirm_dialog(title: str, message: str, default_yes: bool = True) -> bool:
    options = ["Yes", "No"]
    selected = 0 if default_yes else 1

    while True:
        show_menu(title, options, selected, message)
        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        elif key in ('up', 'down'):
            selected = 1 - selected
        elif key == 'a':
            return selected == 0
        elif key == 'b':
            return False

# Directory browser
def choose_directory_interactive(prompt: str, start_dir: str,
                                 require_ext: Optional[List[str]] = None) -> str:
    current = os.path.abspath(start_dir)

    while True:
        try:
            entries = os.listdir(current)
            subdirs = sorted(
                d for d in entries
                if os.path.isdir(os.path.join(current, d)) and not d.startswith('.')
            )
        except Exception:
            subdirs = []

        options: List[str] = []
        if require_ext is None:
            options.append("[Use This Directory]")
        else:
            has_match = any(
                f.lower().endswith(tuple(require_ext))
                for f in entries
                if os.path.isfile(os.path.join(current, f))
            )
            if has_match:
                exts = "/".join(e.lstrip(".").upper() for e in require_ext)
                options.append(f"[Use This Directory]  ({exts} files found here)")

        if current != "/":
            options.append("[.. Parent Directory]")
        options.extend(subdirs)

        idx = select_from_list(prompt, options, f"Current: {current}")
        if idx is None:
            raise GoBack()

        selected = options[idx]
        if selected.startswith("[Use This Directory]"):
            return current
        elif selected == "[.. Parent Directory]":
            parent = os.path.dirname(current)
            if parent and parent != current:
                current = parent
        else:
            current = os.path.join(current, selected)

# Log / run helper
def log(msg: str):
    try:
        with open(EKA_LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def run_eka(args: List[str], timeout: int = 120) -> int:
    import threading
    cmd = [EKA_EXE] + args
    log("Running: " + " ".join(cmd))

    spinner_chars = ["|", "/", "-", "\\"]
    stop_event = threading.Event()

    def _keepalive():
        idx = 0
        while not stop_event.wait(2.0):
            unblank_framebuffer()
            print(f"\r  {spinner_chars[idx % 4]} Working...", end='', flush=True)
            idx += 1

    t = threading.Thread(target=_keepalive, daemon=True)
    t.start()

    try:
        with open(EKA_LOG, "a") as logf:
            result = subprocess.run(
                cmd, cwd=EKA_CONFIG, timeout=timeout,
                stdout=logf, stderr=logf
            )
        return result.returncode
    except subprocess.TimeoutExpired:
        log("Process timed out")
        return 0
    except Exception as ex:
        log(f"Exception: {ex}")
        return 1
    finally:
        stop_event.set()
        t.join(timeout=3)
        print("\r" + " " * 20 + "\r", end='', flush=True)

def run_eka_capture(args: List[str], timeout: int = 120) -> Tuple[int, str]:
    cmd = [EKA_EXE] + args
    log("Running (capture): " + " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=EKA_CONFIG,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        output = result.stdout or ""
        if output:
            log(output.rstrip())
        return result.returncode, output
    except subprocess.TimeoutExpired as ex:
        output = (ex.stdout or "") if isinstance(ex.stdout, str) else ""
        if output:
            log(output.rstrip())
        log("Process timed out")
        return 124, output
    except Exception as ex:
        log(f"Exception: {ex}")
        return 1, ""

def eka_success(ret: int) -> bool:
    """eka2l1 often crashes on exit - treat known signal exits as success."""
    return ret in (0, -6, -11, 245)

# Device handling
def get_current_device_index() -> Optional[int]:
    if not os.path.exists(EKA_CONFIG_YML):
        return None

    try:
        with open(EKA_CONFIG_YML, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r'^\s*device\s*:\s*([0-9]+)\s*$', line)
                if match:
                    return int(match.group(1))
    except Exception as ex:
        log(f"Failed to read config.yml: {ex}")

    return None

def get_current_device_name() -> Optional[str]:
    """Return the model-name key of the currently active device, or None."""
    idx = get_current_device_index()
    if idx is None:
        return None
    devices_yml = os.path.join(EKA_CONFIG, "data", "devices.yml")
    if not os.path.isfile(devices_yml):
        return None
    try:
        with open(devices_yml) as f:
            i = 0
            for line in f:
                stripped = line.rstrip()
                if stripped and not stripped.startswith(" ") and stripped.endswith(":"):
                    if i == idx:
                        return stripped[:-1]
                    i += 1
    except Exception:
        pass
    return None

def set_device_index(index: int) -> None:
    os.makedirs(EKA_CONFIG, exist_ok=True)

    lines: List[str] = []
    if os.path.exists(EKA_CONFIG_YML):
        try:
            with open(EKA_CONFIG_YML, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as ex:
            log(f"Failed to read existing config.yml: {ex}")
            lines = []

    replaced = False
    new_lines: List[str] = []

    for line in lines:
        if re.match(r'^\s*device\s*:\s*[0-9]+\s*$', line):
            new_lines.append(f"device: {index}\n")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"device: {index}\n")

    with open(EKA_CONFIG_YML, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    log(f"Set device to {index} in {EKA_CONFIG_YML}")

def get_valid_installed_devices() -> List[Tuple[int, str]]:
    """Return only devices that have a Z-drive installed."""
    z_drives_base = os.path.join(EKA_CONFIG, "data", "drives", "z")

    if not os.path.isdir(z_drives_base):
        log("Z-drives base directory not found")
        return []

    devices: List[Tuple[int, str]] = []
    devices_yml = os.path.join(EKA_CONFIG, "data", "devices.yml")

    try:
        z_dirs = {
            d.lower(): d for d in os.listdir(z_drives_base)
            if os.path.isdir(os.path.join(z_drives_base, d))
        }
    except Exception as ex:
        log(f"Failed to read Z-drives directory: {ex}")
        return []

    if not z_dirs:
        log("No Z-drives found in Z-drives directory")
        return []

    if os.path.isfile(devices_yml):
        try:
            with open(devices_yml, "r") as f:
                device_index = 0
                for line in f:
                    stripped = line.rstrip()
                    if stripped and not stripped.startswith(" ") and stripped.endswith(":"):
                        device_name = stripped[:-1]
                        if device_name.lower() in z_dirs:
                            devices.append((device_index, device_name))
                            log(f"Found valid device {device_index}: {device_name}")
                        else:
                            log(f"Skipped device {device_index}: {device_name} (no Z-drive found)")
                        device_index += 1
        except Exception as ex:
            log(f"Failed to read devices.yml: {ex}")
    else:
        log("devices.yml not found")

    log(f"Total valid installed devices: {len(devices)}")
    return devices

def change_device():
    clear_screen()
    print("Loading device list...", flush=True)

    devices = get_valid_installed_devices()

    if not devices:
        ok_dialog("Error", "No installed devices found.\n\nPlease install firmware first.\n\nSee log: " + EKA_LOG)
        return

    current_device = get_current_device_index()
    options: List[str] = []

    for device_num, device_name in devices:
        label = f"{device_num} : {device_name}"
        if current_device is not None and device_num == current_device:
            label += "  [CURRENT]"
        options.append(label)

    info = "Select device to write into config.yml"

    try:
        idx = select_from_list("Change Device", options, info, visible=16)
    except GoBack:
        return

    if idx is None:
        return

    device_num, device_name = devices[idx]

    if not confirm_dialog(
        "Confirm Device",
        f"Set this device?\n\n{device_num} : {device_name}"
    ):
        return

    try:
        set_device_index(device_num)
        ok_dialog("Done", f"Device changed successfully.\n\ndevice: {device_num}")
    except Exception as ex:
        log(f"Failed to write config.yml: {ex}")
        ok_dialog("Error", f"Could not write config.yml\n\nSee log: {EKA_LOG}")

# Uppercase-to-lowercase converter for device trees
def convert_tree_to_lowercase(root_path):
    renamed = []
    errors = []

    root_path = os.path.abspath(root_path)
    final_root = root_path

    def unique_temp_name(path):
        base = path + ".__tmp_lowercase__"
        candidate = base
        idx = 1
        while os.path.exists(candidate):
            candidate = f"{base}{idx}"
            idx += 1
        return candidate

    def safe_case_rename(src, dst):
        if src == dst:
            return src

        src_abs = os.path.abspath(src)
        dst_abs = os.path.abspath(dst)

        if src_abs.lower() == dst_abs.lower():
            tmp = unique_temp_name(src_abs)
            os.rename(src_abs, tmp)
            os.rename(tmp, dst_abs)
            return dst_abs

        if os.path.exists(dst_abs):
            raise FileExistsError(f"Target already exists: {dst_abs}")

        os.rename(src_abs, dst_abs)
        return dst_abs

    for current_root, dirs, files in os.walk(root_path, topdown=False):
        for name in files:
            src = os.path.join(current_root, name)
            dst = os.path.join(current_root, name.lower())

            if src == dst:
                continue

            try:
                new_path = safe_case_rename(src, dst)
                renamed.append((src, new_path))
                log(f"Renamed file: {src} -> {new_path}")
            except Exception as ex:
                errors.append(f"Failed to rename\n{src}\n->\n{dst}\n{ex}")
                log(f"ERROR renaming file: {src} -> {dst} ({ex})")

        for name in dirs:
            src = os.path.join(current_root, name)
            dst = os.path.join(current_root, name.lower())

            if src == dst:
                continue

            try:
                new_path = safe_case_rename(src, dst)
                renamed.append((src, new_path))
                log(f"Renamed dir: {src} -> {new_path}")
            except Exception as ex:
                errors.append(f"Failed to rename\n{src}\n->\n{dst}\n{ex}")
                log(f"ERROR renaming dir: {src} -> {dst} ({ex})")

    parent = os.path.dirname(root_path)
    base = os.path.basename(root_path)
    lower_base = base.lower()

    if base != lower_base:
        src = root_path
        dst = os.path.join(parent, lower_base)
        try:
            final_root = safe_case_rename(src, dst)
            renamed.append((src, final_root))
            log(f"Renamed root dir: {src} -> {final_root}")
        except Exception as ex:
            errors.append(f"Failed to rename\n{src}\n->\n{dst}\n{ex}")
            log(f"ERROR renaming root dir: {src} -> {dst} ({ex})")

    return renamed, errors, final_root

def convert_device_paths_to_lowercase():
    start_dir = "/storage/.config/eka2l1/data"

    try:
        target_dir = choose_directory_interactive(
            "Lowercase Converter: Select Folder",
            start_dir
        )
    except GoBack:
        return

    warning = ""
    abs_target = os.path.abspath(target_dir)

    if abs_target == "/":
        warning = "\n\nWARNING:\nThis will rename files and folders recursively from the root directory."
    elif abs_target == "/storage":
        warning = "\n\nWARNING:\nThis will rename the complete contents of /storage recursively."

    if not confirm_dialog(
        "Confirm Lowercase Conversion",
        "Convert folder names and file names to lowercase recursively?\n\n"
        f"Selected folder:\n{target_dir}{warning}"
    ):
        return

    clear_screen()
    print("Converting names to lowercase...", flush=True)

    renamed, errors, final_root = convert_tree_to_lowercase(target_dir)

    if errors:
        preview = "\n\n".join(errors[:3])
        more = ""
        if len(errors) > 3:
            more = f"\n\n... and {len(errors) - 3} more error(s)."
        ok_dialog(
            "Conversion Result",
            f"Conversion stopped with errors.\n\n"
            f"Renamed: {len(renamed)}\n"
            f"Errors: {len(errors)}\n\n"
            f"{preview}{more}\n\nSee log: {EKA_LOG}"
        )
        return

    if not renamed:
        ok_dialog(
            "Conversion Result",
            f"Nothing to rename.\n\nAll names are already lowercase in:\n{target_dir}"
        )
        return

    renamed_sorted = sorted(renamed, key=lambda item: item[1].lower())
    options = [f"{os.path.basename(new)}  <=  {os.path.basename(old)}" for old, new in renamed_sorted]
    selected = 0
    offset = 0
    visible = 14

    while True:
        if selected < offset:
            offset = selected
        elif selected >= offset + visible:
            offset = selected - visible + 1

        offset = max(0, min(offset, max(0, len(options) - visible)))
        show_menu(
            "Lowercase Conversion Result",
            options,
            selected,
            f"Converted: {len(renamed)}\nFinal folder: {final_root}\n\nPress A or B to return.",
            offset,
            visible
        )
        key = controller.wait_for_input()
        if key == "select":
            raise UserQuit()
        elif key == "up":
            selected = max(0, selected - 1)
        elif key == "down":
            selected = min(len(options) - 1, selected + 1)
        elif key == "left":
            selected = max(0, selected - visible)
        elif key == "right":
            selected = min(len(options) - 1, selected + visible)
        elif key in ("a", "b"):
            return

# Mode 1: Install firmware
def install_firmware():
    try:
        bios_dir = choose_directory_interactive(
            "Firmware: Select Directory", EKA_BIOS_DIR)
    except GoBack:
        return

    rpkg_files = sorted(glob.glob(os.path.join(bios_dir, "*.rpkg")) +
                        glob.glob(os.path.join(bios_dir, "*.RPKG")))
    rom_files = sorted(glob.glob(os.path.join(bios_dir, "*.rom")) +
                       glob.glob(os.path.join(bios_dir, "*.ROM")))

    if not rpkg_files:
        ok_dialog("Error", f"No .rpkg file found in:\n{bios_dir}")
        return
    if not rom_files:
        ok_dialog("Error", f"No .rom file found in:\n{bios_dir}")
        return

    rpkg = rpkg_files[0]
    if len(rpkg_files) > 1:
        try:
            idx = select_from_list("Select RPKG", [os.path.basename(f) for f in rpkg_files])
            if idx is None:
                return
            rpkg = rpkg_files[idx]
        except GoBack:
            return

    rom = rom_files[0]
    if len(rom_files) > 1:
        try:
            idx = select_from_list("Select ROM", [os.path.basename(f) for f in rom_files])
            if idx is None:
                return
            rom = rom_files[idx]
        except GoBack:
            return

    info = (
        f"RPKG: {os.path.basename(rpkg)}\n"
        f"ROM:  {os.path.basename(rom)}\n\n"
        f"Install firmware?"
    )
    if not confirm_dialog("Install Firmware", info):
        return

    seed_dir = os.path.join(EKA_CONFIG, "data", "roms", "rm-409")
    os.makedirs(seed_dir, exist_ok=True)
    try:
        shutil.copy2(rom, os.path.join(seed_dir, os.path.basename(rom)))
    except Exception:
        pass

    clear_screen()
    print("Installing firmware...", flush=True)
    print(f"  {os.path.basename(rpkg)}", flush=True)
    print(f"  {os.path.basename(rom)}", flush=True)
    print("\nThis may take a few minutes...", flush=True)

    ret = run_eka(["--installdevice", rpkg, rom], timeout=1800)

    if eka_success(ret):
        _autoset_device_from_zdrive()
        ok_dialog("Done", "Firmware installed successfully!\n\n(Non-zero exit after install is normal)\n\nDevice index auto-set in config.yml.")
    else:
        ok_dialog("Error", f"Installation failed (code {ret})\n\nSee log: {EKA_LOG}")

# Mode 2: Install SIS games
# ---------------------------------------------------------------------------
# SIS format detection
# SISv2 magic: 0x10201A7A little-endian (Symbian OS 9 / S60 3rd+ ed)
# SISv1: UID2 = 0x1000006D at offset 4 (Symbian OS 6-8 / S60 1st+2nd ed)
_SIS_V2_MAGIC = b'\x7a\x1a\x20\x10'
_ZIP_MAGIC    = b'\x50\x4b\x03\x04'   # PK.. — SISX is a ZIP archive containing content.sis

# Known SISv1 UID2 values (bytes 4-7)
_SIS_V1_UID2_VALUES = {
    0x1000006D,   # Standard SIS installer UID (all S60 editions)
    0x10003A12,   # Rare early EPOC/ER5 SIS variant
}

# Platform UIDs embedded in SISv2 body (little-endian).
# Listed most-specific first so the first match wins.
# These appear in SisInfo dependency or platform-requirements blocks.
_SIS_PLATFORM_SIGNATURES: List[Tuple[bytes, str]] = [
    # S60 5th Ed variants (most specific first)
    (b'\x0b\x6b\x28\x10', "s60v5"),   # 0x10286B0B  S60 5th Ed FP2
    (b'\x90\x30\x28\x10', "s60v5"),   # 0x10283090  S60 5th Ed FP1
    (b'\x06\x2f\x28\x10', "s60v5"),   # 0x10282F06  S60 5th Ed (base)
    # S60 3rd Ed variants
    (b'\x13\x35\x28\x10', "s60v3"),   # 0x10283513  S60 3rd Ed FP2
    (b'\xae\x52\x27\x10', "s60v3"),   # 0x102752AE  S60 3rd Ed FP1
    (b'\xbe\x32\x20\x10', "s60v3"),   # 0x102032BE  S60 3rd Ed (base)
    # N-Gage 2.0 runtime dependency → implies S60 3rd Ed / RM-409
    (b'\x78\x3b\x00\x20', "s60v3"),   # 0x20003B78  N-Gage 2.0 ngiplaycommon
    # S60 2nd Ed variants
    (b'\xd2\x8e\x1f\x10', "s60v2"),   # 0x101F8ED2  S60 2nd Ed FP3
    (b'\x61\x79\x1f\x10', "s60v2"),   # 0x101F7961  S60 2nd Ed (base/FP1/FP2)
    # S60 1st Ed
    (b'\x88\x6f\x1f\x10', "s60v1"),   # 0x101F6F88  S60 1st Ed
]

# Human labels and recommended devices per platform key
_PLATFORM_INFO = {
    "s60v1":    ("S60 1st Ed",           "N-Gage 1  (NEM-4 / RM-26)"),
    "s60v2":    ("S60 2nd Ed",           "N-Gage 1  (NEM-4 / RM-26)"),
    "s60v3":    ("S60 3rd Ed",           "N-Gage 2.0  (RM-409)"),
    "s60v5":    ("S60 5th Ed",           "S60v5  (RM-356)"),
    "sisv1":    ("S60 1st/2nd Ed",       "N-Gage 1  (NEM-4 / RM-26)"),
    "unknown":  ("Unknown format",       "—"),
}

# SISv2 UID3 ranges used as last-resort heuristic when no platform
# dependency signature is found in the scanned portion of the file.
_UID3_PLATFORM_RANGES: List[Tuple[int, int, str]] = [
    (0x20000000, 0x2FFFFFFF, "s60v3"),   # N-Gage 2.0 / S60 3rd Ed publisher range
    (0xA0000000, 0xAFFFFFFF, "s60v3"),   # Gameloft / 3rd-party S60 3rd Ed UIDs
]

# Display order for grouped scan view
_PLATFORM_ORDER = ["s60v1", "s60v2", "s60v3", "s60v5", "sisv1", "unknown"]


def _detect_sis_from_data(data: bytes) -> str:
    """Detect platform from raw SIS bytes (used for both plain SIS and SISX content)."""
    import struct
    if len(data) < 4:
        return "unknown"

    header = data[:12]

    # SISv1: identified by UID2 at offset 4
    if len(header) >= 8:
        uid2 = struct.unpack_from("<I", header, 4)[0]
        if uid2 in _SIS_V1_UID2_VALUES:
            return "sisv1"

    if header[0:4] != _SIS_V2_MAGIC:
        return "unknown"

    # Scan body in chunks for platform UIDs (reuse same logic as file-based path)
    _CHUNK    = 262144
    _MAX_SCAN = 4 * 1024 * 1024
    scanned   = 0
    overlap   = b""
    offset    = 0
    while scanned < _MAX_SCAN and offset < len(data):
        chunk  = data[offset:offset + _CHUNK]
        window = overlap + chunk
        for sig, key in _SIS_PLATFORM_SIGNATURES:
            if sig in window:
                return key
        overlap  = window[-3:]
        scanned += len(chunk)
        offset  += _CHUNK

    # UID3 range heuristic
    if len(header) >= 12:
        uid3 = struct.unpack_from("<I", header, 8)[0]
        for lo, hi, key in _UID3_PLATFORM_RANGES:
            if lo <= uid3 <= hi:
                return key

    return "s60v3"


def detect_sis_platform(path: str) -> str:
    """Detect SIS platform key: s60v1/s60v2/s60v3/s60v5/sisv1/unknown.

    Handles both plain .sis files and .sisx (ZIP-wrapped) packages.
    Strategy:
    1. Detect file type by magic bytes (ZIP vs SIS).
    2. For SISX: extract content.sis from ZIP and analyse its bytes.
    3. For SIS: scan up to 4 MB in 256 KB chunks with 3-byte overlap.
    4. If no platform signature found: try UID3 range heuristic.
    5. SISv2 with no match -> default to s60v3.
    """
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
    except Exception:
        return "unknown"

    if len(magic) < 4:
        return "unknown"

    # SISX = ZIP archive (PK magic)
    if magic == _ZIP_MAGIC:
        try:
            import zipfile
            with zipfile.ZipFile(path, "r") as zf:
                sis_name = next(
                    (n for n in zf.namelist() if n.lower() == "content.sis"),
                    None
                )
                if sis_name is None:
                    sis_name = next(
                        (n for n in zf.namelist() if n.lower().endswith(".sis")),
                        None
                    )
                if sis_name:
                    data = zf.read(sis_name)
                    return _detect_sis_from_data(data)
        except Exception:
            pass
        return "unknown"

    # Plain SIS file — read up to 4 MB for analysis
    try:
        with open(path, "rb") as f:
            data = f.read(4 * 1024 * 1024)
        return _detect_sis_from_data(data)
    except Exception:
        return "unknown"

def sis_platform_hint(path: str) -> str:
    """Return a short human-readable platform hint for display."""
    key = detect_sis_platform(path)
    info = _PLATFORM_INFO.get(key, _PLATFORM_INFO["unknown"])
    return f"{info[0]}  →  {info[1]}"

# Scan SIS files by platform
def scan_sis_by_platform():
    try:
        sis_dir = choose_directory_interactive(
            "Scan SIS/SISX: Select Directory", EKA_ROMS_DIR)
    except GoBack:
        return

    clear_screen()
    print("Scanning SIS/SISX files...", flush=True)

    sis_files = find_sis_files_recursive(sis_dir)

    if not sis_files:
        ok_dialog("Scan Result", f"No .sis or .sisx files found in:\n{sis_dir}")
        return

    # Group files by platform
    groups: dict = {}
    for f in sis_files:
        key = detect_sis_platform(f)
        groups.setdefault(key, []).append(f)

    # Build summary menu entries in fixed order
    present_keys = [k for k in _PLATFORM_ORDER if k in groups]
    summary_options: List[str] = []
    for key in present_keys:
        info = _PLATFORM_INFO.get(key, _PLATFORM_INFO["unknown"])
        count = len(groups[key])
        summary_options.append(
            f"[{count:3d} file(s)]  {info[0]}  →  {info[1]}"
        )

    info_text = f"Found {len(sis_files)} SIS/SISX file(s) in:\n{sis_dir}\n\nSelect a platform group to install:"

    while True:
        try:
            idx = select_from_list("Scan: Select Platform Group",
                                   summary_options, info_text, visible=10)
        except GoBack:
            return

        if idx is None:
            return

        chosen_key = present_keys[idx]
        chosen_files = groups[chosen_key]
        info = _PLATFORM_INFO[chosen_key]

        file_options = [get_relative_path(f, sis_dir) for f in chosen_files]
        group_info = (f"Platform: {info[0]}  →  {info[1]}\n"
                      f"Directory: {sis_dir}\n\n"
                      f"Toggle files with A, toggle ALL with X, press Y to install.")

        try:
            selected_indexes = select_multiple_from_list(
                f"Select Files: {info[0]}",
                file_options,
                group_info,
                visible=14
            )
        except GoBack:
            continue

        if not selected_indexes:
            ok_dialog("Scan Installer", "No files selected.")
            continue

        selected_files = [chosen_files[i] for i in selected_indexes]

        if not select_and_set_device(f"install {info[0]} files"):
            continue
        scan_device_name = get_current_device_name() or ""

        if not confirm_dialog(
            "Confirm Install",
            f"Install {len(selected_files)} file(s)?\n\n"
            f"Platform: {info[0]}\n"
            f"Recommended device: {info[1]}\n\n"
            + "\n".join(get_relative_path(f, sis_dir) for f in selected_files[:8])
            + ("\n..." if len(selected_files) > 8 else "")
        ):
            continue

        image_out_dir = os.path.join(sis_dir, "media", "images")
        success = 0
        fail = 0
        failed_files = []
        artwork_copied = 0
        artwork_failed = 0

        for pos, sis_file in enumerate(selected_files, start=1):
            clear_screen()
            rel_name = get_relative_path(sis_file, sis_dir)
            print(f"Installing {pos}/{len(selected_files)}:")
            print(f"  {rel_name}")
            print(f"  Platform: {info[0]}", flush=True)

            before_apps = get_installed_apps_map()
            ret = run_eka(["--install", sis_file])
            after_apps = get_installed_apps_map()

            if eka_success(ret):
                success += 1
                log(f"Installed: {sis_file}")
                new_app = find_new_app_after_install(before_apps, after_apps)
                if new_app:
                    app_name, uid = new_app
                    write_uid_files([(app_name, uid)], EKA_ROMS_DIR, scan_device_name)
                    copied = copy_matching_image_for_uid(
                        os.path.dirname(sis_file), app_name, image_out_dir)
                    if copied:
                        artwork_copied += 1
                    else:
                        artwork_failed += 1
                else:
                    artwork_failed += 1
            else:
                fail += 1
                failed_files.append(rel_name)
                log(f"Failed ({ret}): {sis_file}")

        result = (f"Platform: {info[0]}\n\n"
                  f"Installed: {success}\n"
                  f"Failed: {fail}\n"
                  f"Artwork copied: {artwork_copied}\n"
                  f"Artwork unresolved: {artwork_failed}")
        if failed_files:
            result += "\n\nFailed files:\n" + "\n".join(failed_files[:8])
            result += f"\n\nSee log: {EKA_LOG}"

        ok_dialog("Install Result", result)

def find_sis_files_recursive(root_dir: str) -> List[str]:
    sis_files: List[str] = []
    valid_exts = (".sis", ".sisx")
    for current_root, _, files in os.walk(root_dir):
        for name in files:
            if name.lower().endswith(valid_exts):
                sis_files.append(os.path.join(current_root, name))
    return sorted(sis_files, key=lambda p: p.lower())

def get_relative_path(path: str, base: str) -> str:
    try:
        rel = os.path.relpath(path, base)
        return rel.replace("\\", "/")
    except Exception:
        return os.path.basename(path)

def get_installed_apps_map() -> dict:
    ret, output = run_eka_capture(["--listapp"])
    if ret != 0 and not output.strip():
        return {}
    return {uid.lower(): name.strip() for name, uid in parse_listapp_output(output)}

def find_new_app_after_install(before_apps: dict, after_apps: dict) -> Optional[Tuple[str, str]]:
    new_uids = [uid for uid in after_apps if uid not in before_apps]
    if len(new_uids) == 1:
        uid = new_uids[0]
        return after_apps[uid], uid

    candidates = []
    for uid in new_uids:
        name = after_apps[uid]
        if not is_system_app(name):
            candidates.append((name, uid))

    if len(candidates) == 1:
        return candidates[0]

    if candidates:
        return candidates[0]

    return None

def copy_matching_image_for_uid(source_folder: str, app_name: str, uid_output_dir: str) -> Optional[str]:
    _exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
    try:
        _cands = sorted([os.path.join(source_folder, n) for n in os.listdir(source_folder)
                         if os.path.isfile(os.path.join(source_folder, n)) and n.lower().endswith(_exts)],
                        key=lambda p: os.path.basename(p).lower())
    except Exception:
        return None
    if not _cands:
        return None
    image_src = _cands[0]

    os.makedirs(uid_output_dir, exist_ok=True)

    safe_name = sanitize_uid_name(app_name)
    ext = os.path.splitext(image_src)[1].lower()
    target_name = f"{safe_name}{ext}"
    target_path = os.path.join(uid_output_dir, target_name)

    try:
        shutil.copy2(image_src, target_path)
        log(f"Copied artwork: {image_src} -> {target_path}")
        return target_name
    except Exception as ex:
        log(f"Failed to copy artwork {image_src} -> {target_path}: {ex}")
        return None

# Device selection helper (used by install_sis, create_uid_launchers, uninstall_apps)
def select_and_set_device(action_label: str) -> bool:
    """Show device picker, set config.yml, return True on success."""
    clear_screen()
    print("Loading installed devices...", flush=True)

    devices = get_valid_installed_devices()

    if not devices:
        ok_dialog("Error", f"No installed devices found.\n\nPlease install firmware first.\n\nSee log: {EKA_LOG}")
        return False

    current_device = get_current_device_index()
    options: List[str] = []

    for device_num, device_name in devices:
        label = f"{device_num} : {device_name}"
        if current_device is not None and device_num == current_device:
            label += "  [CURRENT]"
        options.append(label)

    try:
        idx = select_from_list("Select Device", options,
                               f"Select device for: {action_label}", visible=16)
    except GoBack:
        return False

    if idx is None:
        return False

    device_num, device_name = devices[idx]

    if not confirm_dialog(
        "Confirm Device",
        f"Use this device for: {action_label}\n\n{device_num} : {device_name}"
    ):
        return False

    try:
        set_device_index(device_num)
        log(f"Device set to {device_num} for: {action_label}")
        return True
    except Exception as ex:
        log(f"Failed to set device: {ex}")
        ok_dialog("Error", f"Could not set device\n\nSee log: {EKA_LOG}")
        return False

def install_sis():
    if not select_and_set_device("SIS/SISX installation"):
        return

    try:
        sis_dir = choose_directory_interactive(
            "SIS/SISX: Select Directory", EKA_ROMS_DIR,
            require_ext=[".sis", ".sisx"])
    except GoBack:
        return

    sis_files = find_sis_files_recursive(sis_dir)

    if not sis_files:
        ok_dialog("Error", f"No .sis or .sisx files found in:\n{sis_dir}")
        return

    image_out_dir = os.path.join(sis_dir, "media", "images")

    try:
        hints = {}
        for _f in sis_files:
            _h = sis_platform_hint(_f)
            hints[_h] = hints.get(_h, 0) + 1
        hint_lines = "\n".join(f"  {v}x  {k}" for k, v in sorted(hints.items()))
        hint_info = (f"{len(sis_files)} file(s) found recursively in:\n{sis_dir}\n\n"
                     f"Detected platforms:\n{hint_lines}")

        mode_idx = select_from_list(
            "SIS/SISX Installer Mode",
            [
                "Install all SIS/SISX files (recursive)",
                "Select SIS/SISX files individually (recursive)",
            ],
            hint_info
        )
    except GoBack:
        return

    if mode_idx is None:
        return

    selected_files = []

    if mode_idx == 0:
        if not confirm_dialog(
            "Install All",
            f"Install all {len(sis_files)} SIS/SISX files recursively?\n\nDirectory:\n{sis_dir}"
        ):
            return
        selected_files = sis_files
    else:
        sis_options = [f"{get_relative_path(f, sis_dir)}  [{sis_platform_hint(f)}]" for f in sis_files]

        try:
            selected_indexes = select_multiple_from_list(
                "Select SIS/SISX Files",
                sis_options,
                f"Directory:\n{sis_dir}\n\nToggle files with A, press Y to install.",
                visible=14
            )
        except GoBack:
            return

        if not selected_indexes:
            ok_dialog("SIS/SISX Installer", "No SIS/SISX files selected.")
            return

        selected_files = [sis_files[i] for i in selected_indexes]

        if not confirm_dialog(
            "Install Selected",
            f"Install {len(selected_files)} selected SIS/SISX file(s)?"
        ):
            return

    success = 0
    fail = 0
    failed_files = []
    artwork_copied = 0
    artwork_failed = 0

    for pos, sis_file in enumerate(selected_files, start=1):
        clear_screen()
        rel_name = get_relative_path(sis_file, sis_dir)
        hint = sis_platform_hint(sis_file)
        print(f"Installing {pos}/{len(selected_files)}:")
        print(f"  {rel_name}")
        print(f"  Platform: {hint}", flush=True)

        before_apps = get_installed_apps_map()
        ret = run_eka(["--install", sis_file])
        after_apps = get_installed_apps_map()

        if eka_success(ret):
            success += 1
            log(f"SIS/SISX installed successfully: {sis_file}")

            new_app = find_new_app_after_install(before_apps, after_apps)
            if new_app:
                app_name, uid = new_app
                copied_name = copy_matching_image_for_uid(
                    os.path.dirname(sis_file),
                    app_name,
                    image_out_dir
                )
                if copied_name:
                    artwork_copied += 1
                    log(f"Matched artwork for app '{app_name}' ({uid}): {copied_name}")
                else:
                    artwork_failed += 1
                    log(f"No artwork copied for app '{app_name}' ({uid}) from folder {os.path.dirname(sis_file)}")
            else:
                artwork_failed += 1
                log(f"Could not determine new app UID/name after install: {sis_file}")
        else:
            fail += 1
            failed_files.append(rel_name)
            log(f"SIS/SISX install failed ({ret}): {sis_file}")

    if fail == 0:
        ok_dialog(
            "Done",
            f"Installation completed successfully.\n\n"
            f"Installed: {success}\n"
            f"Failed: {fail}\n"
            f"Artwork copied: {artwork_copied}\n"
            f"Artwork unresolved: {artwork_failed}\n\n"
            f"Artwork target:\n{image_out_dir}"
        )
    else:
        preview = "\n".join(failed_files[:8])
        more = ""
        if len(failed_files) > 8:
            more = f"\n... and {len(failed_files) - 8} more"

        ok_dialog(
            "Installation Result",
            f"Completed.\n\n"
            f"Installed: {success}\n"
            f"Failed: {fail}\n"
            f"Artwork copied: {artwork_copied}\n"
            f"Artwork unresolved: {artwork_failed}\n\n"
            f"Failed files:\n{preview}{more}\n\nSee log:\n{EKA_LOG}"
        )

# UID launcher creator
def parse_listapp_output(output: str) -> List[Tuple[str, str]]:
    apps: List[Tuple[str, str]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        match = re.match(r'^\d+\s*:\s*(.*?)\s*\(UID:\s*(0x[0-9a-fA-F]+)\)\s*$', line)
        if match:
            name = match.group(1).strip()
            uid = match.group(2).strip().lower()
            apps.append((name, uid))
    return apps

def sanitize_uid_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = name.replace("'", "_")
    name = re.sub(r'\s+', ' ', name).strip()
    while name.startswith('.'):
        name = '_' + name[1:]
    if not name:
        name = 'unnamed'
    return name

def is_system_app(name: str) -> bool:
    name_lc = name.lower().strip()
    system_names = {
        '', 'installer', 'applications', 'help', 'screensaver', 'telephone', 'app. manager',
        'messaging', 'recorder', 'multimedia', 'settings', 'call divert', 'sysap', 'startup',
        'voice mailbox', 'profiles', 'to-do', 'calendar', 'calculator', 'clock', 'notes',
        'speed dial', 'favourites', 'bluetooth', 'ussd', 'composer', 'fixed dialling',
        'autolock', 'save certificate', 'info message', 'bounce', 'about product',
        'services', 'pushviewer', 'download', 'realone player', 'screen shot',
        'memory card', 'converter', 'videoui', 'contacts', 'images', 'menu',
        'cell broadcast', 'log', 'e-mail', 'sim services', 'service nos.',
        'sim directory', 'radio', 'music player', 'unlockmmc'
    }
    return name_lc in system_names

def build_uid_candidates(apps: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], int, int, int]:
    candidates: List[Tuple[str, str]] = []
    seen_uids = set()
    skipped_system = 0
    skipped_blank = 0
    skipped_dup = 0

    for name, uid in apps:
        name = name.strip()
        uid = uid.strip().lower()

        if not name:
            skipped_blank += 1
            continue
        if uid in seen_uids:
            skipped_dup += 1
            continue
        if is_system_app(name):
            seen_uids.add(uid)
            skipped_system += 1
            continue

        seen_uids.add(uid)
        candidates.append((name, uid))

    return candidates, skipped_system, skipped_blank, skipped_dup

def show_multi_select_menu(title: str, options: List[str], checked: set, selected: int = 0,
                           info: str = "", offset: int = 0, visible: int = 16) -> None:
    clear_screen()
    print("=" * 72)
    print(f"  E K A 2 L 1   I N S T A L L E R  -  {title}")
    print("=" * 72)
    if info:
        print(f"\n{info}\n")
    total = len(options)
    end = min(offset + visible, total)
    for i in range(offset, end):
        cursor = "  > " if i == selected else "    "
        mark = "[x]" if i in checked else "[ ]"
        print(f"{cursor}{mark} {options[i]}")
    if end < total:
        print("    ...")
    print("\n" + "-" * 72)
    print("D-Pad: Navigate | A: Toggle | X: Toggle All | Y: Confirm | B: Back | Select: Quit")
    print("-" * 72)
    sys.stdout.flush()

def select_multiple_from_list(title: str, items: List[str], info: str = "",
                              visible: int = 16) -> Optional[List[int]]:
    if not items:
        return []

    total = len(items)
    selected = 0
    offset = 0
    checked = set()

    while True:
        if selected < offset:
            offset = selected
        elif selected >= offset + visible:
            offset = selected - visible + 1

        offset = max(0, min(offset, max(0, total - visible)))
        show_multi_select_menu(title, items, checked, selected, info, offset, visible)

        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        elif key == 'up':
            selected = max(0, selected - 1)
        elif key == 'down':
            selected = min(total - 1, selected + 1)
        elif key == 'left':
            selected = max(0, selected - visible)
        elif key == 'right':
            selected = min(total - 1, selected + visible)
        elif key == 'a':
            if selected in checked:
                checked.remove(selected)
            else:
                checked.add(selected)
        elif key == 'x':
            if len(checked) == total:
                checked.clear()
            else:
                checked.update(range(total))
        elif key == 'y':
            return sorted(checked)
        elif key == 'b':
            raise GoBack()

def show_available_uid_apps(candidates: List[Tuple[str, str]]) -> None:
    if not candidates:
        ok_dialog('Available Apps', 'No launchable non-system apps found.')
        return

    options = [f'{name} ({uid})' for name, uid in candidates]
    selected = 0
    offset = 0
    visible = 14

    while True:
        if selected < offset:
            offset = selected
        elif selected >= offset + visible:
            offset = selected - visible + 1

        offset = max(0, min(offset, max(0, len(options) - visible)))
        show_menu(
            'Available Apps',
            options,
            selected,
            f'Available launchable apps: {len(candidates)}\n\nPress A to continue or B to go back.',
            offset,
            visible
        )

        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        elif key == 'up':
            selected = max(0, selected - 1)
        elif key == 'down':
            selected = min(len(options) - 1, selected + 1)
        elif key == 'left':
            selected = max(0, selected - visible)
        elif key == 'right':
            selected = min(len(options) - 1, selected + visible)
        elif key == 'a':
            return
        elif key == 'b':
            raise GoBack()

def show_generated_uid_list(created_entries: List[Tuple[str, str, str]], out_dir: str) -> None:
    if not created_entries:
        ok_dialog('Generated UID Files', f'No UID files were created.\n\nOutput: {out_dir}')
        return

    options = [f"{name} -> {uid} [{filename}]" for name, uid, filename in created_entries]
    selected = 0
    offset = 0
    visible = 14

    while True:
        if selected < offset:
            offset = selected
        elif selected >= offset + visible:
            offset = selected - visible + 1

        offset = max(0, min(offset, max(0, len(options) - visible)))
        show_menu(
            'Generated UID Files',
            options,
            selected,
            f'Output: {out_dir}\nCreated: {len(created_entries)}\n\nPress A or B to return.',
            offset,
            visible
        )

        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        elif key == 'up':
            selected = max(0, selected - 1)
        elif key == 'down':
            selected = min(len(options) - 1, selected + 1)
        elif key == 'left':
            selected = max(0, selected - visible)
        elif key == 'right':
            selected = min(len(options) - 1, selected + visible)
        elif key in ('a', 'b'):
            return

def write_uid_files(selected_apps: List[Tuple[str, str]], out_dir: str,
                    device_name: str = "") -> List[Tuple[str, str, str]]:
    created_entries: List[Tuple[str, str, str]] = []
    os.makedirs(out_dir, exist_ok=True)

    for name, uid in selected_apps:
        safe_name = sanitize_uid_name(name)
        target = os.path.join(out_dir, f'{safe_name}.uid')
        if os.path.exists(target):
            target = os.path.join(out_dir, f'{safe_name}_{uid}.uid')

        try:
            with open(target, 'w', encoding='utf-8') as f:
                f.write(uid + '\n')
                if device_name:
                    f.write(device_name.lower() + '\n')
            log(f'Created UID launcher: {target} -> {uid} (device: {device_name or "none"})')
            created_entries.append((name, uid, os.path.basename(target)))
        except Exception as ex:
            log(f'Failed to create UID launcher {target}: {ex}')

    return created_entries

def xml_escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))

def create_uid_gamelist():
    try:
        uid_dir = choose_directory_interactive(
            "Gamelist: Select UID Directory", EKA_ROMS_DIR)
    except GoBack:
        return

    uid_files = sorted(glob.glob(os.path.join(uid_dir, "*.uid")) +
                       glob.glob(os.path.join(uid_dir, "*.UID")))

    if not uid_files:
        ok_dialog("Error", f"No .uid files found in:\n{uid_dir}")
        return

    # gamelist.xml always goes to EKA_ROMS_DIR so that <path> entries are
    # correctly relative to the EmulationStation ROM root.
    out_dir = EKA_ROMS_DIR
    out_file = os.path.join(out_dir, "gamelist.xml")
    image_dir = os.path.join(uid_dir, "media", "images")
    backup_file = None

    if os.path.exists(out_file):
        if not confirm_dialog(
            "Overwrite?",
            f"gamelist.xml already exists in:\n{out_dir}\n\nOverwrite it? A backup will be created."
        ):
            return
        import datetime
        import shutil
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(out_dir, f"gamelist.xml.{ts}.bak")
        try:
            shutil.copy2(out_file, backup_file)
            log(f"Backup created: {backup_file}")
        except Exception as ex:
            log(f"Warning: could not create backup: {ex}")
            backup_file = None

    lines = ['<?xml version="1.0"?>', '<gameList>']

    for uid_file in uid_files:
        base = os.path.basename(uid_file)
        name = os.path.splitext(base)[0]

        try:
            rel_path = os.path.relpath(uid_file, out_dir).replace("\\", "/")
        except Exception:
            rel_path = base
        if not rel_path.startswith("./") and not rel_path.startswith("/"):
            rel_path = "./" + rel_path

        image_tag = "./media/images/ngage.png"
        for ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            candidate = os.path.join(image_dir, name + ext)
            if os.path.exists(candidate):
                try:
                    img_rel = os.path.relpath(candidate, out_dir).replace("\\", "/")
                except Exception:
                    img_rel = f"media/images/{name + ext}"
                if not img_rel.startswith("./") and not img_rel.startswith("/"):
                    img_rel = "./" + img_rel
                image_tag = xml_escape(img_rel)
                break

        uid_device = ""
        try:
            with open(uid_file, encoding="utf-8") as _uf:
                _lines = _uf.read().splitlines()
                if len(_lines) >= 2 and _lines[1].strip():
                    uid_device = _lines[1].strip()
        except Exception:
            pass

        desc = name
        if uid_device:
            desc = f"[{uid_device.upper()}] {name}"

        lines.append('\t<game>')
        lines.append(f'\t\t<path>{xml_escape(rel_path)}</path>')
        name_tag = '\t\t<' + 'name' + '>' + xml_escape(name) + '</' + 'name' + '>'
        lines.append(name_tag)
        lines.append(f'\t\t<desc>{xml_escape(desc)}</desc>')
        lines.append(f'\t\t<image>{image_tag}</image>')
        lines.append('\t\t<video>./media/videos/ngage.mp4</video>')
        lines.append('\t</game>')

    lines.append('</gameList>')

    try:
        with open(out_file, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as ex:
        log(f"Failed to write gamelist.xml {out_file}: {ex}")
        ok_dialog("Error", f"Failed to write gamelist.xml:\n{ex}")
        return

    backup_msg = f"\nBackup: {backup_file}" if backup_file else ""
    ok_dialog(
        "Done",
        f"gamelist.xml created successfully.\n\n"
        f"UID files: {len(uid_files)}\n"
        f"Output:\n{out_file}"
        + backup_msg
    )

def create_uid_launchers():
    if not select_and_set_device("UID launcher creation"):
        return

    try:
        out_dir = choose_directory_interactive(
            'UID Creator: Select Output Directory', '/storage/roms')
    except GoBack:
        return

    clear_screen()
    print('Loading installed app list...', flush=True)

    ret, output = run_eka_capture(['--listapp'])
    apps = parse_listapp_output(output)

    if ret != 0 and not apps:
        ok_dialog('Error', f'Could not get app list.\n\nSee log: {EKA_LOG}')
        return

    if not apps:
        ok_dialog('Error', 'No installed apps found.')
        return

    candidates, skipped_system, skipped_blank, skipped_dup = build_uid_candidates(apps)
    candidates = sorted(candidates, key=lambda item: (item[0].lower(), item[1]))

    if not candidates:
        ok_dialog('Error', 'No launchable non-system apps found.')
        return

    try:
        show_available_uid_apps(candidates)
        mode_idx = select_from_list(
            'UID Creator Mode',
            ['Create all UID launcher files', 'Select apps individually'],
            f'Output: {out_dir}\n\nAvailable apps: {len(candidates)}'
        )
    except GoBack:
        return

    if mode_idx is None:
        return

    selected_apps: List[Tuple[str, str]] = []

    if mode_idx == 0:
        if not confirm_dialog(
            'Create All UID Files',
            f'Create {len(candidates)} UID launcher files in:\n\n{out_dir}'
        ):
            return
        selected_apps = candidates
    else:
        app_options = [f'{name} ({uid})' for name, uid in candidates]
        try:
            selected_indexes = select_multiple_from_list(
                'Select Apps For UID',
                app_options,
                f'Output: {out_dir}\n\nToggle apps with A, then press Y to create.',
                visible=14
            )
        except GoBack:
            return

        if not selected_indexes:
            ok_dialog('UID Creator', 'No apps selected.')
            return

        selected_apps = [candidates[i] for i in selected_indexes]

        if not confirm_dialog(
            'Create Selected UID Files',
            f'Create {len(selected_apps)} selected UID launcher files in:\n\n{out_dir}'
        ):
            return

    device_name = get_current_device_name() or ""
    created_entries = write_uid_files(selected_apps, out_dir, device_name)

    ok_dialog(
        'Done',
        f'UID launcher creation finished.\n\n'
        f'Output: {out_dir}\n\n'
        f'Requested: {len(selected_apps)}\n'
        f'Created: {len(created_entries)}\n'
        f'Skipped system apps: {skipped_system}\n'
        f'Skipped blank names: {skipped_blank}\n'
        f'Skipped duplicate UIDs: {skipped_dup}'
    )

    show_generated_uid_list(created_entries, out_dir)

# Main
DEFAULT_CONFIG_YML = """bkg-path: ""
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

def _create_default_config():
    cfg_path = os.path.join(EKA_CONFIG, "config.yml")
    if not os.path.exists(cfg_path):
        try:
            with open(cfg_path, "w") as f:
                f.write(DEFAULT_CONFIG_YML)
            log("Created default config.yml")
            return True
        except Exception as ex:
            log(f"Failed to create config.yml: {ex}")
    return False

def _seed_bundled_files():
    install_dir = "/usr/bin/eka2l1"
    if not os.path.isdir(install_dir):
        ok_dialog("Error", f"eka2l1 install directory not found:\n{install_dir}")
        return

    clear_screen()
    print("Seeding bundled data...", flush=True)
    seeded = []

    for item in os.listdir(install_dir):
        src = os.path.join(install_dir, item)
        dst = os.path.join(EKA_CONFIG, item)
        if not os.path.exists(dst):
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                seeded.append(item)
                log(f"Seeded: {item}")
                print(f"  {item}", flush=True)
            except Exception as ex:
                log(f"Seed failed for {item}: {ex}")

    cfg_created = _create_default_config()
    if cfg_created:
        seeded.append("config.yml (default)")
        print("  config.yml (default)", flush=True)

    if seeded:
        ok_dialog("Seed Bundled Files", f"Done!\n\nCopied {len(seeded)} item(s) into:\n{EKA_CONFIG}\n\nYou can now install firmware and games.")
    else:
        ok_dialog("Seed Bundled Files", "Nothing to seed - all files already present.")

def _autoset_device_from_zdrive():
    devices_yml = os.path.join(EKA_CONFIG, "data", "devices.yml")
    z_drives_dir = os.path.join(EKA_CONFIG, "data", "drives", "z")
    cfg_path = os.path.join(EKA_CONFIG, "config.yml")

    if not os.path.isfile(devices_yml) or not os.path.isdir(z_drives_dir):
        return

    device_keys = []
    try:
        with open(devices_yml, "r") as f:
            for line in f:
                stripped = line.rstrip()
                if stripped and not stripped.startswith(" ") and stripped.endswith(":"):
                    device_keys.append(stripped[:-1])
    except Exception as ex:
        log(f"_autoset_device_from_zdrive: could not read devices.yml: {ex}")
        return

    available_z = {
        d.lower(): d for d in os.listdir(z_drives_dir)
        if os.path.isdir(os.path.join(z_drives_dir, d))
    }

    match_index = None
    for i, key in enumerate(device_keys):
        if key.lower() in available_z:
            match_index = i
            log(f"_autoset_device_from_zdrive: matched device {key} at index {i}")
            break

    if match_index is None:
        log("_autoset_device_from_zdrive: no matching Z-drive found")
        return

    if not os.path.isfile(cfg_path):
        _create_default_config()

    try:
        with open(cfg_path, "r") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.startswith("device:"):
                new_lines.append(f"device: {match_index}\n")
            else:
                new_lines.append(line)

        with open(cfg_path, "w") as f:
            f.writelines(new_lines)

        log(f"_autoset_device_from_zdrive: set device: {match_index}")
    except Exception as ex:
        log(f"_autoset_device_from_zdrive: failed to update config.yml: {ex}")

def _import_preconfigured():
    try:
        src_dir = choose_directory_interactive(
            "Select source directory (must contain a 'data' folder)",
            "/storage/roms/bios/eka2l1"
        )
    except GoBack:
        return

    data_src = os.path.join(src_dir, "data")
    if not os.path.isdir(data_src):
        ok_dialog("Error", f"No 'data' folder found in:\n{src_dir}\n\nPlease select a directory that contains a pre-configured eka2l1 'data' folder.")
        return

    data_dst = os.path.join(EKA_CONFIG, "data")
    os.makedirs(data_dst, exist_ok=True)

    total_files = sum(len(files) for _, _, files in os.walk(data_src))

    clear_screen()
    print(f"Importing data from:\n  {data_src}", flush=True)
    print(f"Only adding new files - existing files will not be overwritten.", flush=True)
    print(f"\nTotal files to process: {total_files}\n", flush=True)
    log(f"Importing pre-configured data from: {data_src} ({total_files} files)")

    added = 0
    skipped = 0
    processed = 0
    last_unblank = time.time()

    for root, dirs, files in os.walk(data_src):
        rel = os.path.relpath(root, data_src)
        dst_root = os.path.join(data_dst, rel) if rel != "." else data_dst
        os.makedirs(dst_root, exist_ok=True)

        for fname in files:
            src_file = os.path.join(root, fname)
            dst_file = os.path.join(dst_root, fname)
            processed += 1

            now = time.time()
            if now - last_unblank >= 2.0:
                unblank_framebuffer()
                last_unblank = now
                pct = int(processed * 100 / total_files) if total_files else 100
                bar_filled = pct // 5
                bar = "#" * bar_filled + "-" * (20 - bar_filled)
                print(f"\r[{bar}] {pct:3d}%  {processed}/{total_files}  (+{added} added, ={skipped} skipped)    ",
                      end='', flush=True)

            if fname == "devices.yml" and os.path.exists(dst_file):
                backup = dst_file + ".bak"
                try:
                    shutil.copy2(dst_file, backup)
                    shutil.copy2(src_file, dst_file)
                    log(f"Overwritten with backup: {dst_file}")
                    added += 1
                except Exception as ex:
                    log(f"Failed to overwrite devices.yml: {ex}")
                    skipped += 1
                continue

            if not os.path.exists(dst_file):
                try:
                    shutil.copy2(src_file, dst_file)
                    log(f"Added: {dst_file}")
                    added += 1
                except Exception as ex:
                    log(f"Failed to copy {src_file}: {ex}")
                    skipped += 1
            else:
                skipped += 1

    print(f"\r[####################] 100%  {processed}/{total_files}  (+{added} added, ={skipped} skipped)    ",
          flush=True)
    print("", flush=True)

    _autoset_device_from_zdrive()

    ok_dialog("Import Complete",
              f"Import finished!\n\n"
              f"Added: {added} file(s)\n"
              f"Skipped (already exist): {skipped} file(s)\n\n"
              f"devices.yml overwritten (backup: devices.yml.bak)\n"
              f"Device index auto-set to match available firmware.")

def first_run_setup():
    _seed_bundled_files()

# Reset
def reset_eka2l1():
    if not confirm_dialog(
        "Complete Reset",
        f"This will DELETE all eka2l1 data:\n\n{EKA_CONFIG}\n\n"
        "This includes all installed firmware, games,\n"
        "saves, and configuration.\n\n"
        "Are you absolutely sure?"
    ):
        return

    if not confirm_dialog(
        "Are you sure?",
        "Last warning!\n\nAll eka2l1 data will be permanently deleted.\n\nContinue?"
    ):
        return

    clear_screen()
    print(f"Deleting {EKA_CONFIG} ...", flush=True)
    log(f"Reset: deleting {EKA_CONFIG}")

    try:
        if os.path.isdir(EKA_CONFIG):
            shutil.rmtree(EKA_CONFIG)
            log("Reset complete.")
            ok_dialog("Reset Complete", f"Deleted:\n{EKA_CONFIG}\n\nRun 'Setup eka2l1' to reinitialise.")
        else:
            ok_dialog("Reset", f"Nothing to delete - directory not found:\n{EKA_CONFIG}")
    except Exception as ex:
        log(f"Reset failed: {ex}")
        ok_dialog("Error", f"Reset failed:\n{ex}\n\nSee log: {EKA_LOG}")

def uninstall_device():
    clear_screen()
    print("Loading installed devices...", flush=True)

    devices = get_valid_installed_devices()

    if not devices:
        ok_dialog("Uninstall Device", "No installed devices found.")
        return

    current_device = get_current_device_index()
    options: List[str] = []

    for device_num, device_name in devices:
        label = f"{device_num} : {device_name}"
        if current_device is not None and device_num == current_device:
            label += "  [CURRENT]"
        options.append(label)

    try:
        idx = select_from_list("Uninstall Device", options,
                               "Select a device to completely remove.", visible=16)
    except GoBack:
        return

    if idx is None:
        return

    device_num, device_name = devices[idx]

    if not confirm_dialog(
        "Confirm Uninstall",
        f"Remove this device and all its data?\n\n{device_num} : {device_name}\n\n"
        "This will delete:\n"
        "  - Z-drive firmware files\n"
        "  - C-drive data (saves, installed apps)\n"
        "  - ROM files\n"
        "  - devices.yml entry\n\n"
        "This cannot be undone!"
    ):
        return

    clear_screen()
    print(f"Removing device: {device_name} ...", flush=True)
    log(f"Uninstall device: {device_num} : {device_name}")

    removed = []
    errors = []

    z_drives_base = os.path.join(EKA_CONFIG, "data", "drives", "z")
    c_drives_base = os.path.join(EKA_CONFIG, "data", "drives", "c")
    roms_base     = os.path.join(EKA_CONFIG, "data", "roms")

    device_key_lower = device_name.lower()

    for base_dir, label in [
        (z_drives_base, "Z-drive"),
        (c_drives_base, "C-drive"),
        (roms_base,     "ROMs"),
    ]:
        if not os.path.isdir(base_dir):
            continue
        for entry in os.listdir(base_dir):
            if entry.lower() == device_key_lower:
                full_path = os.path.join(base_dir, entry)
                try:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                    removed.append(f"{label}: {full_path}")
                    log(f"Removed {label}: {full_path}")
                except Exception as ex:
                    errors.append(f"{label}: {full_path}\n{ex}")
                    log(f"Failed to remove {label} {full_path}: {ex}")

    # Remove entry from devices.yml
    devices_yml = os.path.join(EKA_CONFIG, "data", "devices.yml")
    if os.path.isfile(devices_yml):
        try:
            with open(devices_yml, "r") as f:
                yml_lines = f.readlines()

            new_yml: List[str] = []
            skip = False
            found = False
            for line in yml_lines:
                stripped = line.rstrip()
                # Top-level key: non-empty, not indented, ends with ':'
                if stripped and not stripped[0].isspace() and stripped.endswith(":"):
                    key = stripped[:-1].strip()
                    if key.lower() == device_key_lower:
                        skip = True
                        found = True
                        log(f"Removing devices.yml entry: {key}")
                        continue
                    else:
                        skip = False
                if not skip:
                    new_yml.append(line)

            if found:
                with open(devices_yml, "w") as f:
                    f.writelines(new_yml)
                removed.append("devices.yml entry removed")
                log(f"devices.yml updated, removed entry: {device_name}")
            else:
                log(f"devices.yml: entry '{device_name}' not found (already removed?)")
        except Exception as ex:
            errors.append(f"devices.yml: {ex}")
            log(f"Failed to update devices.yml: {ex}")

    # Auto-set device index after removal
    _autoset_device_from_zdrive()

    if errors:
        err_text = "\n".join(errors[:3])
        ok_dialog("Uninstall Result",
                  f"Device removed with errors.\n\n"
                  f"Removed: {len(removed)}\n"
                  f"Errors: {len(errors)}\n\n{err_text}\n\nSee log: {EKA_LOG}")
    else:
        ok_dialog("Uninstall Complete",
                  f"Device removed successfully.\n\n"
                  f"{device_num} : {device_name}\n\n"
                  f"Removed {len(removed)} item(s).\n\n"
                  f"Device index in config.yml auto-updated.")

# Uninstall apps / games
def uninstall_apps():
    if not select_and_set_device("app / game uninstall"):
        return

    clear_screen()
    print("Loading installed app list...", flush=True)

    ret, output = run_eka_capture(["--listapp"])
    apps = parse_listapp_output(output)

    if ret != 0 and not apps:
        ok_dialog("Error", f"Could not get app list.\n\nSee log: {EKA_LOG}")
        return

    if not apps:
        ok_dialog("Error", "No installed apps found.")
        return

    candidates, skipped_system, skipped_blank, skipped_dup = build_uid_candidates(apps)
    candidates = sorted(candidates, key=lambda item: (item[0].lower(), item[1]))

    if not candidates:
        ok_dialog("Error", "No removable non-system apps found.")
        return

    app_options = [f"{name}  ({uid})" for name, uid in candidates]

    try:
        selected_indexes = select_multiple_from_list(
            "Uninstall Apps / Games",
            app_options,
            f"Toggle apps with A, then press Y to uninstall.\n\nInstalled apps: {len(candidates)}",
            visible=14
        )
    except GoBack:
        return

    if not selected_indexes:
        ok_dialog("Uninstall Apps", "No apps selected.")
        return

    selected_apps = [candidates[i] for i in selected_indexes]

    if not confirm_dialog(
        "Confirm Uninstall",
        f"Uninstall {len(selected_apps)} app(s)?\n\n"
        + "\n".join(f"  {name} ({uid})" for name, uid in selected_apps[:8])
        + ("\n  ..." if len(selected_apps) > 8 else "")
        + "\n\nThis also removes matching .uid launcher files."
    ):
        return

    success = 0
    fail = 0
    uid_removed = 0

    for name, uid in selected_apps:
        clear_screen()
        print(f"Uninstalling: {name} ({uid})", flush=True)
        ret = run_eka(["--remove", uid])
        if eka_success(ret):
            success += 1
            log(f"Uninstalled app: {name} ({uid})")
            safe_name = sanitize_uid_name(name)
            for candidate_name in (f"{safe_name}.uid", f"{safe_name}_{uid}.uid"):
                uid_path = os.path.join(EKA_ROMS_DIR, candidate_name)
                if os.path.exists(uid_path):
                    try:
                        os.remove(uid_path)
                        uid_removed += 1
                        log(f"Removed .uid launcher: {uid_path}")
                    except Exception as ex:
                        log(f"Failed to remove .uid launcher {uid_path}: {ex}")
        else:
            fail += 1
            log(f"Failed to uninstall app: {name} ({uid}) - code {ret}")

    ok_dialog(
        "Uninstall Complete",
        f"Done!\n\n"
        f"Uninstalled: {success}\n"
        f"Failed: {fail}\n"
        f".uid launchers removed: {uid_removed}\n\n"
        + (f"See log: {EKA_LOG}" if fail else "")
    )

def show_installed_apps():
    if not select_and_set_device("show installed apps"):
        return

    clear_screen()
    print("Loading installed app list...", flush=True)

    ret, output = run_eka_capture(["--listapp"])
    apps = parse_listapp_output(output)

    if not apps:
        ok_dialog("Installed Apps", "No installed apps found.")
        return

    apps_sorted = sorted(apps, key=lambda x: x[0].lower())
    options = [f"{name}  ({uid})" for name, uid in apps_sorted]

    try:
        select_from_list(
            "Installed Apps / Games",
            options,
            info=f"Total: {len(apps_sorted)} installed apps",
            visible=16
        )
    except GoBack:
        return


def main():
    preferred = sys.argv[1] if len(sys.argv) > 1 else None
    init_controller(preferred)

    os.makedirs(EKA_CONFIG, exist_ok=True)

    try:
        with open(EKA_LOG, "w") as f:
            f.write("EmuELEC eka2l1 Commander Log\n")
    except Exception:
        pass

    clear_screen()
    print("Starting eka2l1 Commander...", flush=True)
    time.sleep(0.5)

    try:
        while True:
            try:
                idx = select_from_list(
                    "Main Menu",
                    [
                        "[ RUN THIS FIRST ! ] : Setup eka2l1 (copy needed files to EmuELEC)",
                        "Import pre-configured devices-collection",
                        "Install firmware (.rpkg + .rom)",
                        "Scan SIS/SISX files by platform and install",
                        "Install games and apps (.sis/.sisx)",
                        "Create UID launcher-files from installed games and apps (.uid)",
                        "Create gamelist.xml from .uid launcher-files",
                        "Show / change current device",
                        "Convert uppercase device paths and files to lowercase",
                        "Show installed apps / games",
                        "Uninstall apps / games",
                        "Uninstall a device",
                        "Complete Reset (delete all eka2l1 data)",
                        "Exit",
                    ],
                    "What would you like to do?"
                )

                if idx is None or idx == 13:
                    break
                if idx == 0:
                    try:
                        first_run_setup()
                    except GoBack:
                        continue
                elif idx == 1:
                    try:
                        _import_preconfigured()
                    except GoBack:
                        continue
                elif idx == 2:
                    try:
                        install_firmware()
                    except GoBack:
                        continue
                elif idx == 3:
                    try:
                        scan_sis_by_platform()
                    except GoBack:
                        continue
                elif idx == 4:
                    try:
                        install_sis()
                    except GoBack:
                        continue
                elif idx == 5:
                    try:
                        create_uid_launchers()
                    except GoBack:
                        continue
                elif idx == 6:
                    try:
                        create_uid_gamelist()
                    except GoBack:
                        continue
                elif idx == 7:
                    try:
                        change_device()
                    except GoBack:
                        continue
                elif idx == 8:
                    try:
                        convert_device_paths_to_lowercase()
                    except GoBack:
                        continue
                elif idx == 9:
                    try:
                        show_installed_apps()
                    except GoBack:
                        continue
                elif idx == 10:
                    try:
                        uninstall_apps()
                    except GoBack:
                        continue
                elif idx == 11:
                    try:
                        uninstall_device()
                    except GoBack:
                        continue
                elif idx == 12:
                    try:
                        reset_eka2l1()
                    except GoBack:
                        continue
            except GoBack:
                continue

    except UserQuit:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        clear_screen()
        print("Exiting eka2l1 Commander...", flush=True)
        time.sleep(0.5)
        if controller:
            controller.close()

if __name__ == "__main__":
    main()