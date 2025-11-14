# EmuELEC Bluetooth Audio Quick Guide

All Bluetooth audio helpers now share a single workflow: `btaudio.sh`.  It
scans for A2DP-capable devices, pairs/trusts them, connects, then forces
EmulationStation and every emulator (RetroArch plus stand-alone cores) through
the PulseAudio sink exposed by the Bluetooth headset/speaker.

## btaudio.sh — one-stop pairing and reconnects

1. Put the speaker/headset in pairing mode.
2. From EmulationStation open **Main Menu → Network & Services → Bluetooth Audio
   Setup** (or run `btaudio.sh` via SSH).
3. The script scans for 10 seconds and lists only audio-capable devices.
4. Choose the device to automatically pair, trust, connect, switch the default
   audio sink and toggle EmuELEC’s global audio mode to PulseAudio so every
   client (EmulationStation, RetroArch and stand-alone emulators) immediately
   talks to the Bluetooth sink without manual configuration changes.
5. The successful MAC is stored in `/storage/.config/btaudio.last` for quick
   re-use.

Additional modes:

* `btaudio.sh --last --restart` – reconnects the last saved device (the same
  behaviour exposed by the "Bluetooth Quick Connect" entry).  The EmulationStation
  restart can be suppressed with `--no-restart`.
* `btaudio.sh AA:BB:CC:DD:EE:FF` – skips scanning and connects straight to the
  supplied MAC (automatically routing audio once the sink is detected).

## Backward-compatible launchers

* `btsetup.sh` now simply execs `btaudio.sh --scan` so existing EmulationStation
  menu entries keep launching the interactive workflow.
* `btconnect.sh` execs `btaudio.sh --last --restart` to preserve the quick
  reconnect flow and its default EmulationStation restart.

Logs: `/tmp/btaudio.log`.
