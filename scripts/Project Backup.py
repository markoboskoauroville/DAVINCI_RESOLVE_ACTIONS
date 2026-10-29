"""
Project Backup, a DaVinci Resolve Actions script (Marko, 29.10.2026).

    "Export Current Project to a Folder ... collects all the media from the project and the project file itself and
    saves it in a predefined folder ... The project name is the folder name, and inside the folder name is the project
    itself with its name. Then you can make a folder called Sources ... images, videos, and audio."
    "We can call this Action Project Backup."

    <folder>/<Project name>/<Project name>.drp
    <folder>/<Project name>/Sources/Images | Videos | Audio

The app asks first (the folder, kept from the last run; Delete Source Media; Delete Source Project) and passes
--folder PATH [--delete-source-media] [--delete-source-project]. Every file is copied and its size checked before
anything is removed; the source media go to the Trash (recoverable), the project is deleted from Resolve only after its
.drp is on the drive. Without the delete ticks the open project keeps its own files: it is pointed at the copies only
for the export, then back. Image sequences (name.[0001-0100].ext) are left where they are and never deleted.

While it copies, the status line says the file, its size, the speed and the time left for the whole backup.

"this is a project backup and clean up ... clean up every render file, everything what this project was generating from
the system drive" (Marko, 29.10.2026): the renders of its render jobs are copied into <project>/Renders; with Delete
Source Project they, the render cache and optimized media (CacheClip/<project id>), the gallery stills (.gallery/<id>),
the project's own media folder (captures) and the proxies go to the Trash too. A render is a file in a job's folder whose
name is the job's own render name (its words before the clip's name), never a file the project uses as a source.
"""
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from steps import step, say  # noqa: E402

IMAGES = {'jpg', 'jpeg', 'png', 'tif', 'tiff', 'exr', 'dpx', 'bmp', 'gif', 'heic', 'heif', 'webp', 'psd', 'tga', 'dng'}
VIDEOS = {'mov', 'mp4', 'm4v', 'mxf', 'avi', 'mkv', 'mts', 'm2ts', 'r3d', 'braw', 'ari', 'crm', 'webm', 'mpg', 'mpeg',
          'hevc', 'h264', '3gp'}
AUDIO = {'wav', 'aif', 'aiff', 'mp3', 'm4a', 'aac', 'flac', 'ogg', 'bwf', 'caf', 'opus', 'wma'}


def get_resolve():
    try:
        return resolve                                    # noqa: F821  inside Resolve the name exists
    except NameError:
        pass
    api = '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting'
    os.environ.setdefault('RESOLVE_SCRIPT_API', api)
    os.environ.setdefault('RESOLVE_SCRIPT_LIB',
                          '/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so')
    sys.path.append(api + '/Modules')
    import DaVinciResolveScript as dvr                   # noqa: E402
    return dvr.scriptapp('Resolve')


def args():
    a = sys.argv[1:]
    folder = a[a.index('--folder') + 1] if '--folder' in a else None
    return folder, '--delete-source-media' in a, '--delete-source-project' in a


def gb(n):
    return '%.2f GB' % (n / 1e9) if n >= 1e8 else '%.0f MB' % (n / 1e6) if n >= 1e6 else '%.0f kB' % (n / 1e3)


