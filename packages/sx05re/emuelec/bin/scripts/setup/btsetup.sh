#!/bin/bash
# Backward-compatible wrapper for the unified Bluetooth audio workflow
exec "$(dirname "$0")/btaudio.sh" --scan "$@"
