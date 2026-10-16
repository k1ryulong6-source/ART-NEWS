"""Synthesise the soundtrack for the 幕間休息 promo film 「明日新聞台」 (a black-and-white
1950s television cartoon in the manner of the Fallout series' shorts).

Everything is generated here — no samples, no third-party recordings — as 1950s
space-age lounge music: vibraphone, a theremin-like lead with glides, walking bass,
brushed drums and bright brass stabs, a weightless "space" passage for 一種關注, and a
short jingle on the atom and wordmark. Effects: the television switching on and off,
the zoom into the screen, the rocket. The English voiceover (promo/voice/l1–l6.mp3, see
voice.py) is given an old-radio colour and the music ducks under it. Cue times are the
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
LENGTH = 46.5
N = int(SR * LENGTH)
rng = np.random.default_rng(1957)


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


# ── Lounge instruments ────────────────────────────────────────────────────────
def vibes(freq: float, length: float = 2.4, level: float = 1.0) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    trem = 1 - .32 * (.5 + .5 * np.sin(2 * np.pi * 5.6 * t))
    tone = np.sin(2 * np.pi * freq * t) * np.exp(-t / 1.6) + .22 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t / .25)
    return fade(tone * trem, .003, .3) * level * .22


def theremin(bus, start: float, notes: list, gain: float = .5, pan: float = -.15) -> None:
    """A continuous sine voice gliding between (beats, note) pairs, with vibrato."""
    beat = 60 / 128
    total = sum(b for b, _ in notes) * beat
    n = int(total * SR)
    t = np.arange(n) / SR
    freq = np.zeros(n)
    gate = np.zeros(n)
    pos = 0
    for beats, note in notes:
        m = int(beats * beat * SR)
        if note:
            freq[pos:pos + m] = hz(note)
            gate[pos:pos + m] = 1
        else:
            freq[pos:pos + m] = freq[pos - 1] if pos else 440
        pos += m
    freq = butter(freq, 9)                       # portamento: glide between pitches
    gate = butter(gate, 14)
    vib = 1 + .011 * np.sin(2 * np.pi * 6.2 * t) * np.minimum(1, t / .4)
    phase = 2 * np.pi * np.cumsum(freq * vib) / SR
    voice = (np.sin(phase) + .12 * np.sin(2 * phase)) * np.clip(gate, 0, 1)
    place(bus, start, fade(voice, .05, .3) * .2, gain=gain, pan=pan)


def bass(freq: float, length: float = .45) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * freq * t) + .45 * np.sin(4 * np.pi * freq * t) + .18 * np.sin(6 * np.pi * freq * t)
    return butter(fade(tone * np.exp(-t / .32), .006, .08), 900) * .5


def brush(level: float = 1.0) -> np.ndarray:
    n = int(.32 * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / .03) * np.exp(-t / .12)
    return butter(rng.normal(0, 1, n), [1200, 7000], "band") * env * level * .22


def ride(level: float = 1.0) -> np.ndarray:
    n = int(.5 * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / .012) * np.exp(-t / .22)          # soft attack: a shimmer, not a click
    shimmer = butter(rng.normal(0, 1, n), [4000, 9000], "band") + .2 * np.sin(2 * np.pi * 6200 * t)
    return shimmer * env * level * .035


def sweep(length: float, f0: float, f1: float) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / length)
    return fade(np.sin(2 * np.pi * np.cumsum(f) / SR), .02, .08) * .25


# ── Score ──────────────────────────────────────────────────────────────────────
BEAT = 60 / 128
CHORDS = {"Fmaj7": ["F3", "A3", "C4", "E4"], "Dm7": ["D3", "F3", "A3", "C4"], "Gm7": ["G3", "Bb3", "D4", "F4"],
          "C7": ["C3", "E3", "G3", "Bb3"], "Bbmaj7": ["Bb2", "D3", "F3", "A3"], "F69": ["F3", "A3", "D4", "G4", "C5"]}
WALK = {"Fmaj7": ["F2", "A2", "C3", "E3"], "Dm7": ["D2", "F2", "A2", "C3"], "Gm7": ["G2", "Bb2", "D3", "E3"],
        "C7": ["C3", "Bb2", "G2", "E2"]}
LOOP = ["Fmaj7", "Dm7", "Gm7", "C7"]


def groove(bus, start: float, end: float, level: float = 1.0, drums: bool = True) -> None:
    """Swing lounge: walking bass on every beat, brushes on 2 and 4, ride in swung
    eighths, vibraphone comping on 1 and the 'and' of 2."""
    t, b = start, 0
    while t < end - .05:
        name = LOOP[(b // 4) % 4]
        place(bus, t, bass(hz(WALK[name][b % 4])), gain=.9 * level, pan=-.05)
        if drums:
            if b % 2 == 1:
                place(bus, t, brush(1.0), gain=.9 * level, pan=.2)
            place(bus, t, ride(.8), gain=level, pan=.35)
            place(bus, t + BEAT * 2 / 3, ride(.5), gain=level, pan=.35)
        if b % 4 in (0, 1):
            when = t if b % 4 == 0 else t + BEAT * 2 / 3
            for note in CHORDS[name]:
                place(bus, when, vibes(hz(note[:-1] + str(int(note[-1]) + 1)), 1.4, .55), gain=.7 * level, pan=.25)
        t += BEAT
        b += 1


def stab(bus, t0: float, notes: list, length: float = .3, gain: float = .8) -> None:
    place(bus, t0, chord(notes, length, 1.0), gain=gain)


VOICE_AT = [0.9, 7.1, 15.0, 21.8, 30.4, 36.6]       # when each line starts (subtitles match)


def music() -> np.ndarray:
    bus = np.zeros((2, N))

    # 1 · Television on: a theremin swoops up as the test card appears; a stab as the host pops in.
    theremin(bus, .9, [(1.2, "C4"), (1.4, "F5"), (1.2, "E5"), (.8, None)], gain=.5)
    for note in CHORDS["F69"]:
        place(bus, 1.05, vibes(hz(note[:-1] + str(int(note[-1]) + 1)), 3.0), gain=.8, pan=.2)
    stab(bus, 1.7, ["F4", "A4", "C5", "F5"], .3, .7)
    stab(bus, 1.95, ["F4", "A4", "C5", "F5"], .6, .7)

    # 2–4 · The groove, with a theremin tune over it.
    groove(bus, 6.6, 30.0, 1.0)
    tune_a = [(1, "C5"), (1, "A4"), (1, "F4"), (1, "A4"), (2, "C5"), (2, "D5"), (1, "C5"), (1, "Bb4"), (1, "A4"), (1, "G4"), (4, "A4"), (2, None)]
    tune_b = [(1, "F5"), (1, "E5"), (1, "D5"), (1, "C5"), (2, "D5"), (2, "Bb4"), (1, "A4"), (1, "G4"), (1, "F4"), (1, "E4"), (4, "F4"), (2, None)]
    for t0, tune in ((7.1, tune_a), (14.6, tune_b), (21.6, tune_a), (25.4, tune_b)):
        theremin(bus, t0, tune, gain=.5)
    for t0 in (14.6, 21.4):                                      # scene changes
        stab(bus, t0, ["C4", "E4", "G4", "Bb4"], .25, .75)
        stab(bus, t0 + BEAT * 2 / 3, ["F4", "A4", "C5", "F5"], .55, .8)
        place(bus, t0, cymbal(1.8, .5))
    for t0 in (23.65, 26.7):                                     # the monorail moves on
        stab(bus, t0, ["Bb3", "D4", "F4", "A4"], .4, .45)

    # 5 · 一種關注: weightless — drums and bass drop, the theremin floats, stars chime.
    theremin(bus, 30.5, [(3, "C5"), (2, "F5"), (3, "E5"), (2, "C5"), (4, "D5")], gain=.55)
    for j, note in enumerate(["F5", "A5", "C6", "E6", "G6", "A6"]):
        place(bus, 32.4 + .3 * j, celesta(hz(note), 1.6), gain=1.1, pan=-.5 + .2 * j)
    for t0, name in ((30.0, "Bbmaj7"), (33.0, "Gm7")):
        for note in CHORDS[name]:
            place(bus, t0, vibes(hz(note[:-1] + str(int(note[-1]) + 1)), 3.2, .7), gain=.7, pan=.2)

    # 6 · The atom and the wordmark: the jingle, the groove's last bars, the closing chord.
    jingle = [(39.4, "C5"), (39.7, "A4"), (40.0, "F4"), (40.3, "C5"), (40.6, "F5")]
    for t0, note in jingle:
        place(bus, t0, brass(hz(note), .26 if note != "F5" else 1.1, 1.0), gain=.8)
        place(bus, t0, vibes(hz(note), 1.2), gain=.8)
    place(bus, 40.6, cymbal(2.2, .6))
    for note in CHORDS["Fmaj7"]:
        place(bus, 36.4, vibes(hz(note[:-1] + str(int(note[-1]) + 1)), 2.6), gain=.8, pan=.2)
    groove(bus, 41.4, 45.4, .8)
    stab(bus, 45.4, ["F3", "A3", "D4", "G4", "C5"], .9, .6)
    return bus


def effects() -> np.ndarray:
    bus = np.zeros((2, N))
    place(bus, .1, timpani(hz("G2"), .25, .3), gain=.6)                # the switch
    place(bus, .45, sweep(.7, 180, 1400), gain=.35)                     # tube warm-up
    place(bus, 5.9, whoosh(.8, True), gain=.4)                          # zoom into the screen
    place(bus, 30.3, whoosh(2.6, False), gain=.3, pan=.3)               # the rocket
    for t0 in (31.9, 32.5, 33.1):                                       # the view widens
        place(bus, t0, sweep(1.2, 300, 600) * .5, gain=.25)
    place(bus, 45.6, sweep(.55, 2200, 120), gain=.45)                   # television off
    return bus


def load(path: Path) -> np.ndarray:
    import subprocess
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(float) / 32768


def radio(x: np.ndarray) -> np.ndarray:
    """A 1950s broadcast voice: narrow band, a forward presence peak, tube saturation and a
    small studio."""
    x = butter(x, [280, 4300], "band", order=4)
    x = x + .35 * butter(x, [1800, 3200], "band")
    x = np.tanh(x * 3.0) / np.tanh(3.0)
    n = int(.4 * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t / .08)
    ir[:int(.01 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum())
    return x + .18 * signal.fftconvolve(x, ir)[:len(x)]


def voice() -> tuple:
    track, spans = np.zeros(N), []
    folder = Path(__file__).with_name("voice")
    for i, start in enumerate(VOICE_AT, 1):
        line = radio(load(folder / f"l{i}.mp3"))
        line = line / np.abs(line).max()
        a = at(start)
        n = min(len(line), N - a)
        track[a:a + n] += line[:n]
        spans.append((start, start + n / SR))
    return track, spans


def master(bus: np.ndarray) -> np.ndarray:
    room = int(1.6 * SR)
    t = np.arange(room) / SR
    ir = np.stack([rng.normal(0, 1, room), rng.normal(0, 1, room)]) * np.exp(-6.9 * t / 1.6)
    ir = butter(ir, 6000)
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    wet = np.stack([signal.fftconvolve(bus[c], ir[c])[:N] for c in range(2)])
    mix = bus * .8 + wet * .35
    mix = butter(mix, [55, 11000], "band")                    # warm, slightly vintage
    mix *= envelope([0, .05, 45.95, 46.3], [0, 1, 1, 0])
    mix = mix / np.abs(mix).max() * .95
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
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
    bed = master(music() + effects())
    vo, spans = voice()
    # Duck the music for the whole of each line (about −14 dB), easing in and out, so it
    # does not swell back between words.
    window = np.zeros(N)
    for start, end in spans:
        window[at(start - .12):at(end + .2)] = 1
    duck = 1 - .8 * np.clip(butter(window, 3), 0, 1)
    mix = bed * duck + np.stack([vo, vo]) * .95
    mix = mix / np.abs(mix).max() * .9
    write(target, mix)
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
