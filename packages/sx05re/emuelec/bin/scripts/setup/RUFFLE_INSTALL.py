#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present worstcase_scenario (https://github.com/worstcase-scenario)

import os
import glob
import re
import shutil
from typing import Dict, List, Tuple, Optional
import sys
import struct
import select
import time
from evdev import InputDevice, list_devices, ecodes as e



class UserQuit(Exception):
    pass


class GoBack(Exception):
    pass


def find_controller_device() -> str:
    patterns = re.compile(r"(pad|controller|joystick|xbox|playstation|ps[0-9]|dualshock|dualsense|8bitdo)", re.I)

    # Collect candidates: (priority, path, name)
    candidates = []
    for path in sorted(glob.glob("/dev/input/event*")):
        base = os.path.basename(path)
        name_path = f"/sys/class/input/{base}/device/name"
        devname = ""
        try:
            with open(name_path, "r", encoding="utf-8", errors="ignore") as f:
                devname = f.read().strip()
        except Exception:
            devname = ""

        priority = 0 if (devname and patterns.search(devname)) else 1
        candidates.append((priority, path, devname))

    # Try preferred candidates first
    for _, path, devname in sorted(candidates, key=lambda t: (t[0], t[1])):
        try:
            with open(path, "rb") as _f:
                pass
            if devname:
                print(f"Auto-detected controller: {devname} ({path})", flush=True)
            else:
                print(f"Auto-detected input device: {path}", flush=True)
            return path
        except Exception:
            continue

    print("Warning: No /dev/input/event* device could be opened; falling back to /dev/input/event0", flush=True)
    return "/dev/input/event0"

# ---------------------------------------------------------------------------
# Controller Input Handling
# ---------------------------------------------------------------------------

class ControllerInput:

    def __init__(self, preferred_path: Optional[str] = None):
        self.dev = wait_for_controller(preferred_path)
        self.last_hat_x = 0
        self.last_hat_y = 0

    def wait_for_input(self) -> str:
        for event in self.dev.read_loop():
            # Button presses
            if event.type == e.EV_KEY and event.value == 1:
                code = event.code

                # D-Pad (digital)
                if code == e.BTN_DPAD_UP:
                    return 'up'
                if code == e.BTN_DPAD_DOWN:
                    return 'down'
                if code == e.BTN_DPAD_LEFT:
                    return 'left'
                if code == e.BTN_DPAD_RIGHT:
                    return 'right'

                # Confirm / Back
                if code in (e.BTN_SOUTH, e.BTN_START):
                    return 'a'
                if code == e.BTN_EAST:
                    return 'b'

                # Additional buttons
                if code == e.BTN_NORTH:
                    return 'y'
                if code == e.BTN_WEST:
                    return 'x'
                if code == e.BTN_TL:
                    return 'l1'
                if code == e.BTN_TR:
                    return 'r1'

                # Quit / special
                if code in (e.BTN_SELECT, e.BTN_MODE):
                    return 'select'

                # Some controllers map D-pad to face buttons/keys; keep a small fallback
                if code in (e.KEY_UP,):
                    return 'up'
                if code in (e.KEY_DOWN,):
                    return 'down'
                if code in (e.KEY_LEFT,):
                    return 'left'
                if code in (e.KEY_RIGHT,):
                    return 'right'
                if code in (e.KEY_ENTER,):
                    return 'a'
                if code in (e.KEY_ESC, e.KEY_BACKSPACE):
                    return 'b'

            # D-Pad (hat axes)
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

            # Heuristic: real gamepad usually has face buttons and/or dpad
            has_face = any(btn in keys for btn in (e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST))
            has_dpad = any(btn in keys for btn in (e.BTN_DPAD_UP, e.BTN_DPAD_DOWN, e.BTN_DPAD_LEFT, e.BTN_DPAD_RIGHT))
            has_hat = any(ax in abs_caps for ax in (e.ABS_HAT0X, e.ABS_HAT0Y))

            if has_face or has_dpad or has_hat:
                print(f"Controller found: {dev.name} ({dev.path})", flush=True)
                return dev

        time.sleep(1.0)


def init_controller(preferred_path: Optional[str] = None):
    global controller
    controller = ControllerInput(preferred_path)

def unblank_framebuffer() -> None:
    for p in ("/sys/class/graphics/fb0/blank", "/sys/class/graphics/fb1/blank"):
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("0")
        except Exception:
            pass

def clear_screen():
    unblank_framebuffer()
    print("\033[2J\033[H", end='', flush=True)


