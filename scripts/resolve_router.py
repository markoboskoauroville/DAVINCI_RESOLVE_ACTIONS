#!/usr/bin/env python3
"""
resolve_router.py, the one door into DaVinci Resolve's scripting API. Marko, 22.10.2026: "You need to make API access
router for Davinci to resolve this kind of problems. If two apps are reaching resolve at the same time ... coordinate
how you use Davinci resolve and fix that."

Why: every app and every Claude session opened its own connection to Resolve. When Resolve was busy (22.10.2026: its
main thread spinning after clips on the open timeline were overwritten), each call hung forever, the callers piled up
(six stuck pythons), and none of them could tell busy from broken.

What it is: one process, started by DaVinci Resolve Actions (Mantra) and ending with it. It keeps the only connection
in a child worker, runs the calls one at a time (a page switch goes before a session's job), gives each a timeout, and
when Resolve does not answer it kills the worker, says BUSY to everyone at once, and probes until Resolve is back.

HTTP on 127.0.0.1, port claimed as "resolve" in ~/.config/mantra-ports.json (8940 preferred):

    GET  /health                 {"ok": true}
    GET  /status                 state (ready | busy | starting | gone), page, the job running, the queue, the hold
    GET  /page                   the current page, as last seen (no call into Resolve)
    GET  /pages                  the pages ticked in Resolve's page bar (read from UI.preset, no call)
    POST /open?page=edit         switch the page (first in line, 3 s)
    POST /run                    {"who": "elevate", "code": "...", "timeout": 60} or {"who":..., "file": "/x.py",
                                 "args": [...]}: the code runs in the worker with  resolve, project, pm  given and
                                 sets  result ; the answer is {"ok", "result", "out", "error", "seconds"}
    POST /hold                   {"who": "elevate", "minutes": 5}: only that caller's /run jobs go until it lets go or
                                 the minutes pass (page switches still go: they are his hand)
    POST /release                {"who": "elevate"}

Answers: 200 done, 503 Resolve busy (with "since"), 423 held by someone else, 504 the call timed out (the worker was
replaced), 500 the code failed. The command line client is resolve-run (~/.local/bin). The log is
~/.config/resolve-router.log, one line per call: who, what, seconds, outcome.
"""

import io
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.expanduser('~/.local/lib/mantra'))
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.expanduser('~/.config/resolve-router.log')
API = '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting'
LIB = '/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so'
PAGES = ['media', 'cut', 'edit', 'fusion', 'color', 'fairlight', 'deliver', 'photo']
PROBE = 3           # seconds a probe may take before Resolve counts as busy
LOOK = 1.0          # seconds between looks at the page while idle
MAX_LOG = 512 * 1024


def log(text):
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > MAX_LOG:
            os.replace(LOG, LOG + '.old')
        with open(LOG, 'a') as fh:
            fh.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), text))
    except OSError:
        pass


# ---------------------------------------------------------------- the worker: the only connection, one call at a time
def worker():
    """Lines of JSON in, lines of JSON out. Runs in its own process so a call Resolve never answers can be killed."""
    os.environ.setdefault('RESOLVE_SCRIPT_API', API)
    os.environ.setdefault('RESOLVE_SCRIPT_LIB', LIB)
    sys.path.append(os.path.join(API, 'Modules'))
    out = sys.stdout
    sys.stdout = sys.stderr                                      # a job's prints never break the protocol
    import DaVinciResolveScript as dvr                           # noqa: E402
    r = None
    for line in sys.stdin:
        job = json.loads(line)
        t = time.time()
        answer = {'id': job['id']}
        try:
            if r is None:
                r = dvr.scriptapp('Resolve')
                if r is None:
                    raise RuntimeError('Resolve does not answer scriptapp() (External scripting must be Local)')
            kind = job['kind']
            if kind == 'page':
                answer['result'] = (r.GetCurrentPage() or 'none').lower()
            elif kind == 'open':
                answer['result'] = bool(r.OpenPage(job['page']))
            else:
                pm = r.GetProjectManager()
                g = {'__name__': '__main__', 'resolve': r, 'pm': pm,
                     'project': pm.GetCurrentProject() if pm else None, 'result': None}
                buf = io.StringIO()
                old_out, old_argv = sys.stdout, sys.argv
                sys.stdout = buf
                try:
                    if job.get('file'):
                        sys.argv = [job['file']] + [str(a) for a in job.get('args', [])]
                        g['__file__'] = job['file']
                        code = open(job['file']).read()
                    else:
                        code = job['code']
                    try:
                        exec(compile(code, job.get('file') or '<%s>' % job.get('who', 'run'), 'exec'), g)
                    except SystemExit as e:
                        if e.code not in (None, 0):
                            raise RuntimeError('exit %s' % e.code)
                finally:
                    sys.stdout, sys.argv = old_out, old_argv
                answer['out'] = buf.getvalue()[-20000:]
                res = g.get('result')
                try:
                    json.dumps(res)
                except (TypeError, ValueError):
                    res = repr(res)
                answer['result'] = res
            answer['ok'] = True
        except Exception as e:                                   # noqa: BLE001  the job's own failure, told back
            answer['ok'] = False
            answer['error'] = '%s: %s' % (type(e).__name__, e)
            answer['trace'] = traceback.format_exc()[-4000:]
            if 'scriptapp' in str(e):
                r = None
        answer['seconds'] = round(time.time() - t, 3)
        out.write(json.dumps(answer) + '\n')
        out.flush()


