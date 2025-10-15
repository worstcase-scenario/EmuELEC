#!/usr/bin/env python3
import sys
import os
import json
import time
import builtins
from evdev import InputDevice, list_devices, ecodes as e
from evdev import UInput

CONFIG_FILE = "/storage/.config/emuelec/scripts/macro_config.json"

# Ensure console output shows immediately on screen. When called from the
# EmulationStation menu the script runs through a tee pipeline, so we mirror all
# stdout messages to the active framebuffer console to keep them visible on the
# TV while preserving the log.


def setup_console_print():
    original_print = builtins.print
    tty_handle = None

    for path in ("/dev/tty0", "/dev/console"):
        try:
            tty_handle = open(path, "w", buffering=1)
            break
        except OSError:
            continue

    def console_print(*args, **kwargs):
        target = kwargs.get("file", sys.stdout)
        kwargs.pop("flush", None)
        original_print(*args, **kwargs, flush=True)

        if tty_handle and target in (None, sys.stdout):
            mirror_kwargs = dict(kwargs)
            mirror_kwargs["file"] = tty_handle
            try:
                original_print(*args, **mirror_kwargs, flush=True)
            except OSError:
                tty_handle.close()
                tty_handle = None

    return console_print


print = setup_console_print()


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("❌ No saved configuration found. Please run Setup first!")
        sys.exit(1)

    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)

    if "macros" not in data:
        # migrate legacy single-macro format on the fly
        data = {
            "device_path": data.get("device_path"),
            "macros": [
                {
                    "name": "DEFAULT MACRO",
                    "trigger_code": data.get("trigger_code"),
                    "macro_keys": data.get("macro_keys", []),
                }
            ],
        }

    macros = [m for m in data.get("macros", []) if m.get("macro_keys")]
    if not macros:
        print("❌ No macros stored in configuration. Please create one with Setup!")
        sys.exit(1)

    data["macros"] = macros
    return data


def wait_for_controller(preferred_path=None):
    print("\n🔌 Waiting for controller...")

    if preferred_path:
        try:
            dev = InputDevice(preferred_path)
            print(f"🎮 Controller found: {dev.name} ({dev.path})")
            return dev
        except OSError:
            pass

    while True:
        devices = [InputDevice(path) for path in list_devices()]
        for dev in devices:
            if dev.capabilities().get(e.EV_KEY):
                keys = dev.capabilities()[e.EV_KEY]
                if any(btn in keys for btn in [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST]):
                    print(f"🎮 Controller found: {dev.name} ({dev.path})")
                    return dev
        time.sleep(1)


def clear_console():
    print("\033[2J\033[H", end="")


def controller_menu(dev, title, options):
    index = 0

    while True:
        clear_console()
        print(title)
        print("\nUse D-Pad to choose a macro and press (A) to confirm.")
        print("Press (B) to cancel and exit.")
        print()

        for i, option in enumerate(options):
            prefix = "👉" if i == index else "  "
            print(f"{prefix} {option}")

        for event in dev.read_loop():
            if event.type != e.EV_KEY or event.value != 1:
                continue

            if event.code == e.BTN_DPAD_DOWN:
                index = (index + 1) % len(options)
                break
            if event.code == e.BTN_DPAD_UP:
                index = (index - 1) % len(options)
                break
            if event.code == e.BTN_SOUTH:
                return index
            if event.code == e.BTN_EAST:
                print("\n❌ Macro activation cancelled.")
                sys.exit(0)


def run_macro_mode(dev, macro):
    trigger_code = macro["trigger_code"]
    macro_keys = macro["macro_keys"]

    ui = UInput({e.EV_KEY: list(set(macro_keys))}, name="Virtual-Macro", bustype=e.BUS_USB)
    trigger_pressed = False
    macro_executed = False
    press_start = 0

    print("\n🚀 Macro active! Press the trigger to execute. Hold for 3 seconds to exit.")

    for event in dev.read_loop():
        if event.type == e.EV_KEY and event.code == trigger_code:
            if event.value == 1:
                trigger_pressed = True
                macro_executed = False
                press_start = time.time()
            elif event.value == 0:
                if trigger_pressed:
                    hold_time = time.time() - press_start
                    trigger_pressed = False
                    if hold_time >= 3:
                        print("👋 Exiting...")
                        ui.close()
                        return
                    elif not macro_executed:
                        print("▶ Executing macro...")
                        for key in macro_keys:
                            ui.write(e.EV_KEY, key, 1)
                            ui.syn()
                            time.sleep(0.05)
                            ui.write(e.EV_KEY, key, 0)
                            ui.syn()

        if trigger_pressed and not macro_executed and time.time() - press_start >= 0.1:
            macro_executed = True
            print("▶ Executing macro...")
            for key in macro_keys:
                ui.write(e.EV_KEY, key, 1)
                ui.syn()
                time.sleep(0.05)
                ui.write(e.EV_KEY, key, 0)
                ui.syn()


def main():
    config = load_config()
    macros = config["macros"]

    dev = wait_for_controller(config.get("device_path"))

    option_labels = [f"{macro['name']} (Trigger {macro['trigger_code']})" for macro in macros]
    selection = controller_menu(dev, "🎛  Select macro to activate", option_labels)
    chosen_macro = macros[selection]

    run_macro_mode(dev, chosen_macro)


if __name__ == "__main__":
    main()