def clock(s):
    s = int(max(0, s))
    return '%d:%02d:%02d' % (s // 3600, s // 60 % 60, s % 60) if s >= 3600 else '%d:%02d' % (s // 60, s % 60)


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or 'Untitled'


def walk(folder):
    for clip in folder.GetClipList() or []:
        yield clip
    for sub in folder.GetSubFolderList() or []:
        yield from walk(sub)


def kind(path, clip_type):
    ext = path.rsplit('.', 1)[-1].lower() if '.' in os.path.basename(path) else ''
    if ext in IMAGES:
        return 'Images'
    if ext in AUDIO:
        return 'Audio'
    if ext in VIDEOS:
        return 'Videos'
    t = (clip_type or '').lower()
    return 'Images' if 'still' in t else 'Audio' if t == 'audio' else 'Videos'


def unique(dest_dir, name, taken):
    """The name in its category folder; a second file of the same name from elsewhere gets " (2)"."""
    stem, ext = os.path.splitext(name)
    n, cand = 1, name
    while os.path.join(dest_dir, cand).lower() in taken:
        n += 1
        cand = '%s (%d)%s' % (stem, n, ext)
    taken.add(os.path.join(dest_dir, cand).lower())
    return os.path.join(dest_dir, cand)


def renders(project, sources):
    """The rendered files of the project's render jobs: in each job's folder, the files named like its output (the
    job's custom words before the clip name), same extension, never a source of the project."""
    out = []
    for job in project.GetRenderJobList() or []:
        folder, first = job.get('TargetDir') or '', (job.get('OutputFilename') or '').split(' and more')[0]
        if not folder or not first or not os.path.isdir(folder):
            continue
        stem, ext = os.path.splitext(first)
        prefix = stem[:stem.rfind(' ') + 1] if ' and more' in (job.get('OutputFilename') or '') and ' ' in stem else stem
        for n in sorted(os.listdir(folder)):
            p = os.path.join(folder, n)
            if (os.path.isfile(p) and n.lower().endswith(ext.lower()) and n.startswith(prefix) and p not in sources
                    and p not in out):
                out.append(p)
    return out


def generated(pm, project, name, files):
    """What the project made beside its media: cache and optimized media, gallery stills, its media folder, proxies."""
    s = project.GetSetting() or {}
    uid = project.GetUniqueId()
    places = [os.path.join(s.get('perfCacheClipsLocation') or '', uid),
              os.path.join(s.get('colorGalleryStillsLocation') or '', uid),
              os.path.join(s.get('projectMediaLocation') or '', name)]
    out = [p for p in places if p.strip('/') and os.path.basename(p) and os.path.isdir(p)]
    for f in files:
        for clip in f['clips']:
            px = clip.GetClipProperty('Proxy Media Path') or ''
            if px and os.path.isfile(px) and px not in out:
                out.append(px)
    return out


def size_of(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(r, n)) for r, _, ns in os.walk(p) for n in ns if os.path.isfile(os.path.join(r, n)))


