#!/bin/sh
# install.sh — put the DaVinci Resolve Assistant's scripts into Resolve, refresh the star mirror, then check.
#
#   ~/Developer/resolve-scripts/install.sh
#
# Copies Toggle HD UHD.py, Previous Page.py and Create Timeline.py into Resolve's Scripts/Utility
# folder (Workspace > Scripts > Utility inside Resolve; Resolve reads the folder
# every time the menu opens, no restart needed). Then, when MANTRA_STAR is on this Mac,
# copies the star's side of the assistant (pages_helper.py, the two badges, the three apps)
# into star/ here, so the repository holds everything. Ends with check.py.

set -e
HERE=$(cd "$(dirname "$0")" && pwd)
UTILITY="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"
STAR="$HOME/Developer/MANTRA_STAR"
PYTHON="$HOME/.pyenv/versions/3.10.14/bin/python3"
[ -x "$PYTHON" ] || PYTHON=python3

mkdir -p "$UTILITY"
for name in "Toggle HD UHD.py" "Previous Page.py" "Create Timeline.py"; do
    cp "$HERE/$name" "$UTILITY/$name"
    echo "installed  $name"
done

if [ -d "$STAR" ]; then
    mkdir -p "$HERE/star"
    for rel in overlay/pages_helper.py overlay/hdbadge.lua overlay/pagebadge.lua apps/display.lua apps/pages.lua apps/importbutton.lua; do
        if [ -f "$STAR/$rel" ]; then
            cp "$STAR/$rel" "$HERE/star/$(basename "$rel")"
            echo "mirrored   star/$(basename "$rel")"
        else
            echo "MISSING    $STAR/$rel" >&2
        fi
    done
fi
echo
exec "$PYTHON" "$HERE/check.py"
