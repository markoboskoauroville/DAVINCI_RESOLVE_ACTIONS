#!/usr/bin/env python3
"""
Previous Page, a DaVinci Resolve script (DaVinci Resolve Assistant, README.md). Marko, 9.9.2026: "something which is
same as Alt+Tab or Command+Tab ... It needs to jump only between spaces which
user enabled ... remember last two tabs, so it switches back and forth."

Workspace > Scripts > Utility > Previous Page. Give it a shortcut in
DaVinci Resolve > Keyboard Customization (search for the script's name).

This is the same jump as the star's Pages app makes on Option+`, from inside
Resolve and without external scripting: back to the page used before this
one, among every page unless the star's submenu narrowed the ring. Run it
twice and you are where you started. It reads and writes the same file as the
star, ~/.config/pages.json: the last-used order (mru) and, if the star's
submenu chose its own ring, that choice (ring). Without the star the file is
still kept, so the back-and-forth works alone.
"""

import json
import os
import sys

ORDER = ['media', 'cut', 'edit', 'fusion', 'color', 'fairlight', 'deliver', 'photo']
STATE = os.path.expanduser('~/.config/pages.json')


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


def load():
    try:
        with open(STATE) as fh:
            s = json.load(fh)
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def save(s):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(STATE, 'w') as fh:
            json.dump(s, fh)
    except OSError:
        pass


def main():
    r = get_resolve()
    if not r:
        print('ERROR Resolve is not running, or external scripting is not set to Local')
        return 2
    current = (r.GetCurrentPage() or 'none').lower()
    s = load()
    ring = s.get('ring') or ORDER                     # every page, unless the star's submenu narrowed it
    ring = [p for p in ORDER if p in ring]
    mru = [p for p in s.get('mru', []) if p in ORDER]
    target = next((p for p in mru if p != current and p in ring), None)
    if target is None:
        others = [p for p in ring if p != current]
        if not others:
            print('only one page in the ring')
            return 1
        after = [p for p in others if ORDER.index(p) > ORDER.index(current)] if current in ORDER else []
        target = (after or others)[0]
    if not r.OpenPage(target):
        print('ERROR Resolve would not open %s' % target)
        return 1
    for p in (current, target):
        if p in mru:
            mru.remove(p)
        if p != 'none':
            mru.insert(0, p)
    s['mru'], s['current'] = mru[:len(ORDER)], target
    save(s)
    print('%s -> %s' % (current, target))
    return 0


if __name__ == '__main__':
    sys.exit(main())
else:
    main()
