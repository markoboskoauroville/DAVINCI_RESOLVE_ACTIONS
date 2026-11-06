"""
hang_watch.py, the HANG DETECTOR (v21, 6.11.2026). Marko: "build the DaVinci monitor inside this application ... It's
going to just warn you if DaVinci hangs. If it hangs, we need to restart it and start the job again, not stay in one
place" and "When it hangs, it needs to give me the voice, and also show a message on screen that this DaVinci stopped
responding".

Runs as a thread inside resolve_router.py (the one connection to Resolve). Every LOOK seconds it asks Resolve, through
the router's own queue, for the render queue; it never opens a second connection.

Two kinds of hang:
  RENDER   a job is Rendering and neither its percent nor its output file has moved for STALL_ONE (one pass) or
           STALL_TWO (multi-pass: the second pass may sit still for minutes, Marko 6.11.2026) seconds.
  FROZEN   Resolve's process is there but the router cannot get an answer for FROZEN seconds.
Either way: the voice says it once (langsay), and ~/.config/resolve-hang.json says {"state": "hung", ...}; the app
shows "This DaVinci stopped responding" on screen from that file.
A RENDER hang (or a FROZEN one while a render was running) is then restarted by itself: hang_restart.py runs detached,
quits Resolve (kills it when it does not quit), opens it again, loads the project and queues every unfinished job again,
captions burned in whenever the timeline has captions (Marko 6.11.2026: "Subtitles are of uttermost importance"), and
starts them. At most MAX_RESTARTS for the same job; then it only warns. A FROZEN Resolve with no render running is only
warned about: the RESTART DAVINCI button in the message is his.
"""
import json
import os
import subprocess
import sys
import time

STATE = os.path.expanduser('~/.config/resolve-hang.json')
LOOK = 5
STALL_ONE = 180
STALL_TWO = 600
FROZEN = 90
MAX_RESTARTS = 3
HERE = os.path.dirname(os.path.abspath(__file__))

WATCH_CODE = r'''
p = pm.GetCurrentProject()
jobs = []
busy = bool(p and p.IsRenderingInProgress())
if p:
    for j in p.GetRenderJobList():
        s = p.GetRenderJobStatus(j["JobId"]) or {}
        if s.get("JobStatus") in ("Complete",):
            continue
        jobs.append({"id": j["JobId"], "timeline": j.get("TimelineName"), "dir": j.get("TargetDir"),
                     "file": j.get("OutputFilename"), "w": j.get("FormatWidth"), "h": j.get("FormatHeight"),
                     "format": j.get("VideoFormat"), "codec": j.get("VideoCodec"), "profile": j.get("EncodingProfile"),
                     "multipass": j.get("MultiPassEncode"), "status": s.get("JobStatus"), "pct": s.get("CompletionPercentage")})
result = {"project": p.GetName() if p else None, "rendering": busy, "jobs": jobs}
'''


def read_state():
    try:
        return json.load(open(STATE))
    except Exception:                                            # noqa: BLE001
        return {}


def write_state(d):
    d['updated'] = time.time()
    tmp = STATE + '.tmp'
    json.dump(d, open(tmp, 'w'), indent=1)
    os.replace(tmp, STATE)


def say(text):
    """The voice, once, in the background: langsay renders with Speechify before it plays (no-sound-drops)."""
    try:
        subprocess.Popen(['/bin/zsh', '-lc', 'langsay en "%s"' % text.replace('"', '')],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def size(job):
    try:
        return os.path.getsize(os.path.join(job['dir'], job['file']))
    except Exception:                                            # noqa: BLE001
        return -1


def watch(R, log):
    """The thread. R is the router (submit / state); log writes the router log."""
    last = None              # {"id", "pct", "size", "moved", "multipass"}
    snap = None              # the last answer with a render running: what to queue again
    no_answer_since = None
    project = None           # the project last seen open: the RESTART button opens it again
    while True:
        time.sleep(LOOK)
        st = read_state()
        if st.get('state') == 'restarting':
            last, no_answer_since = None, None
            continue
        code, ans = R.submit({'kind': 'run', 'who': 'hang-watch', 'code': WATCH_CODE, 'timeout': 10}, 2)
        now = time.time()
        if code == 423:                                          # held by a session: not ours to judge now
            continue
        if code != 200 or not ans.get('ok'):
            if R.state == 'gone':                                # Resolve is closed: nothing hangs
                no_answer_since, last = None, None
                continue
            no_answer_since = no_answer_since or now
            if now - no_answer_since > FROZEN and st.get('state') != 'hung':
                hung('FROZEN', 'DaVinci Resolve has not answered for %d sec' % (now - no_answer_since), snap, log, project)
            continue
        no_answer_since = None
        res = ans.get('result') or {}
        project = res.get('project') or project
        if st.get('state') == 'hung' and st.get('kind') == 'FROZEN':
            write_state({'state': 'ok', 'note': 'Resolve answers again', 'since': now})
            log('hang-watch: Resolve answers again')
        running = [j for j in res.get('jobs', []) if j.get('status') == 'Rendering']
        if not running:
            last, snap = None, None
            if st.get('state') == 'restarted' and now - st.get('since', now) > 30:
                write_state({'state': 'ok', 'since': now})
            continue
        snap = res
        j = running[0]
        sz = size(j)
        if not last or last['id'] != j['id'] or j.get('pct') != last['pct'] or sz != last['size']:
            last = {'id': j['id'], 'pct': j.get('pct'), 'size': sz, 'moved': now}
            if st.get('state') not in ('ok', None, 'restarted'):
                write_state({'state': 'ok', 'since': now})
            continue
        limit = STALL_TWO if j.get('multipass') else STALL_ONE
        if now - last['moved'] > limit and st.get('state') != 'hung':
            hung('RENDER', '%s stands at %s %% for %d sec' % (j.get('timeline'), j.get('pct'), now - last['moved']), res, log, project)
            last = None


def hung(kind, why, snap, log, project=None):
    st = read_state()
    first = (snap or {}).get('jobs') or []
    key = first[0]['timeline'] if first else ''
    tries = st.get('tries', {})
    n = tries.get(key, 0)
    restart = bool(snap and snap.get('rendering') and first) and n < MAX_RESTARTS
    d = {'state': 'hung', 'kind': kind, 'why': why, 'since': time.time(), 'job': key, 'tries': tries,
         'restart': restart, 'snap': snap, 'project': (snap or {}).get('project') or project}
    write_state(d)
    log('hang-watch: %s HUNG: %s; %s' % (kind, why, 'restarting it (try %d)' % (n + 1) if restart else 'warning only'))
    if restart:
        say('DaVinci stopped responding. I am restarting it and starting the render again.')
        tries[key] = n + 1
        d['tries'] = tries
        write_state(d)
        subprocess.Popen([sys.executable, os.path.join(HERE, 'hang_restart.py')], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    elif snap and first and n >= MAX_RESTARTS:
        say('DaVinci stopped responding again on the same render. I restarted it %d times. Please look at it.' % n)
    else:
        say('DaVinci stopped responding.')
