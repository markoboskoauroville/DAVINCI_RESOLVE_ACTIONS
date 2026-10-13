#!/usr/bin/env python3
"""
Create Timeline, a DaVinci Resolve script (DaVinci Resolve Assistant, README.md).
Marko, 9.9.2026: "create a new timeline using the selected clips ... named by
the selected clip or the first one of a bunch instead of Timeline 1 ... without
asking me anything. Very simple script."

Workspace > Scripts > Utility > Create Timeline. Give it a shortcut in
DaVinci Resolve > Keyboard Customization (search for the script's name).

Select one or more clips in the Media Pool and run it. A new timeline is made
from them, in the order they sit in the pool, named after the first clip with
its extension taken off ("A001_C002.mov" becomes "A001_C002"). If a timeline
with that name exists already the new one is "A001_C002 2", then "3", and so
on; Resolve wants timeline names unique. The new timeline becomes the current
one, as Resolve does for any new timeline. Nothing is asked, nothing else is
touched. With no clip selected it says so and does nothing.
"""

import os
import sys


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


def clip_name(clip):
    """The clip's name as the pool shows it, without the file extension."""
    name = ''
    try:
        name = clip.GetName() or ''
    except Exception:                                     # noqa: BLE001
        pass
    if not name:
        try:
            name = clip.GetClipProperty('Clip Name') or clip.GetClipProperty('File Name') or ''
        except Exception:                                 # noqa: BLE001
            name = ''
    base, ext = os.path.splitext(name)
    return (base if base and len(ext) <= 5 else name).strip() or 'Timeline'


def unique(project, name):
    taken = set()
    for i in range(1, int(project.GetTimelineCount() or 0) + 1):
        tl = project.GetTimelineByIndex(i)
        if tl:
            taken.add(tl.GetName())
    if name not in taken:
        return name
    n = 2
    while '%s %d' % (name, n) in taken:
        n += 1
    return '%s %d' % (name, n)


def main():
    r = get_resolve()
    if not r:
        print('ERROR Resolve is not running, or external scripting is not set to Local')
        return 2
    project = r.GetProjectManager().GetCurrentProject()
    if not project:
        print('ERROR no project is open')
        return 2
    pool = project.GetMediaPool()
    clips = pool.GetSelectedClips() or []
    if not clips:
        print('no clip is selected in the Media Pool')
        return 1
    name = unique(project, clip_name(clips[0]))
    timeline = pool.CreateTimelineFromClips(name, [{'mediaPoolItem': c} for c in clips])
    if not timeline:
        timeline = pool.CreateTimelineFromClips(name, clips)          # the older call, for an older Resolve
    if not timeline:
        print('ERROR Resolve would not create the timeline "%s"' % name)
        return 1
    print('timeline "%s": %d clip%s' % (timeline.GetName(), len(clips), '' if len(clips) == 1 else 's'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
else:
    main()
