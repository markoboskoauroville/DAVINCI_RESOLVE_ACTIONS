"""steps.py: an action's steps under the control of DaVinci Resolve Actions (Mantra). Marko, 28.10.2026: "Every action
should have a play button, a next button (in this case, a "Next Step" button), a stop button, and a restart button. When
I start an action, I still have control over how I run it" and "there should be a status line for each step, the title of
the step, and I can press Next. If I press Play, I see what's going on."

A script marks where each step begins and says what it is doing:

    from steps import step, say
    step("Colour management")
    say("DaVinci WG / Intermediate in, Rec.709 Gamma 2.4 out")

The app writes ~/.config/resolve-actions-control.json:  {"run": "<id>", "mode": "play" | "step", "allow": N, "stop": false}
    play     every step goes on by itself
    step     step N+1 begins only once "allow" is above N (each NEXT STEP raises it by one)
    stop     the run ends at the next step() or say(), cleanly
and reads ~/.config/resolve-actions-status.json, written here at every change:
    {"run", "state": running | waiting | stopped, "at": index of the current step, "steps": [{"title", "state", "line"}]}
The app itself writes "done" or "failed" when the script ends.

Run without the app (Resolve's own Workspace > Scripts menu, a terminal) there is no control for this run, and step()
and say() only print.
"""
import json
import os
import time

CONTROL = os.path.expanduser('~/.config/resolve-actions-control.json')
STATUS = os.path.expanduser('~/.config/resolve-actions-status.json')
_run = {'id': None, 'steps': []}


def _control():
    try:
        with open(CONTROL) as f:
            c = json.load(f)
        return c if c.get('run') and c.get('active') else None
    except (OSError, ValueError):
        return None


def _write(state):
    s = {'run': _run['id'], 'state': state, 'at': len(_run['steps']) - 1, 'steps': _run['steps'], 't': time.time()}
    tmp = STATUS + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(s, f)
    os.replace(tmp, STATUS)


def _stop_if_asked(c):
    if c and c.get('stop'):
        if _run['steps']:
            _run['steps'][-1]['state'] = 'stopped'
        _write('stopped')
        raise SystemExit(0)


def step(title):
    """The next step begins: in step mode it waits here until NEXT STEP allows it."""
    print('STEP %d: %s' % (len(_run['steps']) + 1, title), flush=True)
    c = _control()
    if c is None:
        return
    if c['run'] != _run['id']:                                   # a new run: the worker process outlives runs
        _run['id'], _run['steps'] = c['run'], []
    if _run['steps']:
        _run['steps'][-1]['state'] = 'done'
    _run['steps'].append({'title': title, 'state': 'waiting', 'line': ''})
    n = len(_run['steps'])
    while True:
        c = _control()
        _stop_if_asked(c)
        if c is None or c.get('mode') == 'play' or int(c.get('allow', 0)) >= n:
            break
        _write('waiting')
        time.sleep(0.2)
    _run['steps'][-1]['state'] = 'running'
    _write('running')


def say(*text):
    """What the step is doing now: printed, and the step's status line in the app."""
    line = ' '.join(str(t) for t in text)
    print(line, flush=True)
    c = _control()
    if c is None or c['run'] != _run['id'] or not _run['steps']:
        return
    _stop_if_asked(c)
    _run['steps'][-1]['line'] = line
    _write('running')
