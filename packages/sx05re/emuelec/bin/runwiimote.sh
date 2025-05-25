#!/bin/sh
""":"
# Shell part
/usr/bin/systemctl stop eventlircd
exec python3 "$0" "$@"
"""
# Python code starts here

import os
import sysconfig
import evdev
import uinput

# Automatically detect screen resolution
SCREEN_WIDTH = int(os.popen("xrandr | grep '*' | awk '{print $1}' | cut -d 'x' -f1").read().strip())
SCREEN_HEIGHT = int(os.popen("xrandr | grep '*' | awk '{print $1}' | cut -d 'x' -f2").read().strip())

# Maximum IR coordinates
MAX_IR_X = 1023
MAX_IR_Y = 767
IR_DEVICE_NAME = "Nintendo Wii Remote IR"

# Ensure sysconfig recognizes the .so extension
if sysconfig.get_config_var("SO") is None:
    import sys
    sysconfig._CONFIG_VARS["SO"] = ".so"

# Function to normalize coordinates
def normalize(val, max_val, screen_size):
    return int((val / max_val) * screen_size)

# Find IR device
def find_ir_device():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for dev in devices:
        if IR_DEVICE_NAME in dev.name:
            print(f"✔ Found IR device: {dev.name} ({dev.path})")
            return dev
    raise RuntimeError("❌ Wiimote IR device not found")

# Main function
def main():
    ir_dev = find_ir_device()

    ui = uinput.Device([
        uinput.ABS_X + (0, SCREEN_WIDTH, 0, 0),
        uinput.ABS_Y + (0, SCREEN_HEIGHT, 0, 0),
        uinput.BTN_LEFT
    ], name="Wiimote IR")  # Set device name

    x = SCREEN_WIDTH // 2
    y = SCREEN_HEIGHT // 2

    for event in ir_dev.read_loop():
        if event.type == evdev.ecodes.EV_ABS:
            if event.code == evdev.ecodes.ABS_HAT0X:
                x = SCREEN_WIDTH - normalize(event.value, MAX_IR_X, SCREEN_WIDTH)
            elif event.code == evdev.ecodes.ABS_HAT0Y:
                y = normalize(event.value, MAX_IR_Y, SCREEN_HEIGHT)

            ui.emit(uinput.ABS_X, x, syn=False)
            ui.emit(uinput.ABS_Y, y)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exit.")
