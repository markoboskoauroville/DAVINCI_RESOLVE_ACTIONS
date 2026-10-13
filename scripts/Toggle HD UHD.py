#!/usr/bin/env python3
"""
Toggle HD UHD, a DaVinci Resolve script (DaVinci Resolve Assistant, README.md). Marko, 8.9.2026: "I need in the menu
somewhere an option, and a shortcut, to change my current project resolution,
either HD 1080p or UHD, without going into the settings every time."
"Everything is happening inside DaVinci."

Workspace > Scripts > Utility > Toggle HD UHD. Give it a shortcut in
DaVinci Resolve > Keyboard Customization (search for the script's name).

What it does: reads the project's timeline resolution; 3840 wide becomes
1920 x 1080, anything else becomes 3840 x 2160. The current timeline is set
the same way when it keeps its own settings instead of the project's. Nothing
else in the project is touched. The word beside the star (the star's UHD HD
Display app) is repainted and the mode kept in ~/.config/hdbadge.json.
"""

import os
import sys

HD = ('1920', '1080', 'HD')
UHD = ('3840', '2160', 'UHD')


def get_resolve():
    try:
        return resolve                                    # noqa: F821  inside Resolve the name exists
    except NameError:
        pass
    api = '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting'
    os.environ.setdefault('RESOLVE_SCRIPT_API', api)
    os.environ.setdefault('RESOLVE_SCRIPT_LIB',
                          '/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so')
    sys.path.append(os.path.join(api, 'Modules'))
    import DaVinciResolveScript as dvr                   # noqa: E402
    return dvr.scriptapp('Resolve')


STATE = os.path.expanduser('~/.config/hdbadge.json')


def remember(mode):
    """The last known mode, for the star's UHD HD Display when it cannot ask Resolve.
    Only the mode is touched: the file also holds the star's own keys (enabled,
    hotkey), and rewriting it whole once switched the display app off (9.9.2026)."""
    import json
    state = {}
    try:
        with open(STATE) as fh:
            state = json.load(fh)
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        pass
    state['mode'] = mode
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, 'w') as fh:
            json.dump(state, fh)
    except OSError:
        pass


def paint_badge(r, mode):
    """The word in the menu bar (the star's UHD HD Display) shows the new mode."""
    import subprocess
    remember(mode)
    lua = os.path.expanduser('~/Developer/MANTRA_STAR/overlay/hdbadge.lua')
    try:
        subprocess.run(['/opt/homebrew/bin/hs', '-c', 'return dofile(%r).set(%r)' % (lua, mode)],
                       capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        pass


def main():
    r = get_resolve()
    if not r:
        print('ERROR Resolve is not running, or external scripting is not set to Local')
        return 2
    project = r.GetProjectManager().GetCurrentProject()
    if not project:
        print('ERROR no project is open')
        return 2
    width = str(project.GetSetting('timelineResolutionWidth') or '')
    if '--read' in sys.argv:                              # the star's UHD HD Display asking, once: say it, change nothing
        mode = 'UHD' if width == UHD[0] else 'HD' if width == HD[0] else '?'
        remember(mode)
        print(mode)
        return 0
    w, h, label = HD if width == UHD[0] else UHD
    ok = project.SetSetting('timelineResolutionWidth', w) and project.SetSetting('timelineResolutionHeight', h)
    tl = project.GetCurrentTimeline()
    tl_note = ''
    if tl and str(tl.GetSetting('useCustomSettings')) == '1':
        tl.SetSetting('timelineResolutionWidth', w)
        tl.SetSetting('timelineResolutionHeight', h)
        tl_note = ' (and the timeline %s, which keeps its own settings)' % tl.GetName()
    if not ok:
        print('ERROR Resolve refused the change; is a render or a playback running?')
        return 1
    paint_badge(r, label)
    print('%s: %s x %s%s' % (label, w, h, tl_note))
    return 0


if __name__ == '__main__':
    sys.exit(main())
else:
    main()
