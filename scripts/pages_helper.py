#!/usr/bin/env python3
"""
pages_helper.py, the star's bridge to DaVinci Resolve's pages. Part of the
DaVinci Resolve Assistant (~/Developer/resolve-scripts). Marko, 9.9.2026:
"I need something which is same as Alt+Tab or Command+Tab in the Mac ... It
needs to jump only between spaces which user enabled."

One long-lived process, started by apps/pages.lua while Resolve runs, so a
press of the shortcut never waits for Python and the Resolve API to wake up.
Lines in on stdin, lines out on stdout:

    in   read                  out  page color
    in   open fusion           out  page fusion        (or  error ...)
    in   pages                 out  pages edit,fusion,color,fairlight,deliver
    in   quit                  the process ends

and by itself, every time Resolve's page changes (looked at twice a second:
Resolve's API has no event for it, so this is the one place a poll exists),
a line  page <name>.  While Resolve is up but not answering (a project still
loading, External scripting not set to Local) the helper says  waiting  once
and keeps trying every few seconds; when Resolve is gone it says  gone  and
exits. Every failure is written to ~/.config/resolve-assistant.log with the
time, never to the screen.

WHICH PAGES ARE ENABLED comes from Resolve's own page bar. The API cannot say,
but Resolve writes its choice to ~/Library/Preferences/Blackmagic Design/
DaVinci Resolve/UI.preset, a hex-encoded Qt stream holding one block of
settings per screen resolution; the live block is the one named by
LastUsedResolution. In that block the keys ShowMediaPage, ShowCutPage,
ShowEditPage, ShowFusionPage, ShowColorPage, ShowFairlightPage,
ShowDeliverPage and ShowPhotoPage each carry a one-byte bool.
"""

import os
import re
import select
import signal
import struct
import subprocess
import sys
import time

PAGES = ['media', 'cut', 'edit', 'fusion', 'color', 'fairlight', 'deliver', 'photo']
PREF = os.path.expanduser('~/Library/Preferences/Blackmagic Design/DaVinci Resolve/UI.preset')
LOG = os.path.expanduser('~/.config/resolve-assistant.log')
POLL = 0.5            # seconds between looks at the page
RECONNECT = 4         # seconds between tries while Resolve is not answering
MAX_LOG = 512 * 1024


def say(line):
    sys.stdout.write(line + '\n')
    sys.stdout.flush()


