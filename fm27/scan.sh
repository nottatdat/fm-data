#!/bin/bash
# Capture FM27 with FMSuperScout's external scanner.
#
# Prerequisite: FM27 is running (Steam/Proton Experimental) with the save loaded,
# and C:\FMSuperScout\FMSuperScout.Scanner.exe exists in the FM27 prefix.
#
# On Linux we run the Windows scanner with the host Proton Wine *outside* the
# pressure-vessel container. It then connects to the same wineserver as the game
# (default prefix socket) and can see fm.exe. Running it via `proton run` starts
# a separate session and fails with "Football Manager is not running".
set -e
PREFIX=/mnt/data/SteamLibrary/steamapps/compatdata/4530370/pfx
PROTON_DIR="/home/dat/.local/share/Steam/steamapps/common/Proton - Experimental"
export WINEPREFIX="$PREFIX"
export WINEDEBUG=-all
export LD_LIBRARY_PATH="$PROTON_DIR/files/lib/x86_64-linux-gnu:$PROTON_DIR/files/lib/i386-linux-gnu:$PROTON_DIR/files/lib"
"$PROTON_DIR/files/bin/wine" 'C:\FMSuperScout\FMSuperScout.Scanner.exe' scan
