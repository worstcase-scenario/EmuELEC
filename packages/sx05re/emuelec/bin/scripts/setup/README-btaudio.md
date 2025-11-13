# EmuELEC Bluetooth Audio Quick Guide

These helpers live in `Tools -> Network & Services` inside EmulationStation
and can also be executed from an SSH shell.  They share the same routing
logic through `btaudio-lib.sh`, so EmulationStation and every emulator will
output through the Bluetooth sink as soon as a connection succeeds.

## btsetup.sh — interactive pairing

1. Put the speaker/headset in pairing mode.
2. From EmulationStation open **Main Menu → Network & Services → Bluetooth Audio Setup**
   (or run `btsetup.sh` via SSH).
3. Press **YES** to start a 10‑second scan.  Only audio‑capable devices are
   listed.
4. Choose the device and confirm the dialog.  The script will pair, trust and
   connect it, then switch PulseAudio/ALSA defaults to the device.
5. When the success dialog shows the sink name, audio from EmulationStation
   and all cores is already routed to the Bluetooth output.

The successful MAC is stored in `/storage/.config/btaudio.last` for quick
re-use.

## btconnect.sh — reconnect last device

* Launch **Main Menu → Network & Services → Bluetooth Quick Connect** or run
  `btconnect.sh` via SSH.
* The script recalls the MAC from `/storage/.config/btaudio.last` (or accept a
  MAC on the command line) and forces A2DP mode.
* After the "Active sink" confirmation, EmulationStation is restarted unless
  `--no-restart` is supplied (or `NO_ES_RESTART=1` is exported).

### Command-line usage

```bash
btsetup.sh        # interactive scan/pair route
btconnect.sh      # reconnect previously paired sink
btconnect.sh --no-restart AA:BB:CC:DD:EE:FF
btconnect.sh --help
btsetup.sh  --help
```

Logs: `/tmp/btsetup.log` and `/tmp/btconnect.log`.