def show_menu(
    title: str,
    options: List[str],
    selected: int = 0,
    info: str = "",
    offset: int = 0,
    visible: int = 20,
    show_items: bool = False,
) -> None:
    """Render the menu."""
    clear_screen()
    print("=" * 98)
    print(f" {title}")
    print("=" * 98)

    total = len(options)
    if visible <= 0:
        visible = total

    # Clamp offset
    if offset < 0:
        offset = 0
    if offset > max(0, total - 1):
        offset = max(0, total - 1)

    start = offset
    end = min(offset + visible, total)
    
    if info:
        print(f"\n\n\n{info}\n")

    for i in range(start, end):
        option = options[i]
        if i == selected:
            print(f"  > {option}")
        else:
            print(f"    {option}")

    if end < total:
        print("    ...")

    print("\n" + "-" * 98)
    print("D-Pad: Navigate | A: Select | B: Back | Select: Quit | Left/Right: Page up/down")
    print("-" * 98)
    sys.stdout.flush()

def select_from_list(title: str, items: List[str], info: str = "", visible: int = 20, show_items: bool = False) -> Optional[int]:
    if not items:
        return None

    total = len(items)
    selected = 0
    offset = 0

    # Ensure sensible visible window
    if visible <= 0:
        visible = total

    while True:
        # Keep selected visible
        if selected < offset:
            offset = selected
        elif selected >= offset + visible:
            offset = selected - visible + 1

        # Clamp offset to valid range
        if total > visible:
            max_off = max(0, total - visible)
            if offset > max_off:
                offset = max_off
        else:
            offset = 0

        show_menu(title, items, selected, info, offset=offset, visible=visible)

        key = controller.wait_for_input()

        if key == 'select':
            raise UserQuit()

        elif key == 'up':
            if selected > 0:
                selected -= 1

        elif key == 'down':
            if selected < total - 1:
                selected += 1

        elif key == 'left':
            # Page up
            selected = max(0, selected - visible)

        elif key == 'right':
            # Page down
            selected = min(total - 1, selected + visible)

        elif key == 'a':
            return selected

        elif key == 'b':
            raise GoBack()


def confirm_dialog(title: str, message: str, default_yes: bool = True) -> bool:
    options = ["Yes", "No"]
    selected = 0 if default_yes else 1
    
    while True:
        show_menu(title, options, selected, message)
        
        key = controller.wait_for_input()
        
        if key == 'select':
            raise UserQuit()
        
        elif key in ['up', 'down']:
            selected = 1 - selected
        
        elif key == 'a':
            return selected == 0
        
        elif key == 'b':
            return False


def ok_dialog(title: str, message: str) -> None:
    options = ["OK"]
    selected = 0
    while True:
        show_menu(title, options, selected, message, 0, 20, False)
        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        if key in ['a', 'b', 'start']:
            return


def back_exit_dialog(title: str, message: str) -> str:
    options = ["B A C K", "E X I T"]
    selected = 0
    while True:
        show_menu(title, options, selected, message, 0, 20, False)
        key = controller.wait_for_input()
        if key == 'select':
            raise UserQuit()
        if key in ['up', 'down']:
            selected = 1 - selected
        if key in ['b']:
            return "back"
        if key in ['a', 'start']:
            return "back" if selected == 0 else "exit"


# ---------------------------------------------------------------------------
# Custom Command Line Editor
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Ruffle installer
# ---------------------------------------------------------------------------
PORT_URL   = "https://github.com/worstcase-scenario/qtruffle/releases/download/v1.0/flash-ruffle-emuelec.tar.gz"
PORTDIR    = "/storage/roms/ports/qtwebbrowser"
SCRIPTS    = "/storage/roms/ports_scripts"
ESCFG      = "/storage/.emulationstation/es_systems.cfg"
CACHE      = "/storage/roms/flash-ruffle-emuelec.tar.gz"
RUFFLE_LOG = "/emuelec/logs/ruffle-install.log"

ES_ENTRY = """\t<system>
\t\t<fullname>Adobe Flash Player</fullname>
\t\t<name>flash</name>
\t\t<manufacturer>Macromedia</manufacturer>
\t\t<release>1996</release>
\t\t<hardware>computer</hardware>
\t\t<path>/storage/roms/flash</path>
\t\t<extension>.swf .SWF</extension>
\t\t<command>emuelecRunEmu.sh %ROM% -P%SYSTEM% --core=%CORE% --emulator=%EMULATOR% --controllers="%CONTROLLERSCONFIG%"</command>
\t\t<platform>flash</platform>
\t\t<theme>flash</theme>
\t\t<emulators>
\t\t\t<emulator name="ruffle">
\t\t\t\t<cores>
\t\t\t\t\t<core default="true">ruffle</core>
\t\t\t\t</cores>
\t\t\t</emulator>
\t\t</emulators>
\t</system>
"""

BROWSER_ENTRY = """\t<game>
\t\t<path>./qtwebbrowser.sh</path>
\t\t<name>Qt Web Browser</name>
\t\t<desc>Full web browser (Qt WebEngine / Chromium) by Snowram. Browse with the gamepad: left stick moves the mouse, A clicks, B is Escape, Start is Enter. An on-screen keyboard opens for text input.</desc>
\t\t<image>/storage/roms/ports/qtwebbrowser/cover.jpg</image>
\t</game>
"""

