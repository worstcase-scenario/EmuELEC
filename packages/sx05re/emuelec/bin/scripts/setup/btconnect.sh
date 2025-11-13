#!/bin/bash
# Backward-compatible wrapper for quick Bluetooth reconnects
exec "$(dirname "$0")/btaudio.sh" --last --restart "$@"
