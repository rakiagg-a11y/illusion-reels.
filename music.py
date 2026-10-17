"""
Original ambient / cinematic music beds for the reels, synthesised from
scratch with numpy (no samples, no third-party recordings, so no copyright
issues). Each track is exactly the reel length and loops seamlessly.

Structure (one "mood" per track):
  * a low drone on the chord root (detuned saws, low-passed)
  * a slow pad playing a 4-chord minor progression
  * a sub-bass pulse on each beat
  * a plucked arpeggio with a tempo-synced delay
  * a shared reverb; the reverb tail is wrapped around the clip start so the
    loop point is inaudible

  python3 music.py --seed 3 --out bed.wav
"""
import argparse, math, wave
import numpy as np

SR = 44100

SCALES = {  # semitone offsets of natural / harmonic minor
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}
PROGRESSIONS = [  # scale degrees (0-based) of chord roots
    [0, 5, 2, 6], [0, 3, 5, 4], [0, 6, 5, 6], [0, 2, 5, 4],
]


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(f, t, phase=0.0):
    x = (f * t + phase) % 1.0
    return 2 * x - 1


def lowpass(x, cutoff):
    """Simple one-pole low-pass, applied twice (12 dB/oct)."""
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    for _ in range(2):
        acc = 0.0
        # vectorised via lfilter-like recursion in chunks would need scipy;
        # use scipy if present for speed
        try:
            from scipy.signal import lfilter
            y = lfilter([1 - a], [1, -a], x)
            x = y
            continue
        except ImportError:
            pass
        for i in range(len(x)):
            acc = (1 - a) * x[i] + a * acc
            y[i] = acc
        x = y.copy()
    return x


def env_adsr(n, a, d, s, r):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = max(na, 1)
    e[:na] = np.linspace(0, 1, na)
    if nd:
        e[na:na + nd] = np.linspace(1, s, min(nd, max(n - na, 0)))
    if nr and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def reverb(x, rng, seconds=2.6, mix=0.35):
    from scipy.signal import fftconvolve
    n = int(seconds * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.linspace(0, 7, n))
    ir = lowpass(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum())
    wet = np.stack([fftconvolve(x[:, c], ir * (1 + 0.02 * c))[: len(x) + n]
                    for c in range(2)], 1)
    return wet, mix


def make_track(seed, seconds=15.0):
    rng = np.random.default_rng(seed)
    bpm = float(rng.choice([80, 90, 96, 100, 120]))
    beats = round(seconds * bpm / 60)
    bpm = beats * 60 / seconds                      # fit exactly -> clean loop
    beat = 60 / bpm
    n = int(seconds * SR)
    t = np.arange(n) / SR
    scale = SCALES[rng.choice(list(SCALES))]
    root = int(rng.integers(45, 52))                # A2..D#3
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]
    chord_len = n // len(prog)

    def note(deg, octave=0):
        o, d = divmod(deg, 7)
        return root + 12 * (o + octave) + scale[d]

    out = np.zeros((n, 2))

    # drone
    f0 = midi_hz(root - 12)
    drone = sum(saw(f0 * (1 + dt), t, ph) for dt, ph in
                ((0, 0), (0.004, 0.3), (-0.003, 0.7)))
    drone = lowpass(drone, 260 + 120 * np.sin(2 * np.pi * t / seconds).mean())
    out += 0.16 * np.stack([drone, drone], 1)

    # pad
    for i, deg in enumerate(prog):
        s0, s1 = i * chord_len, (i + 1) * chord_len if i < len(prog) - 1 else n
        tt = t[s0:s1] - t[s0]
        pad = np.zeros(s1 - s0)
        for k in (0, 2, 4):
            f = midi_hz(note(deg + k, 1))
            for dt in (-0.006, 0.006):
                pad += saw(f * (1 + dt), tt, rng.random())
        pad = lowpass(pad, 1400) * env_adsr(s1 - s0, 1.0, 0.5, 0.8, 0.9)
        out[s0:s1, 0] += 0.045 * pad
        out[s0:s1, 1] += 0.045 * np.roll(pad, 220)

    # sub-bass pulse on every beat
    for b in range(beats):
        s0 = int(b * beat * SR)
        m = int(0.45 * SR)
        s1 = min(s0 + m, n)
        tt = np.arange(s1 - s0) / SR
        deg = prog[min(int(b * beat * SR) // chord_len, len(prog) - 1)]
        f = midi_hz(note(deg, -1))
        thump = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 7)
        out[s0:s1] += 0.30 * thump[:, None]

    # plucked arpeggio, 8th or 16th notes
    step = beat / float(rng.choice([2, 4]))
    pattern = rng.permutation([0, 2, 4, 7, 4, 2, 9, 7])
    k = 0
    tt_full = np.arange(int(0.6 * SR)) / SR
    pluck_env = np.exp(-tt_full * 9)
    arp = np.zeros(n)
    tpos = 0.0
    while tpos < seconds - 1e-6:
        s0 = int(tpos * SR)
        deg = prog[min(s0 // chord_len, len(prog) - 1)]
        f = midi_hz(note(deg + int(pattern[k % len(pattern)]), 2))
        seg = min(len(tt_full), n - s0)
        tone = (np.sin(2 * np.pi * f * tt_full[:seg]) +
                0.3 * np.sin(4 * np.pi * f * tt_full[:seg]))
        arp[s0:s0 + seg] += tone * pluck_env[:seg]
        k += 1
        tpos += step
    # tempo-synced ping-pong delay (dotted 8th)
    d = int(beat * 0.75 * SR)
    left, right = arp.copy(), np.zeros(n)
    for r in range(1, 5):
        g = 0.45 ** r
        sh = np.roll(arp, d * r) * g
        (right if r % 2 else left)[:] += sh
    out[:, 0] += 0.055 * left
    out[:, 1] += 0.055 * right

    # reverb with the tail wrapped to the start (seamless loop)
    wet, mix = reverb(out, rng)
    tail = wet[n:]
    wet = wet[:n].copy()
    wet[: len(tail)] += tail
    out = out * (1 - mix) + wet * mix

    # gentle master: normalise and soft clip
    out /= np.abs(out).max() + 1e-9
    out = np.tanh(out * 1.3) / np.tanh(1.3)
    out *= 0.85
    return out, {"bpm": round(bpm, 1), "root": root, "seed": seed}


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def track_for(seed, path, seconds=15.0):
    x, meta = make_track(seed, seconds)
    write_wav(path, x)
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="bed.wav")
    ap.add_argument("--seconds", type=float, default=15.0)
    a = ap.parse_args()
    print(track_for(a.seed, a.out, a.seconds))
