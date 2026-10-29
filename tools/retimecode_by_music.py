"""Every clip gets Marko-C0001's time code at the moment it was recorded (sync by music), written into new files."""
import os, subprocess, json
FPS = 25
V = os.path.expanduser('~/Music/SantoshiKoncert/VIDEO'); P = os.path.expanduser('~/Music/SantoshiKoncert/PRINTED_SONGS')
OUT = os.path.expanduser('~/Music/SantoshiKoncert/SYNCHRONIZED BY TIME CODE'); os.makedirs(OUT, exist_ok=True)
M0 = ((21 * 60 + 43) * 60 + 51) * FPS + 19                     # Marko-C0001's first frame: 21:43:51:19
C37 = 26.747
off = {  # Marko file seconds at each clip's frame 0
    'C0036.MP4': C37 - 435, 'C0037.MP4': C37, 'C0038.MP4': 3819.423, 'C0039.MP4': 5133.163,
    'C0040.MP4': 5133.163 + 3827, 'C0041.MP4': 5133.163 + 4222,
    '01 Jai Ganesha Pahi Mam.wav': 397.145, '02 Ambe Jagadambe.wav': 951.148, '03 Kali Kali Maha Maya.wav': 1545.153,
    '04 Sarasvati Maha Lakshmi.wav': 2939.66, '05 Kailasha Vasa Maha deva.wav': 3736.368, '06 Uma Parvati Ananda Ma.wav': 4296.373,
    '07 Rama Rama Jaya Raja Ram.wav': 5265.878, '08 Asatoma Sadgamaya.wav': 6218.883}
def tc(fr):
    fr %= 24 * 3600 * FPS
    return '%02d:%02d:%02d:%02d' % (fr // 90000, fr // 1500 % 60, fr // 25 % 60, fr % 25)
plan = {}
for name, o in off.items():
    fr = M0 + round(o * FPS)
    src = os.path.join(V, 'SVEMIR CAM', name) if name.endswith('.MP4') else os.path.join(P, name)
    dst = os.path.join(OUT, name)
    plan[name] = {'tc': tc(fr), 'marko_seconds': o, 'wraps_midnight': fr >= 24 * 3600 * FPS}
    if name.endswith('.MP4'):
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-map', '0:v:0', '-map', '0:a', '-c', 'copy', '-timecode', tc(fr), dst]
    else:
        sr = int(json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=sample_rate', '-of', 'json', src],
                                           capture_output=True, text=True).stdout)['streams'][0]['sample_rate'])
        samples = (fr % (24 * 3600 * FPS)) * sr // FPS        # BWF time reference: samples since midnight
        plan[name]['time_reference'] = samples
        cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-c', 'copy', '-write_bext', '1', '-metadata', 'time_reference=%d' % samples, dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(name, tc(fr), 'ok' if r.returncode == 0 else 'FAILED ' + r.stderr[-300:], flush=True)
# the master itself: its own time code, the file linked (not copied)
dst = os.path.join(OUT, 'Marko-C0001.MP4')
if not os.path.exists(dst): os.symlink(os.path.join(V, 'marko cam', 'Marko-C0001.MP4'), dst)
plan['Marko-C0001.MP4'] = {'tc': tc(M0), 'master': True}
json.dump(plan, open(os.path.join(OUT, 'time codes.json'), 'w'), indent=1, ensure_ascii=False)
print('done', flush=True)
