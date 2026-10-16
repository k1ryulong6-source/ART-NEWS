"""Synthesise the score for the 幕間休息 promo film 「一束光」.

Everything is generated here (no samples, no third-party recordings): a felt-piano
voice, a slow string-like pad, and sound effects tied to the picture — the projector,
the enlarger, the developing tray, the gallery lamp, the door and the neon 日. The cue
times below are the same seconds as the film's timeline in src/promo.html.

  python promo/score.py promo/score.wav        (needs numpy and scipy)

The film is in D minor and resolves to D major when 日 lights up.
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
LENGTH = 40.0
N = int(SR * LENGTH)
rng = np.random.default_rng(1013)


def midi(note: str) -> float:
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    pitch = names[note[0]]
    rest = note[1:]
    if rest.startswith("#"):
        pitch += 1
        rest = rest[1:]
    elif rest.startswith("b"):
        pitch -= 1
        rest = rest[1:]
    return 440.0 * 2 ** ((pitch + 12 * (int(rest) + 1) - 69) / 12)


def at(t: float) -> int:
    return max(0, min(N, int(t * SR)))


def buffer() -> np.ndarray:
    return np.zeros((2, N))


def place(bus: np.ndarray, start: float, sound: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
    i = at(start)
    n = min(len(sound), N - i)
    if n <= 0:
        return
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    bus[0, i:i + n] += sound[:n] * gain * left
    bus[1, i:i + n] += sound[:n] * gain * right


def butter(sound: np.ndarray, cutoff, kind: str = "low", order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, sound, axis=-1)


def envelope(times: list[float], levels: list[float], length: int = N) -> np.ndarray:
    t = np.arange(length) / SR
    return np.interp(t, times, levels)


# ── Voices ─────────────────────────────────────────────────────────────────────
def piano(freq: float, velocity: float = .7, length: float = 4.5) -> np.ndarray:
    """Soft felt piano: inharmonic partials with per-partial decay and a muted hammer."""
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    inharm = 0.00035
    base_decay = 3.2 * (220 / freq) ** 0.35
    for k in range(1, 11):
        f = k * freq * np.sqrt(1 + inharm * k * k)
        if f > SR / 2.2:
            break
        amp = (1 / k ** 1.5) * (velocity ** (0.6 * (k - 1)))
        decay = base_decay / (1 + 0.35 * (k - 1))
        phase = rng.uniform(0, 2 * np.pi)
        out += amp * np.sin(2 * np.pi * f * t + phase) * np.exp(-t / decay)
    attack = np.minimum(1, t / 0.004)
    hammer = butter(rng.normal(0, 1, n), 1800) * np.exp(-t / 0.012) * 0.05
    release = np.minimum(1, (length - t) / 0.4)
    return (out * attack + hammer) * release * velocity * 0.35


def pad(freqs: list[float], length: float, cutoff: float = 1400) -> np.ndarray:
    """Slow strings: three detuned saws per note, filtered, with gentle vibrato."""
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for freq in freqs:
        for cents in (-7, 0, 6):
            f = freq * 2 ** (cents / 1200)
            vib = 1 + 0.0025 * np.sin(2 * np.pi * (4.6 + rng.uniform(-.4, .4)) * t + rng.uniform(0, 6))
            phase = np.cumsum(f * vib) / SR + rng.uniform(0, 1)
            out += signal.sawtooth(2 * np.pi * phase) / 3
    out = butter(out, cutoff, order=2)
    out = butter(out, 90, "high")
    return out / max(1, len(freqs)) * 0.28


def bell(freq: float, length: float = 5.0) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for ratio, amp, decay in ((1, 1, 3.2), (2.76, .45, 1.6), (5.4, .25, .9), (8.93, .12, .5)):
        out += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / decay)
    return out * np.minimum(1, t / 0.002) * 0.18


def click(length: float = .06, tone: float = 2400, gain: float = 1.0) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    burst = rng.normal(0, 1, n) * np.exp(-t / 0.004)
    body = np.sin(2 * np.pi * tone * t) * np.exp(-t / 0.01) * .4
    return butter(burst + body, [500, 7000], "band") * gain


def thump(length: float = 1.2, freq: float = 55) -> np.ndarray:
    n = int(length * SR)
    t = np.arange(n) / SR
    sweep = freq * (1 + 1.5 * np.exp(-t / 0.03))
    return np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t / 0.25) * 0.8


def reverb(bus: np.ndarray, seconds: float = 3.4, mix: float = .32) -> np.ndarray:
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.normal(0, 1, n), rng.normal(0, 1, n)]) * np.exp(-6.9 * t / seconds)
    ir = butter(ir, 5200)
    ir[:, :int(.018 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    wet = np.stack([signal.fftconvolve(bus[c], ir[c])[:N] for c in range(2)])
    return bus * (1 - mix) + wet * mix * 1.6


# ── Score ──────────────────────────────────────────────────────────────────────
def music() -> np.ndarray:
    bus = buffer()

    # Pad: Dm9 (cinema) → Bbmaj7 → Gm9 (darkroom) → Fmaj7 → C/E → Dm9 (gallery)
    # → A sus4 (the door) → D major add9 when 日 lights.
    chords = [
        (1.0, 10.8, ["D3", "A3", "C4", "E4", "F4"], 1100),
        (10.0, 15.6, ["Bb2", "F3", "A3", "D4"], 900),
        (15.0, 19.6, ["G2", "D3", "F3", "A3", "Bb3"], 900),
        (19.0, 23.6, ["F2", "C3", "E3", "A3", "C4"], 1500),
        (23.0, 26.4, ["E2", "C3", "G3", "C4", "D4"], 1500),
        (25.8, 29.6, ["D2", "A2", "F3", "C4", "E4"], 1300),
        (29.0, 32.0, ["A2", "E3", "A3", "D4"], 1000),
        (31.4, 40.0, ["D2", "A2", "F#3", "A3", "E4", "F#4"], 1700),
    ]
    for start, end, notes, cutoff in chords:
        length = end - start
        sound = pad([midi(n) for n in notes], length, cutoff)
        env = envelope([0, 1.2, length - 1.2, length], [0, 1, 1, 0], len(sound))
        place(bus, start, sound * env, gain=1.0)
    # Swell through the push into the screen and when the lamp turns white.
    swell = envelope([0, 9.2, 10.4, 11.2, 18.2, 19.3, 20.4, 40], [1, 1, 1.8, 1, 1, 1.6, 1, 1])
    bus *= swell

    # Felt piano, three phrases and a resolution.
    phrases = [
        # cinema: D minor, mid register
        (2.4, "A4", .55), (3.6, "D5", .6), (4.8, "E5", .55), (6.0, "F5", .65), (7.4, "E5", .5),
        (8.2, "C5", .45), (9.0, "D5", .55),
        # darkroom: lower, slower
        (12.8, "D4", .5), (14.0, "F4", .5), (15.2, "A4", .55), (16.6, "G4", .5), (17.8, "Bb4", .5),
        # gallery: brighter
        (20.6, "C5", .55), (21.8, "A5", .6), (23.0, "G5", .55), (24.2, "E5", .5), (25.4, "F5", .55),
        (26.6, "D5", .5), (27.6, "E5", .45),
        # door: one held note
        (29.4, "A4", .4),
        # 日: D major arpeggio, then the tagline bell
        (33.3, "D4", .5), (33.55, "A4", .5), (33.8, "F#5", .55), (34.05, "E5", .5), (34.4, "A5", .55),
    ]
    for start, note, velocity in phrases:
        f = midi(note)
        pan = np.clip((np.log2(f / 440)) * 0.5, -.6, .6)
        place(bus, start, piano(f, velocity, 5.5), pan=pan)
    place(bus, 35.2, bell(midi("D6"), 4.6), pan=.15)
    place(bus, 35.2, bell(midi("A5"), 4.6), gain=.5, pan=-.2)
    return bus


def effects() -> np.ndarray:
    bus = buffer()
    t = np.arange(N) / SR

    # Projector: lamp switch, then a 24 fps shutter rattle and motor hum.
    place(bus, 1.1, click(.08, 1800, 1.2), gain=.5, pan=.5)
    place(bus, 1.1, thump(.6, 70), gain=.25, pan=.5)
    rattle = np.zeros(N)
    for frame in np.arange(1.25, 10.5, 1 / 24):
        i = at(frame + rng.normal(0, .0015))
        burst = click(.02, 2600 + rng.normal(0, 80), 1)
        rattle[i:i + len(burst)] += burst[:max(0, N - i)]
    motor = np.sin(2 * np.pi * 48 * t) * .5 + np.sin(2 * np.pi * 96 * t) * .25
    projector = (rattle * .35 + motor * .02) * envelope([0, 1.2, 1.6, 9.2, 10.4, 10.5, 40], [0, 0, 1, 1, .6, 0, 0])
    place(bus, 0, butter(projector, 6000), gain=.55, pan=.55)

    # Push into the screen: an airy riser.
    riser = butter(rng.normal(0, 1, N), [1500, 9000], "band") * envelope([0, 9.0, 10.45, 10.9, 40], [0, 0, .5, 0, 0])
    place(bus, 0, riser, gain=.25)

    # Enlarger: switch on, lamp hum, switch off with the timer's beep.
    place(bus, 10.6, click(.05, 2000, 1), gain=.45, pan=-.2)
    hum = (np.sin(2 * np.pi * 100 * t) + .4 * np.sin(2 * np.pi * 200 * t)) * envelope([0, 10.6, 10.7, 12.05, 12.15, 40], [0, 0, 1, 1, 0, 0])
    place(bus, 0, hum, gain=.03)
    place(bus, 12.12, click(.05, 1600, 1), gain=.45, pan=-.2)
    beep = np.sin(2 * np.pi * 2093 * t[:int(.18 * SR)]) * np.minimum(1, np.minimum(t[:int(.18 * SR)] / .005, (.18 - t[:int(.18 * SR)]) / .02))
    place(bus, 12.18, beep, gain=.06, pan=.3)

    # Developer tray: liquid moving with each rock of the tray.
    rock = np.cos((t - 12.4) * 2.4)
    slosh_env = np.abs(rock) ** 3 * envelope([0, 12.4, 13.2, 18.2, 19.2, 40], [0, 0, 1, 1, 0, 0])
    water = butter(rng.normal(0, 1, N), [250, 1800], "band")
    water = water * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t + np.sin(2 * np.pi * .9 * t)))
    for c, pan in ((0, -.4), (1, .4)):
        side = slosh_env * (0.5 + 0.5 * np.sign(rock) * (1 if c else -1))
        place(bus, 0, water * side, gain=.09, pan=pan)

    # Safelight turns into the gallery lamp: a big switch, felt more than heard.
    place(bus, 19.25, click(.08, 1200, 1), gain=.5)
    place(bus, 19.25, thump(1.4, 48), gain=.45)

    # The door: air moving through the gap.
    air = butter(rng.normal(0, 1, N), [180, 2400], "band") * envelope([0, 28.8, 29.8, 30.8, 31.6, 40], [0, 0, .7, .5, 0, 0])
    place(bus, 0, air, gain=.16)

    # Neon 日: hum that stutters with the flicker keyframes (31.5s + % of 1.6s).
    start, dur = 31.5, 1.6
    on = envelope([0, start, start + .08 * dur, start + .12 * dur, start + .22 * dur, start + .27 * dur,
                   start + .42 * dur, start + dur, 33.3, 34.6, 40],
                  [0, 0, 1, 0, 1, 0, .7, .45, .35, 0, 0])
    buzz = signal.sawtooth(2 * np.pi * 120 * t) * .4 + np.sin(2 * np.pi * 60 * t)
    buzz = butter(buzz, [80, 3200], "band") * on
    place(bus, 0, buzz, gain=.05)
    for k in (.08, .22, .42):
        place(bus, start + k * dur, click(.03, 3000, 1), gain=.35)

    # Room tone under everything.
    room = butter(rng.normal(0, 1, (2, N)), 900) * envelope([0, .4, 38.8, 40], [0, 1, 1, 0])
    bus += room * .006
    return bus


def master(bus: np.ndarray) -> np.ndarray:
    bus = butter(bus, 28, "high")
    bus *= envelope([0, .3, 39.0, 40], [0, 1, 1, 0])
    peak = np.abs(bus).max()
    bus = bus / peak * 0.95
    bus = np.tanh(bus * 1.15) / np.tanh(1.15)     # gentle saturation, never clips
    return bus * 10 ** (-1 / 20)


def write(path: Path, bus: np.ndarray) -> None:
    pcm = (np.clip(bus, -1, 1).T * 32767).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(SR)
        out.writeframes(pcm.tobytes())


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("score.wav")
    mix = reverb(music(), 3.6, .38) + reverb(effects(), 1.8, .2)
    write(target, master(mix))
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
