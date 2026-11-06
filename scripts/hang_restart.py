#!/usr/bin/env python3
"""
hang_restart.py: started (detached) by hang_watch.py when a render hangs. Reads the jobs from ~/.config/resolve-hang.json,
saves and quits DaVinci Resolve (Cmd+S, Cmd+Q through Macro Recorder; ax-quit, SIGTERM, SIGKILL only when it ignores that: MANTRA 31.57), opens it again, loads the same project through the router,
queues every unfinished job again and starts them. The app stays open through it (state "restarting").

Captions (Marko 6.11.2026: "Subtitles are of uttermost importance"): a timeline with clips on a subtitle track is
queued with ExportSubtitle + BurnIn, and the job is not started when Resolve does not take it.
The half-written file of the hung job goes to the Trash first: never overwrite.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hang_watch as hw                                          # noqa: E402

QUALITY = 10000      # kbps; the render job list does not carry the bit rate (Elevate Media: 10 Mbit/s, video-over-internet.md)


def port():
    try:
        return int(json.load(open(os.path.expanduser('~/.config/mantra-ports.json')))['resolve'])
    except Exception:                                            # noqa: BLE001
        return 8940


def run(code, timeout=60):
    req = urllib.request.Request('http://127.0.0.1:%d/run' % port(), method='POST',
                                 data=json.dumps({'who': 'hang-restart', 'code': code, 'timeout': timeout}).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout + 30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:                                        # noqa: BLE001
            return {'ok': False, 'error': str(e)}
    except Exception as e:                                       # noqa: BLE001
        return {'ok': False, 'error': str(e)}


def resolve_up():
    return subprocess.run(['pgrep', '-f', 'DaVinci Resolve.app/Contents/MacOS/Resolve'], capture_output=True).returncode == 0


def save_and_quit(up, wait=60):
    """MANTRA 31.57 (Marko 6.11.2026): Cmd+S, then Cmd+Q, through Macro Recorder; if Resolve ignores it, macro ax-quit,
    then SIGTERM, last SIGKILL. `up` tells whether Resolve still runs. Returns how it went."""
    def gone(sec):
        for _ in range(int(sec / 2)):
            if not up():
                return True
            time.sleep(2)
        return not up()
    subprocess.run(['macro', 'do', 'WinActivate "DaVinci Resolve"\\nSleep 500\\nSend "{Cmd down}s{Cmd up}"\\nSleep 2000\\n'
                    'Send "{Cmd down}q{Cmd up}"'], capture_output=True, timeout=60)
    if gone(wait):
        return 'saved and quit'
    subprocess.run(['macro', 'ax-quit', 'DaVinci Resolve'], capture_output=True, timeout=60)
    if gone(30):
        return 'ax-quit'
    subprocess.run(['pkill', '-TERM', '-x', 'Resolve'])
    if gone(20):
        return 'SIGTERM'
    subprocess.run(['pkill', '-9', '-x', 'Resolve'])
    time.sleep(3)
    return 'SIGKILL'


def main():
    st = hw.read_state()
    snap = st.get('snap') or {}
    jobs, project = snap.get('jobs') or [], snap.get('project') or st.get('project')
    st.update(state='restarting', step='quitting DaVinci Resolve', since=time.time())
    hw.write_state(st)

    how = save_and_quit(resolve_up)
    # the half-written files of the jobs that were running go to the Trash before anything is rendered again
    for j in jobs:
        f = os.path.join(j.get('dir') or '', j.get('file') or '')
        if j.get('status') == 'Rendering' and os.path.isfile(f):
            os.remove(f)                                          # a half-written file is deleted, never kept

    st.update(step='opening DaVinci Resolve (it was %s)' % how)
    hw.write_state(st)
    subprocess.run(['open', '-a', 'DaVinci Resolve'])
    ok = False
    for _ in range(90):                                          # up to 4.5 min for Resolve and its project
        time.sleep(3)
        a = run('p = pm.LoadProject(%r) or pm.GetCurrentProject(); result = p.GetName() if p else None' % project, 60)
        if a.get('ok') and a.get('result') == project:
            ok = True
            break
    if ok and not jobs:                                          # a frozen Resolve with nothing rendering: back, that is all
        st.update(state='restarted', step='DaVinci Resolve is open again with %s' % project, since=time.time())
        hw.write_state(st)
        hw.say('DaVinci is back.')
        return
    if not ok:
        st.update(state='hung', kind='RESTART', why='DaVinci Resolve did not come back with %s' % project, restart=False)
        hw.write_state(st)
        hw.say('I restarted DaVinci, but the project did not open. Please look at it.')
        return

    st.update(step='queuing %d render jobs again' % len(jobs))
    hw.write_state(st)
    code = r'''
import time
project = pm.GetCurrentProject()
resolve.OpenPage("deliver"); time.sleep(1)
want = %s
tls = {project.GetTimelineByIndex(i+1).GetName(): project.GetTimelineByIndex(i+1) for i in range(project.GetTimelineCount())}
for j in project.GetRenderJobList():
    if (project.GetRenderJobStatus(j["JobId"]) or {}).get("JobStatus") != "Complete": project.DeleteRenderJob(j["JobId"])
fmt = {"MP4": "mp4", "QuickTime": "mov", "MOV": "mov"}
cod = {"H.265": "H265", "H.264": "H264"}
new, notes = [], []
for w in want:
    tl = tls.get(w["timeline"])
    if not tl: notes.append("NO TIMELINE " + str(w["timeline"])); continue
    project.SetCurrentTimeline(tl)
    project.SetCurrentRenderMode(1)
    project.SetCurrentRenderFormatAndCodec(fmt.get(w["format"], "mp4"), cod.get(w["codec"], w["codec"] or "H265"))
    caps = any(tl.GetItemListInTrack("subtitle", k) for k in range(1, tl.GetTrackCount("subtitle") + 1))
    s = {"SelectAllFrames": True, "TargetDir": w["dir"], "CustomName": w["file"].rsplit(".", 1)[0],
         "FormatWidth": w["w"], "FormatHeight": w["h"], "ExportVideo": True, "ExportAudio": True,
         "VideoQuality": %d, "MultiPassEncode": bool(w.get("multipass"))}
    if w.get("profile"): s["EncodingProfile"] = w["profile"]
    ok = project.SetRenderSettings(s)
    burn = project.SetRenderSettings({"ExportSubtitle": True, "SubtitleFormat": "BurnIn"}) if caps else True
    if not (ok and burn): notes.append("NOT QUEUED %%s: settings %%s, captions burn-in %%s" %% (w["timeline"], ok, burn)); continue
    new.append(project.AddRenderJob())
    notes.append("queued %%s%%s" %% (w["timeline"], " with captions burned in" if caps else ""))
started = project.StartRendering(new) if new else False
pm.SaveProject()
result = {"jobs": new, "started": bool(started), "notes": notes}
''' % (json.dumps(jobs), QUALITY)
    a = run(code, 120)
    r = a.get('result') or {}
    if a.get('ok') and r.get('started'):
        st.update(state='restarted', step='%d render jobs started again' % len(r['jobs']), notes=r.get('notes'), since=time.time())
        hw.write_state(st)
        hw.say('DaVinci is back. %d renders started again.' % len(r['jobs']))
    else:
        st.update(state='hung', kind='RESTART', why='the jobs did not start again: %s' % (r.get('notes') or a.get('error')),
                  restart=False)
        hw.write_state(st)
        hw.say('I restarted DaVinci, but the renders did not start again. Please look at it.')


if __name__ == '__main__':
    main()