# ---------------------------------------------------------------- the router
class Router:
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs = queue.PriorityQueue()                        # (priority, n, job, reply-box)
        self.n = 0
        self.proc = None
        self.state = 'starting'
        self.since = time.time()
        self.page = 'none'
        self.running = None
        self.hold = None                                         # {"who", "until"}
        self.last = []                                           # the last calls, for /status

    # -- the worker process
    def spawn(self):
        self.kill()
        self.proc = subprocess.Popen([sys.executable, '-u', os.path.abspath(__file__), '--worker'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, bufsize=1)

    def kill(self):
        p, self.proc = self.proc, None
        if p and p.poll() is None:
            p.kill()                                             # SIGKILL: a call stuck in Resolve holds Python's lock
            try:
                p.wait(2)
            except subprocess.TimeoutExpired:
                pass

    def call(self, job, timeout):
        """One job into the worker; (answer or None on timeout). Only the dispatcher thread calls this."""
        if self.proc is None or self.proc.poll() is not None:
            self.spawn()
        self.n += 1
        job['id'] = self.n
        box = []
        p = self.proc

        def read():
            try:
                box.append(json.loads(p.stdout.readline()))
            except Exception:                                    # noqa: BLE001
                pass
        try:
            p.stdin.write(json.dumps(job) + '\n')
            p.stdin.flush()
        except OSError:
            self.spawn()
            return None
        t = threading.Thread(target=read, daemon=True)
        t.start()
        t.join(timeout)
        if not box:
            self.kill()
            return None
        return box[0]

    def set_state(self, s):
        if s != self.state:
            log('Resolve %s (was %s for %ds)' % (s, self.state, time.time() - self.since))
            self.state, self.since = s, time.time()

    # -- the one thread that talks to Resolve
    def dispatch(self):
        while True:
            try:
                pri, _, job, box = self.jobs.get(timeout=LOOK)
            except queue.Empty:
                self.look()
                continue
            if self.state != 'ready' and not self.probe():
                box.put((503, {'ok': False, 'busy': True, 'state': self.state, 'since': self.since,
                               'error': 'Resolve is %s (for %ds): try again later' % (self.state, time.time() - self.since)}))
                self.note(job, 'busy', 0)
                continue
            if job['kind'] == 'open' and time.time() - job.get('made', 0) > 1.5:
                box.put((409, {'ok': False, 'error': 'too late: the page was asked 1.5 s ago, its keys went instead'}))
                self.note(job, 'stale', 0)
                continue
            self.running = {'who': job.get('who'), 'kind': job['kind'], 'started': time.time()}
            t = time.time()
            ans = self.call(job, job.get('timeout', 60))
            self.running = None
            if ans is None:
                self.set_state('busy')
                box.put((504, {'ok': False, 'busy': True, 'error': 'Resolve did not answer in %ss; the connection was '
                               'replaced, Resolve counts as busy until a probe answers' % job.get('timeout', 60)}))
                self.note(job, 'timeout', time.time() - t)
                continue
            if job['kind'] == 'open' and ans.get('ok') and ans.get('result'):
                self.page = job['page']
            box.put((200 if ans.get('ok') else 500, ans))
            self.note(job, 'ok' if ans.get('ok') else 'error ' + ans.get('error', ''), ans.get('seconds', 0))

    def probe(self):
        """Does Resolve answer a small call in PROBE seconds?"""
        if not resolve_running():
            self.set_state('gone')
            return False
        ans = self.call({'kind': 'page'}, PROBE + (8 if self.proc is None else 0))
        self._probed = time.time()
        if ans and ans.get('ok'):
            self.page = ans['result']
            self.set_state('ready')
            return True
        self.set_state('busy' if ans is None else 'starting')
        return False

    def look(self):
        """Idle: keep the page fresh, and while busy keep probing (no more often than every 3 s)."""
        if self.state == 'ready':
            ans = self.call({'kind': 'page'}, PROBE)
            if ans is None:
                self.set_state('busy')
            elif ans.get('ok'):
                self.page = ans['result']
        elif time.time() - getattr(self, '_probed', 0) > 3:
            self._probed = time.time()
            self.probe()

    def note(self, job, outcome, seconds):
        what = job['kind'] if job['kind'] != 'run' else 'run ' + (os.path.basename(job.get('file') or '') or 'code')
        if job['kind'] == 'open':
            what += ' ' + job['page']
        log('%s %s %.2fs %s' % (job.get('who', '?'), what, seconds, outcome))
        self.last = ([{'at': time.strftime('%H:%M:%S'), 'who': job.get('who'), 'what': what,
                       'seconds': round(seconds, 2), 'outcome': outcome[:200]}] + self.last)[:20]

    # -- the door
    def submit(self, job, pri):
        if job['kind'] == 'run' and self.hold and self.hold['until'] > time.time() and job.get('who') != self.hold['who']:
            return 423, {'ok': False, 'held': True, 'by': self.hold['who'], 'until': self.hold['until'],
                         'error': 'Resolve is held by %s for %ds more' % (self.hold['who'], self.hold['until'] - time.time())}
        if self.state in ('busy', 'gone') and time.time() - getattr(self, '_probed', 0) < 3:
            return 503, {'ok': False, 'busy': True, 'state': self.state, 'since': self.since,
                         'error': 'Resolve is %s (for %ds): try again later' % (self.state, time.time() - self.since)}
        box = queue.Queue()
        with self.lock:
            self.n += 1
            self.jobs.put((pri, self.n, job, box))
        try:
            return box.get(timeout=job.get('timeout', 60) + 600)
        except queue.Empty:
            return 504, {'ok': False, 'error': 'waited too long in the queue'}

    def status(self):
        h = self.hold if self.hold and self.hold['until'] > time.time() else None
        return {'state': self.state, 'since': self.since, 'page': self.page, 'running': self.running,
                'queued': self.jobs.qsize(), 'hold': h, 'last': self.last, 'pid': os.getpid()}


def resolve_running():
    try:
        return subprocess.run(['pgrep', '-f', 'DaVinci Resolve.app/Contents/MacOS/Resolve'],
                              capture_output=True, timeout=3).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return True


def enabled_pages():
    sys.path.insert(0, HERE)
    try:
        import pages_helper
        return pages_helper.enabled_pages()
    except Exception:                                            # noqa: BLE001
        return PAGES[:-1]


R = Router()


class Door(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        try:
            return json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/health':
            self.send(200, {'ok': True, 'name': 'resolve'})
        elif u.path == '/status':
            self.send(200, R.status())
        elif u.path == '/page':
            self.send(200, {'page': R.page, 'state': R.state})
        elif u.path == '/pages':
            self.send(200, {'pages': enabled_pages()})
        else:
            self.send(404, {'error': 'no such path'})

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[-1] for k, v in parse_qs(u.query).items()}
        b = self.body()
        who = b.get('who') or q.get('who') or 'someone'
        if u.path == '/open':
            page = (b.get('page') or q.get('page') or '').lower()
            if page not in PAGES:
                return self.send(400, {'error': 'no page called ' + page})
            self.send(*R.submit({'kind': 'open', 'page': page, 'who': who, 'timeout': PROBE, 'made': time.time()}, 0))
        elif u.path == '/run':
            if not (b.get('code') or b.get('file')):
                return self.send(400, {'error': 'give "code" or "file"'})
            job = {'kind': 'run', 'who': who, 'code': b.get('code'), 'file': b.get('file'), 'args': b.get('args', []),
                   'timeout': min(float(b.get('timeout', 60)), 1800)}
            self.send(*R.submit(job, 1))
        elif u.path == '/hold':
            if R.hold and R.hold['until'] > time.time() and R.hold['who'] != who:
                return self.send(423, {'ok': False, 'by': R.hold['who'], 'until': R.hold['until']})
            R.hold = {'who': who, 'until': time.time() + 60 * min(float(b.get('minutes', 5)), 60)}
            log('%s holds Resolve until %s' % (who, time.strftime('%H:%M:%S', time.localtime(R.hold['until']))))
            self.send(200, {'ok': True, 'hold': R.hold})
        elif u.path == '/release':
            if R.hold and R.hold['who'] == who:
                R.hold = None
                log('%s let go of Resolve' % who)
            self.send(200, {'ok': True})
        else:
            self.send(404, {'error': 'no such path'})


def main():
    if '--worker' in sys.argv:
        return worker()
    try:
        import ports
        port = ports.claim('resolve', 8940)
    except Exception:                                            # noqa: BLE001  the registry is a convenience
        port = 8940
    srv = ThreadingHTTPServer(('127.0.0.1', port), Door)
    log('router on %d (pid %d)' % (port, os.getpid()))
    print('router %d' % port, flush=True)
    threading.Thread(target=R.dispatch, daemon=True).start()

    def leave(*_):
        R.kill()
        log('router stops')
        os._exit(0)
    signal.signal(signal.SIGTERM, leave)
    signal.signal(signal.SIGHUP, leave)
    owner = os.getppid()

    def watch():                                                 # the app that started us is gone: so are we
        while True:
            time.sleep(1)
            if owner != 1 and os.getppid() != owner:
                leave()
    threading.Thread(target=watch, daemon=True).start()
    srv.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
