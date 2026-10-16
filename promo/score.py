"""Synthesise the score for the 幕間休息 promo film 「幕間新聞片」 (a cinema newsreel).

Everything is generated here — no samples, no third-party recordings: an intermission
piano waltz, then the newsreel: snare and timpani rolls, a brass fanfare on the title,
a march under each section (film in B♭, photography in C, art in D, rising), soft
flash-bulb pops, a stamp, a final cadence on 「完」, a music-box clock and a closing
chord. The master is band-limited like an old optical soundtrack. Cue times are the
film's timeline seconds (src/promo.html).

  python promo/score.py promo/score.wav        (needs numpy and scipy)
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
LENGTH = 46.0
N = int(SR * LENGTH)
rng = np.random.default_rng(1016)


def hz(note: str) -> float:
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    pitch, rest = names[note[0]], note[1:]
    if rest.startswith("#"):
        pitch, rest = pitch + 1, rest[1:]
    elif rest.startswith("b"):
        pitch, rest = pitch - 1, rest[1:]
    return 440.0 * 2 ** ((pitch + 12 * (int(rest) + 1) - 69) / 12)


def at(t: float) -> int:
    return max(0, min(N, int(round(t * SR))))


def place(bus: np.ndarray, start: float, sound: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
    i = at(start)
    n = min(len(sound), N - i)
    if n <= 0:
        return
    bus[0, i:i + n] += sound[:n] * gain * np.cos((pan + 1) * np.pi / 4)
    bus[1, i:i + n] += sound[:n] * gain * np.sin((pan + 1) * np.pi / 4)


def butter(x: np.ndarray, cutoff, kind: str = "low", order: int = 2) -> np.ndarray:
    return signal.sosfilt(signal.butter(order, cutoff, btype=kind, fs=SR, output="sos"), x, axis=-1)


def envelope(times: list, levels: list, length: int = N) -> np.ndarray:
    return np.interp(np.arange(length) / SR, times, levels)


def fade(x: np.ndarray, attack: float = .005, release: float = .05) -> np.ndarray:
    n = len(x)
    t = np.arange(n) / SR
    return x * np.minimum(1, t / max(attack, 1e-4)) * np.minimum(1, (n / SR - t) / max(release, 1e-4))


# ── Instruments ────────────────────────────────────────────────────────────────
def brass(freq: float, length: float, level: float = 1.0) -> np.ndarray:
    """Additive brass: upper harmonics bloom with loudness, a small pitch scoop on the
    attack and a late vibrato."""
    n = int(length * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / .035) * (0.78 + 0.22 * np.exp(-t / .12))
    env *= np.clip((length - t) / .08, 0, 1)
    scoop = 1 - 0.018 * np.exp(-t / .03)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.4 * t) * np.minimum(1, np.maximum(0, t - .25) / .3)
    phase = 2 * np.pi * np.cumsum(freq * scoop * vib) / SR
    out = np.zeros(n)
    for k in range(1, 14):
        if k * freq > 9000:
            break
        out += (1 / k) * env ** (1 + 0.45 * (k - 1)) * np.sin(k * phase)
    return out * level * 0.22


def chord(notes: list, length: float, level: float = 1.0, spread: float = .006) -> np.ndarray:
    n = int(length * SR)
    parts = [np.pad(brass(hz(note), length, level), (int(i * spread * SR), 0))[:n] for i, note in enumerate(notes)]
    return sum(parts) / np.sqrt(len(notes))


def tuba(freq: float, length: float = .32) -> np.ndarray:
    return butter(brass(freq, length, 1.0), 700) * 1.6


def piano(freq: float, velocity: float = .6, length: float = 3.0) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    decay0 = 2.6 * (220 / freq) ** 0.35
    for k in range(1, 9):
        f = k * freq * np.sqrt(1 + 0.00035 * k * k)
        if f > SR / 2.2:
            break
        out += (1 / k ** 1.5) * velocity ** (0.6 * (k - 1)) * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / (decay0 / (1 + .35 * (k - 1))))
    return fade(out, .004, .3) * velocity * .35


def celesta(freq: float, length: float = 1.4) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * freq * t) * np.exp(-t / .5) + .35 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t / .12)
    return fade(out, .003, .2) * .2


def snare(level: float = 1.0) -> np.ndarray:
    n = int(.25 * SR)
    t = np.arange(n) / SR
    noise = butter(rng.normal(0, 1, n), [1500, 8500], "band") * np.exp(-t / .07)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / .03) * .6
    return fade(noise + tone, .0015, .03) * level * .5


def timpani(freq: float, level: float = 1.0, length: float = 1.8) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    f = freq * (1 + .03 * np.exp(-t / .05))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .55) + .3 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.exp(-t / .3)
    thud = butter(rng.normal(0, 1, n), 300) * np.exp(-t / .03) * .6
    return fade(body + thud, .002, .2) * level * .7


def cymbal(length: float = 2.6, level: float = 1.0) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    x = butter(rng.normal(0, 1, n), [3500, 12000], "band") * np.exp(-t / .9)
    return fade(x, .002, .3) * level * .35


def roll(bus, start: float, end: float, maker, rate: float, levels=(.15, 1.0), pan: float = 0.0) -> None:
    times = np.arange(start, end, 1 / rate)
    for i, t0 in enumerate(times):
        k = i / max(1, len(times) - 1)
        level = (levels[0] + (levels[1] - levels[0]) * k) * (0.85 + 0.3 * rng.random())
        place(bus, t0 + rng.normal(0, .003), maker(level), pan=pan + rng.normal(0, .05))


def whoosh(length: float, rising: bool = True) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    lo, hi = butter(x, 600), butter(x, [1200, 6000], "band")
    k = t / length if rising else 1 - t / length
    env = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 1.5
    return (lo * (1 - k) + hi * k) * env * .5


def pop() -> np.ndarray:
    """A flash bulb: a soft low pop and a short bright sizzle, no sharp click."""
    n = int(.8 * SR)
    t = np.arange(n) / SR
    low = np.sin(2 * np.pi * 90 * t) * np.exp(-t / .06)
    fizz = butter(rng.normal(0, 1, n), [2500, 7000], "band") * np.exp(-t / .18) * .35
    return fade(low + fizz, .004, .1) * .6


# ── Score ──────────────────────────────────────────────────────────────────────
TRIADS = {"Bb": ["Bb", "D", "F"], "C": ["C", "E", "G"], "D": ["D", "F#", "A"], "Eb": ["Eb", "G", "Bb"],
          "F": ["F", "A", "C"], "G": ["G", "B", "D"], "A": ["A", "C#", "E"]}
CADENCE = {"Bb": ("Bb", "Eb", "F"), "C": ("C", "F", "G"), "D": ("D", "G", "A")}


def voicing(root: str, octave: int = 4) -> list:
    return [tone + str(octave) for tone in TRIADS[root]]


def march(bus, start: float, end: float, key: str, intensity: float = 1.0) -> None:
    """Newsreel march at 120 bpm: I – IV – V – I in two-second bars; tuba on 1 and 3,
    snare on 2 and 4, brass chords on the off-beats."""
    bars = [CADENCE[key][0], CADENCE[key][1], CADENCE[key][2], CADENCE[key][0]]
    beat, t, b = .5, start, 0
    while t < end - .05:
        root = bars[(b // 4) % 4]
        tones = TRIADS[root]
        if b % 2 == 0:
            place(bus, t, tuba(hz((tones[0] if b % 4 == 0 else tones[2]) + "2")), gain=.85 * intensity, pan=-.1)
        else:
            place(bus, t, snare(.7), gain=.7 * intensity, pan=.15)
        place(bus, t + beat / 2, chord(voicing(root, 4), .16, .7), gain=.55 * intensity, pan=.2)
        if intensity > 1.05:
            place(bus, t + beat / 2, snare(.35), gain=.4, pan=.15)
        t += beat
        b += 1


def music() -> np.ndarray:
    bus = np.zeros((2, N))

    # 0 · Intermission: a quiet piano waltz in B♭ (3/4) while the slide is up.
    waltz = [("Bb2", "D4", "F4"), ("F2", "C4", "Eb4"), ("Bb2", "D4", "F4"), ("Eb2", "Eb4", "G4")]
    for bar, (bass, a, b) in enumerate(waltz):
        t0 = .35 + bar * .9
        place(bus, t0, piano(hz(bass), .5, 2.0), pan=-.2)
        for off, vel in ((.3, .4), (.6, .35)):
            place(bus, t0 + off, piano(hz(a), vel, 1.5), pan=.1)
            place(bus, t0 + off, piano(hz(b), vel, 1.5), pan=.2)
    bus *= envelope([0, 3.2, 4.1, 46], [.5, .5, 0, 0])

    # 1 · Opening titles: drum roll → fanfare on the title slam.
    roll(bus, 4.2, 5.55, snare, 22, (.08, .9), .1)
    roll(bus, 4.6, 5.55, lambda v: timpani(hz("F2"), v, .5), 12, (.1, .7), -.2)
    place(bus, 5.6, cymbal(3.2, 1.0))
    place(bus, 5.6, timpani(hz("Bb1"), 1.0, 2.0))
    fanfare = [(5.6, ["Bb3", "D4", "F4", "Bb4"], .55), (6.15, ["Bb3", "D4", "F4", "Bb4"], .18), (6.35, ["Bb3", "D4", "F4", "Bb4"], .18),
               (6.55, ["C4", "Eb4", "F4", "A4"], .4), (7.0, ["D4", "F4", "Bb4", "D5"], .9), (7.95, ["Eb4", "G4", "Bb4", "Eb5"], .45),
               (8.45, ["F4", "A4", "C5", "F5"], .45), (8.95, ["D4", "F4", "Bb4", "D5"], .55)]
    for t0, notes, length in fanfare:
        place(bus, t0, chord(notes, length, 1.0), gain=.9)
        place(bus, t0, tuba(hz(notes[0][:-1] + "2"), min(length, .5)), gain=.5)
    roll(bus, 8.95, 9.5, lambda v: timpani(hz("Bb1"), v, .4), 14, (.4, .9))

    # Section hits and marches: 電影 (B♭), 攝影 (C), 藝術 (D) — each a step higher.
    for t0, key, low in ((10.0, "Bb", "Bb1"), (18.5, "C", "C2"), (26.5, "D", "D2")):
        place(bus, t0, cymbal(2.4, .8))
        place(bus, t0, timpani(hz(low), 1.0))
        place(bus, t0, chord(voicing(key, 4) + [key + "5"], .7, 1.0), gain=.8)
    march(bus, 10.85, 18.4, "Bb", .85)
    march(bus, 19.3, 26.4, "C", .9)
    march(bus, 27.3, 34.7, "D", .95)
    place(bus, 12.0, timpani(hz("F2"), .8))                       # the newspaper lands

    # A short brass line over each march, one phrase per section.
    for t0, notes in ((14.0, ["F4", "Bb4", "D5", "C5", "Bb4"]), (20.0, ["G4", "C5", "E5", "D5", "C5"]),
                      (28.0, ["A4", "D5", "F#5", "E5", "D5"])):
        for j, n in enumerate(notes):
            place(bus, t0 + j * .5, brass(hz(n), .45 if j < len(notes) - 1 else 1.2, .9), gain=.7, pan=-.25)

    # 5 · Recap: the march builds.
    march(bus, 34.8, 38.4, "D", 1.15)
    roll(bus, 37.6, 38.5, snare, 22, (.2, 1.0), .1)
    place(bus, 38.35, chord(["A3", "C#4", "E4", "G4"], .45, 1.0), gain=.9)

    # 6 · 完: the final cadence.
    place(bus, 38.85, cymbal(3.5, 1.1))
    place(bus, 38.85, timpani(hz("D2"), 1.1, 2.2))
    place(bus, 38.85, chord(["D3", "A3", "D4", "F#4", "A4", "D5"], 1.6, 1.0), gain=1.0)
    roll(bus, 39.2, 40.25, lambda v: timpani(hz("D2"), v, .4), 14, (.9, .3))

    # Next issue: a music box ticking through two hours.
    box = ["D6", "A5", "F#5", "A5"]
    for j, t0 in enumerate(np.arange(40.8, 42.5, .25)):
        place(bus, t0, celesta(hz(box[j % 4])), pan=.3 if j % 2 else -.3)

    # Wordmark: a warm closing chord.
    for n in ("D3", "A3", "F#4", "A4"):
        place(bus, 42.8, brass(hz(n), 3.0, .55), gain=.35)
    place(bus, 42.8, piano(hz("D4"), .55, 3.5))
    place(bus, 43.3, celesta(hz("D6"), 2.5), gain=1.2)
    return bus


def effects() -> np.ndarray:
    bus = np.zeros((2, N))
    t = np.arange(N) / SR
    # Projector running under everything, as a soft whirr.
    whirr = butter(rng.normal(0, 1, N), [300, 1300], "band") * (0.75 + 0.25 * np.sin(2 * np.pi * 24 * t))
    place(bus, 0, whirr * envelope([0, .3, 1.0, 45, 46], [0, 0, 1, 1, 0]), gain=.018)
    # The newspaper spins in; section wipes; iris closes.
    place(bus, 10.85, whoosh(1.15, True), gain=.35)
    for t0 in (9.98, 18.48, 26.48):
        place(bus, t0, whoosh(.3, True), gain=.2)
    for t0 in (9.45, 29.6, 40.3):
        place(bus, t0, whoosh(.45, False), gain=.15)
    # Flash bulbs.
    for t0 in (19.3, 21.85, 24.2):
        place(bus, t0, pop(), gain=.5, pan=rng.uniform(-.3, .3))
    # The 一種關注 stamp.
    place(bus, 33.35, timpani(hz("G2"), .5, .5), gain=.6)
    return bus


def master(bus: np.ndarray) -> np.ndarray:
    hall_len = int(2.2 * SR)
    t = np.arange(hall_len) / SR
    ir = np.stack([rng.normal(0, 1, hall_len), rng.normal(0, 1, hall_len)]) * np.exp(-6.9 * t / 2.2)
    ir = butter(ir, 4500)
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    wet = np.stack([signal.fftconvolve(bus[c], ir[c])[:N] for c in range(2)])
    mix = bus * .78 + wet * .4
    mix = butter(mix, [85, 8000], "band")                   # old optical soundtrack
    mix += butter(rng.normal(0, 1, (2, N)), [2000, 7000], "band") * .0025 * envelope([0, .3, 45.3, 46], [0, 1, 1, 0])
    mix *= envelope([0, .2, 45.2, 46], [0, 1, 1, 0])
    mix = mix / np.abs(mix).max() * .95
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    return mix * 10 ** (-1 / 20)


def write(path: Path, bus: np.ndarray) -> None:
    pcm = (np.clip(bus, -1, 1).T * 32767).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(SR)
        out.writeframes(pcm.tobytes())


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("score.wav")
    write(target, master(music() + effects()))
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
