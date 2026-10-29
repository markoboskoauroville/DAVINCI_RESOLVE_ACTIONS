"""avsync: where a stretch of file B sits in file A, by the rhythm of the sound (onset envelope), not its colour.
measure(A, tA, B, tB, length, search) -> (seconds to add to tB so B lines up with A at tA, strength)"""
import subprocess, numpy as np
from scipy.signal import stft
SR, HOP = 16000, 80                      # 200 envelope values a second: 5 ms resolution
def audio(path, start, dur):
    p = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '%.3f' % max(0, start), '-i', path, '-t', '%.3f' % dur, '-vn',
                        '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, timeout=120)
    return np.frombuffer(p.stdout, np.int16).astype(np.float32) / 32768
def envelope(x):
    _, _, Z = stft(x, SR, nperseg=512, noverlap=512 - HOP)
    m = np.log1p(40 * np.abs(Z))                     # level-independent: the shape of the spectrum
    flux = np.maximum(0, np.diff(m, axis=1)).sum(0)  # where something starts
    flux -= np.convolve(flux, np.ones(40) / 40, 'same')
    return (flux - flux.mean()) / (flux.std() + 1e-9)
def measure(A, tA, B, tB, length=60, search=12):
    a = envelope(audio(A, tA, length))
    b = envelope(audio(B, tB - search, length + 2 * search))
    n = len(a); best = []
    for lag in range(0, len(b) - n):
        best.append(float(np.dot(a, b[lag:lag + n]) / n))
    best = np.array(best); k = int(best.argmax())
    others = np.delete(best, range(max(0, k - 40), k + 40))
    strength = (best[k] - others.mean()) / (others.std() + 1e-9)
    return k / (SR / HOP) - search, float(best[k]), float(strength)
