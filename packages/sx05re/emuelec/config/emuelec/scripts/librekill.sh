#!/bin/sh

# Function to force kill Librespot
kill_librespot() {
    # Find and force kill all related processes
    pkill -9 -f "/storage/roms/ports/librespot/librespot"
}

# Run the kill function
kill_librespot



# #!/bin/bash

# echo "Shutdown erkannt, beende Librespot..."

# # Suche alle PIDs von librespot
# PIDS=$(pgrep -f "/storage/roms/ports/librespot/librespot")

# if [ -n "$PIDS" ]; then
    # echo "Librespot läuft mit PIDs: $PIDS"
    
    # # Beende alle gefundenen Prozesse
    # for PID in $PIDS; do
        # echo "Beende Prozess $PID..."
        # kill -TERM "$PID"
    # done

    # # Warte kurz, um das Beenden zu ermöglichen
    # sleep 2  

    # # Prüfe, ob noch Prozesse laufen
    # for PID in $PIDS; do
        # if kill -0 "$PID" 2>/dev/null; then
            # echo "Prozess $PID reagiert nicht, erzwinge Beenden..."
            # kill -KILL "$PID"
        # fi
    # done

    # echo "Librespot wurde beendet."
# else
    # echo "Librespot läuft nicht."
# fi

# echo "Shutdown wird fortgesetzt."