class InstallError(Exception):
    pass


def log(msg: str) -> None:
    print(msg, flush=True)
    try:
        with open(RUFFLE_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def progress(title: str, message: str) -> None:
    clear_screen()
    print("=" * 98)
    print(f" {title}")
    print("=" * 98)
    print(f"\n{message}\n", flush=True)


def download_port() -> None:
    import urllib.request
    if os.path.isfile(CACHE):
        log("Using existing archive: " + CACHE)
        return
    log("Downloading " + PORT_URL)
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
                    bar = ("#" * (pct // 2)).ljust(50)
                    progress("Install Flash (Ruffle)",
                             f"Downloading port archive...\n\n"
                             f"[{bar}] {pct}%\n\n"
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
    progress("Install Flash (Ruffle)", "Checking archive integrity...")
    if subprocess.run(["gzip", "-t", CACHE]).returncode != 0:
        try:
            os.remove(CACHE)
        except OSError:
            pass
        raise InstallError("Archive corrupted - removed, please retry")
    progress("Install Flash (Ruffle)", "Extracting (this takes a minute)...")
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


def finalize_port() -> None:
    if not os.path.isfile(os.path.join(PORTDIR, "qtwebbrowser.aarch64")):
        raise InstallError("qtwebbrowser.aarch64 missing after extraction")
    if not os.path.isfile(os.path.join(PORTDIR, "ruffle", "ruffle.js")):
        raise InstallError("ruffle.js missing after extraction")
    for name in ("Flash-Ruffle.sh", "qtwebbrowser.sh"):
        p = os.path.join(SCRIPTS, name)
        if os.path.isfile(p):
            os.chmod(p, 0o755)
    os.makedirs("/storage/roms/flash", exist_ok=True)


def write_es_entry() -> None:
    progress("Install Flash (Ruffle)", "Writing EmulationStation system entry...")
    os.makedirs(os.path.dirname(ESCFG), exist_ok=True)
    if os.path.isfile(ESCFG):
        content = open(ESCFG, encoding="utf-8").read()
        if '<emulator name="ruffle">' in content:
            log("ES system entry already present")
            return
        shutil.copy2(ESCFG, ESCFG + ".bak." + time.strftime("%Y%m%d%H%M%S"))
    else:
        content = '<?xml version="1.0"?>\n<systemList>\n</systemList>\n'
    if "</systemList>" not in content:
        raise InstallError("no </systemList> in " + ESCFG)
    content = content.replace("</systemList>", ES_ENTRY + "</systemList>")
    with open(ESCFG + ".tmp", "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(ESCFG + ".tmp", ESCFG)


def install_ruffle() -> None:
    if os.path.isfile(os.path.join(PORTDIR, "qtwebbrowser.aarch64")):
        log("Port already installed")
    else:
        download_port()
        extract_port()
    finalize_port()
    write_es_entry()
    ok_dialog("Installation complete",
              "Flash (Ruffle) is installed.\n\n"
              "Put your .swf games into /storage/roms/flash\n"
              "and restart EmulationStation.\n\n"
              "Per-game controls: place a <game>.gptk file\n"
              "next to the .swf. Exit games with Select+Start.")


def add_browser_entry() -> None:
    gl = os.path.join(SCRIPTS, "gamelist.xml")
    if os.path.isfile(gl) and "qtwebbrowser.sh" in open(gl, encoding="utf-8").read():
        ok_dialog("Qt Web Browser", "The browser is already in the Ports list.")
        return
    if not confirm_dialog("Add Qt Web Browser?",
                          "The Flash player is built on a full Qt Web Browser.\n"
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


def main() -> None:
    preferred = sys.argv[1] if len(sys.argv) > 1 else None
    init_controller(preferred)

    try:
        with open(RUFFLE_LOG, "w", encoding="utf-8") as f:
            f.write("EmuELEC Flash (Ruffle) Installer Log\n")
    except Exception:
        pass

    try:
        while True:
            try:
                idx = select_from_list(
                    "Flash (Ruffle) Installer",
                    [
                        "Install / update Flash (Ruffle)",
                        "Add Qt Web Browser to the Ports list",
                        "Exit",
                    ],
                    "What would you like to do?",
                )
                if idx is None or idx == 2:
                    break
                if idx == 0:
                    install_ruffle()
                elif idx == 1:
                    add_browser_entry()
            except GoBack:
                continue
            except InstallError as exc:
                log(f"ERROR: {exc}")
                ok_dialog("Installation FAILED",
                          f"{exc}\n\nCheck {RUFFLE_LOG} for details.")

    except UserQuit:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        clear_screen()


if __name__ == "__main__":
    main()