def trash(paths):
    """To the Trash through Finder (each volume's own), fifty at a time: recoverable."""
    done = 0
    for i in range(0, len(paths), 50):
        part = paths[i:i + 50]
        items = ', '.join('POSIX file "%s"' % p.replace('\\', '\\\\').replace('"', '\\"') for p in part)
        r = subprocess.run(['osascript', '-e', 'tell application "Finder" to delete {%s}' % items],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError('the Trash refused: ' + r.stderr.strip()[-200:])
        done += len(part)
        say('To the Trash: %d of %d' % (done, len(paths)))


def main():
    folder, delete_media, delete_project = args()
    if not folder:
        raise SystemExit('No folder: run Project Backup from DaVinci Resolve Actions, which asks for it')

    step('Read the project')
    resolve = get_resolve()
    if resolve is None:
        raise SystemExit('Resolve does not answer (Preferences > System > General > External scripting = Local)')
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    name = project.GetName()
    pool = project.GetMediaPool()
    target = os.path.join(folder, safe(name))
    files, seqs, seen = [], [], {}
    for clip in walk(pool.GetRootFolder()):
        path = clip.GetClipProperty('File Path') or ''
        if not path:
            continue                                      # titles, generators, compound and fusion clips
        if re.search(r'\[\d+-\d+\]', path):
            seqs.append(path)
            continue
        if not os.path.isfile(path):
            say('Offline, not copied: ' + path)
            continue
        if path in seen:
            seen[path]['clips'].append(clip)
            continue
        seen[path] = {'src': path, 'clips': [clip], 'kind': kind(path, clip.GetClipProperty('Type')),
                      'size': os.path.getsize(path)}
        files.append(seen[path])
    rendered = renders(project, set(seen))
    made = generated(pm, project, name, files)
    total = sum(f['size'] for f in files) + sum(os.path.getsize(r) for r in rendered)
    counts = {k: sum(1 for f in files if f['kind'] == k) for k in ('Images', 'Videos', 'Audio')}
    say('%s: %d files (%d images, %d videos, %d audio), %d renders, %s in all%s' % (
        name, len(files), counts['Images'], counts['Videos'], counts['Audio'], len(rendered), gb(total),
        ', %d image sequences left in place' % len(seqs) if seqs else ''))
    os.makedirs(target, exist_ok=True)
    free = shutil.disk_usage(target).free
    if free < total * 1.02:
        raise SystemExit('Not enough room on %s: %s free, %s needed' % (folder, gb(free), gb(total)))
    for k in counts:
        os.makedirs(os.path.join(target, 'Sources', k), exist_ok=True)

    step('Copy the media and the renders')
    taken, copied, t0, moved_bytes = set(), 0, time.time(), 0
    if rendered:
        os.makedirs(os.path.join(target, 'Renders'), exist_ok=True)
    rjobs = [{'src': r, 'kind': 'Renders', 'size': os.path.getsize(r), 'clips': [], 'render': True} for r in rendered]
    work = files + rjobs
    for i, f in enumerate(work, 1):
        where = os.path.join(target, 'Renders') if f.get('render') else os.path.join(target, 'Sources', f['kind'])
        f['dst'] = unique(where, os.path.basename(f['src']), taken)
        if os.path.abspath(f['src']) == os.path.abspath(f['dst']):
            raise SystemExit('The backup folder is where the media already are: choose another folder')
        if os.path.isfile(f['dst']) and os.path.getsize(f['dst']) == f['size']:
            copied += f['size']                           # already there from an earlier run: kept
            say('%d/%d %s · already in the backup' % (i, len(work), os.path.basename(f['dst'])))
            continue
        last = 0.0
        with open(f['src'], 'rb') as r, open(f['dst'] + '.part', 'wb') as w:
            while True:
                chunk = r.read(8 << 20)
                if not chunk:
                    break
                w.write(chunk)
                copied += len(chunk)
                moved_bytes += len(chunk)
                now = time.time()
                if now - last >= 0.5:
                    last = now
                    rate = moved_bytes / max(now - t0, 0.001)
                    say('%d/%d %s (%s) · %.0f MB/s · %s of %s · %s left' % (
                        i, len(work), os.path.basename(f['src']), gb(f['size']), rate / 1e6,
                        gb(copied), gb(total), clock((total - copied) / max(rate, 1))))
        os.replace(f['dst'] + '.part', f['dst'])
        shutil.copystat(f['src'], f['dst'])
        if os.path.getsize(f['dst']) != f['size']:
            raise SystemExit('Copy of %s came out a different size: stopped, nothing deleted' % f['src'])
    rate = moved_bytes / max(time.time() - t0, 0.001)
    say('Copied and checked: %d files and %d renders, %s in %s (%.0f MB/s)' % (
        len(files), len(rjobs), gb(total), clock(time.time() - t0), rate / 1e6))

    step('Point the project at the copies')
    pointed = 0
    for f in files:
        for clip in f['clips']:
            if clip.ReplaceClip(f['dst']):
                pointed += 1
            else:
                say('Could not point %s at its copy' % os.path.basename(f['src']))
    say('%d clips now use the copies in %s' % (pointed, os.path.join(target, 'Sources')))

    step('Export the project file')
    pm.SaveProject()
    drp = os.path.join(target, safe(name) + '.drp')
    if not pm.ExportProject(name, drp, True) or not os.path.isfile(drp):
        raise SystemExit('Resolve did not export %s: nothing deleted' % drp)
    say('%s (%s), its media in Sources' % (drp, gb(os.path.getsize(drp))))
    if not delete_media:
        # the open project keeps its own files; only the exported one uses the copies
        for f in files:
            for clip in f['clips']:
                clip.ReplaceClip(f['src'])
        pm.SaveProject()

    step('Delete the source media')
    if delete_media:
        trash([f['src'] for f in files])
        say('%d source files are in the Trash (%s); the project uses the copies' % (len(files), gb(total)))
    else:
        say('Kept: Delete Source Media was not ticked')

    step('Delete the source project and what it made')
    if delete_project:
        pm.SaveProject()
        pm.CloseProject(project)
        if not pm.DeleteProject(name):
            raise SystemExit('Resolve did not delete the project %s (it is backed up in %s)' % (name, drp))
        say('The project %s is deleted from Resolve; it is in %s' % (name, target))
        gone = [p for p in rendered + made if os.path.exists(p)]
        freed = sum(size_of(p) for p in gone)
        if gone:
            trash(gone)
        say('Cleaned up: the project, %d render(s) (backed up in Renders), cache, optimized media, gallery stills, '
            'captures and proxies: %d items, %s to the Trash' % (len(rendered), len(gone), gb(freed)))
    else:
        say('Kept: Delete Source Project was not ticked (renders, cache and stills stay)')
    print('Project Backup done: %s' % target)


if __name__ == '__main__':
    main()