def log(text):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        if os.path.exists(LOG) and os.path.getsize(LOG) > MAX_LOG:
            os.replace(LOG, LOG + '.old')
        with open(LOG, 'a') as fh:
            fh.write('%s pages_helper: %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), text))
    except OSError:
        pass


RESOLVE_BIN = 'DaVinci Resolve.app/Contents/MacOS/Resolve'   # the process is called Resolve, not DaVinci Resolve


def resolve_running():
    """Is Resolve's process there? By its full path: the executable is plainly "Resolve", and
    pgrep -x "DaVinci Resolve" never matched, so the first try after a launch said gone (9.9.2026)."""
    try:
        out = subprocess.run(['pgrep', '-f', RESOLVE_BIN], capture_output=True, text=True, timeout=3)
        return out.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return True                                              # cannot tell: assume it is there


# ---------------------------------------------------------------- the enabled pages
def _u16(text):
    return text.encode('utf-16-be')


def enabled_pages():
    """The pages ticked in Resolve's page bar, in Resolve's order. All of them if the file cannot be read."""
    try:
        with open(PREF, 'rb') as fh:
            raw = fh.read()
        data = bytes.fromhex(raw.split(b'\n', 1)[1].strip().decode('ascii'))
    except (OSError, ValueError, IndexError) as e:
        log('UI.preset unreadable: %s' % e)
        return PAGES[:-1]

    # the live block: the resolution named by LastUsedResolution
    key = _u16('LastUsedResolution')
    i = data.find(key)
    current = None
    if i >= 0:
        j = i + len(key) + 5                                    # QVariant type (4) + isNull (1)
        n = struct.unpack('>I', data[j:j + 4])[0]
        if 0 < n < 64:
            current = data[j + 4:j + 4 + n].decode('utf-16-be', 'replace')

    # every block starts, in effect, at a resolution-shaped key like 2560x1440
    marks = []
    for m in re.finditer(rb'(?:\x00[0-9]){3,5}\x00x(?:\x00[0-9]){3,5}', data):
        marks.append((m.start(), m.group().decode('utf-16-be')))

    def block_of(offset):
        name = None
        for off, res in marks:
            if off < offset:
                name = res
            else:
                break
        return name

    flags = {}
    for page in PAGES:
        k = _u16('Show%sPage' % page.capitalize())
        found = []
        start = 0
        while True:
            i = data.find(k, start)
            if i < 0:
                break
            j = i + len(k)
            if data[j:j + 5] == b'\x00\x00\x00\x01\x00':          # a bool, not null
                found.append((block_of(i), data[j + 5] == 1))
            start = j
        if not found:
            continue
        pick = [v for res, v in found if res == current] or [found[0][1]]
        flags[page] = pick[0]
    if not flags:
        log('UI.preset has no Show*Page keys; every page assumed')
    ring = [p for p in PAGES if flags.get(p, p != 'photo')]
    return ring or PAGES[:-1]


# ---------------------------------------------------------------- Resolve
def get_resolve():
    api = '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting'
    os.environ.setdefault('RESOLVE_SCRIPT_API', api)
    os.environ.setdefault('RESOLVE_SCRIPT_LIB',
                          '/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so')
    if os.path.join(api, 'Modules') not in sys.path:
        sys.path.append(os.path.join(api, 'Modules'))
    try:
        import DaVinciResolveScript as dvr                       # noqa: E402
        return dvr.scriptapp('Resolve')
    except Exception as e:                                       # noqa: BLE001  the module is missing or Resolve refuses
        log('cannot reach Resolve: %s' % e)
        return None


def current_page(r):
    try:
        page = r.GetCurrentPage()
    except Exception as e:                                       # noqa: BLE001
        log('GetCurrentPage failed: %s' % e)
        return None
    return (page or 'none').lower()


_pending = b''


def stdin_line(timeout):
    """One line from the star, or None after timeout; '' when the star closed our stdin."""
    # the app that started us is gone (killed, crashed): our parent is launchd now and stdin may never close,
    # because the child can hold a copy of the pipe's write end; leave as if told to quit (13.10.2026)
    if os.getppid() == 1:
        return ''
    # read from the descriptor into our own buffer: sys.stdin.readline() swallowed every line that arrived with the
    # first one into Python's buffer, where select() no longer saw it, so a second "open" waited for the next press
    # and ⌥` seemed to work only sometimes (22.10.2026)
    global _pending
    if b'\n' not in _pending:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        chunk = os.read(sys.stdin.fileno(), 4096)
        if not chunk:
            return ''
        _pending += chunk
        if b'\n' not in _pending:
            return None
    line, _, _pending = _pending.partition(b'\n')
    return line.decode('utf-8', 'replace') + '\n'


wanted_page = None                                               # an open asked while the API was not answering


def connect():
    """Resolve's API, waiting while Resolve is up but not answering. None when Resolve is gone or we are told to quit."""
    global wanted_page
    said = False
    while True:
        r = get_resolve()
        if r and current_page(r) is not None:
            return r
        if not resolve_running():
            return None
        if not said:
            say('waiting')
            said = True
        line = stdin_line(RECONNECT)
        if line == '' or (line and line.strip() == 'quit'):
            return None
        if line and line.startswith('open '):
            wanted_page = line.split(' ', 1)[1].strip().lower()
            say('error not connected')


def serve(r):
    """The conversation, until Resolve stops answering (True) or the star says quit (False)."""
    say('pages ' + ','.join(enabled_pages()))
    last = current_page(r)
    if last is None:
        return True
    say('page ' + last)
    global wanted_page
    if wanted_page in PAGES and wanted_page != last:
        try:
            r.OpenPage(wanted_page)
        except Exception as e:                                   # noqa: BLE001
            log('OpenPage(%s) failed: %s' % (wanted_page, e))
    wanted_page = None
    tick = time.time()
    while True:
        line = stdin_line(POLL)
        if line is not None:
            if line == '':                                       # the star closed our stdin
                return False
            cmd, _, arg = line.strip().partition(' ')
            if cmd == 'quit':
                return False
            elif cmd == 'read':
                last = current_page(r)
                if last is None:
                    return True
                say('page ' + last)
            elif cmd == 'pages':
                say('pages ' + ','.join(enabled_pages()))
            elif cmd == 'open':
                arg = arg.strip().lower()
                if arg not in PAGES:
                    say('error no page called ' + arg)
                    continue
                try:
                    ok = r.OpenPage(arg)
                except Exception as e:                           # noqa: BLE001
                    log('OpenPage(%s) failed: %s' % (arg, e))
                    ok = False
                if not ok:
                    say('error Resolve would not open ' + arg)
                    continue
                last = current_page(r) or arg
                say('page ' + last)
            elif cmd:
                say('error unknown command ' + cmd)
        if time.time() - tick >= POLL:
            tick = time.time()
            page = current_page(r)
            if page is None:
                return True
            if page != last:
                last = page
                say('page ' + page)


def _signalled(signum, _frame):
    """Killed from outside (Hammerspoon reloading, a terminate): one line in the log, then out."""
    log('terminated (signal %d)' % signum)
    sys.exit(3)


def main():
    signal.signal(signal.SIGTERM, _signalled)
    signal.signal(signal.SIGHUP, _signalled)
    log('start')
    while True:
        r = connect()
        if r is None:
            say('gone')
            log('gone')
            return 2
        try:
            again = serve(r)
        except Exception as e:                                   # noqa: BLE001  never die quietly
            log('serve failed: %r' % (e,))
            again = True
        if not again:
            log('quit')
            return 0
        if not resolve_running():
            say('gone')
            log('gone')
            return 2
        say('waiting')                                           # Resolve is there, the API dropped: back to connect()
        time.sleep(1)


if __name__ == '__main__':
    sys.exit(main())
