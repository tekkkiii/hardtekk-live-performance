#!/usr/bin/env python3
"""Generate an album of 10-drop hardtekk tracks.

Each track gets:
- its own sample-like synth palette
- its own rhythm/groove pattern
- 10 drops per track
- output as separate WAV files in an album folder

Run:
    python3 hardtekk_album.py --tracks 5 --output-dir album
"""

import argparse
import math
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100

TRACKS = [
    {"name": "Brachial 01", "bpm": 170, "root": 55.0, "seed": 11, "drive": 1.3, "color": 1.0},
    {"name": "Scharfkant 02", "bpm": 172, "root": 61.74, "seed": 23, "drive": 1.45, "color": 1.15},
    {"name": "Kettenspur 03", "bpm": 168, "root": 58.27, "seed": 37, "drive": 1.6, "color": 1.2},
    {"name": "Stahlregen 04", "bpm": 174, "root": 65.41, "seed": 51, "drive": 1.7, "color": 1.3},
    {"name": "Felsblock 05", "bpm": 176, "root": 73.42, "seed": 77, "drive": 1.9, "color": 1.4},
]


def sine(freq, t):
    return np.sin(2.0 * math.pi * freq * t)


def saw(freq, t):
    return 2.0 * (freq * t - np.floor(freq * t + 0.5))


def square(freq, t):
    return np.sign(np.sin(2.0 * math.pi * freq * t))


def triangle(freq, t):
    return 2.0 * np.abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0


def envelope(length, attack=0.01, release=0.8):
    a = max(1, int(length * attack))
    env = np.ones(length)
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a, endpoint=False)
    if length > a:
        env[a:] = np.linspace(1.0, release, length - a, endpoint=True)
    return env


def make_kick(duration, freq=52.0, amp=0.9):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    body = np.sin(2.0 * math.pi * freq * t)
    click = 0.55 * np.exp(-60.0 * t) * np.sin(2.0 * math.pi * 160.0 * t)
    env = np.exp(-10.0 * t)
    return (body + click) * env * amp


def make_snare(duration, amp=0.6):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    rng = np.random.default_rng(42)
    noise = rng.normal(0.0, 1.0, n)
    noise *= np.exp(-36.0 * t)
    tone = 0.7 * np.sin(2.0 * math.pi * 180.0 * t)
    return (noise + tone) * amp


def make_hat(duration, amp=0.20):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    rng = np.random.default_rng(7)
    noise = rng.normal(0.0, 1.0, n)
    env = np.exp(-120.0 * t)
    return noise * env * amp


def make_bass(freq, duration, amp=0.7):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    osc = 0.8 * square(freq, t) + 0.2 * sine(freq * 0.5, t)
    env = np.exp(-5.0 * t)
    return osc * env * amp


def make_lead(freq, duration, amp=0.28):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    osc = 0.7 * saw(freq, t) + 0.25 * sine(freq * 2.0, t)
    env = np.exp(-18.0 * t)
    return osc * env * amp


def make_pad(freq, duration, amp=0.12):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    osc = 0.7 * triangle(freq, t) + 0.3 * sine(freq * 0.5, t)
    env = envelope(n)
    return osc * env * amp


def make_riser(duration, freq_start=80.0, freq_end=2200.0, amp=0.18):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    ramp = np.linspace(0.0, 1.0, n)
    freq = freq_start + (freq_end - freq_start) * ramp
    sig = 0.5 * saw(freq, t) + 0.5 * noise_tone(freq, t)
    env = np.linspace(0.0, 1.0, n, endpoint=False)
    return sig * env * amp


def noise_tone(freq, t):
    rng = np.random.default_rng(int(freq * 1000) % 9973)
    noise = rng.normal(0.0, 1.0, len(t))
    return noise * np.exp(-0.2 * (t * freq / 100.0))


def generate_drop(track, drop_index, length_seconds=22.5):
    bpm = track["bpm"]
    beat = 60.0 / bpm
    base = track["root"]
    seed = track["seed"] + drop_index * 17
    rng = np.random.default_rng(seed)

    mix = np.zeros(int(length_seconds * SAMPLE_RATE), dtype=np.float32)
    bars = 8
    steps = int((length_seconds / (bars * beat)) * bars)
    # Each drop is 8 bars long, with accented pattern shifts per drop
    per_beat = int(beat * SAMPLE_RATE)

    for bar in range(bars):
        sec_start = bar * 4 * beat
        for beat_idx in range(4):
            sec = sec_start + beat_idx * beat
            beat_start = int(sec * SAMPLE_RATE)

            # Kick every 1st and 3rd beat, heavier late in the set
            if beat_idx in (0, 2):
                kick = make_kick(beat * 0.5, freq=base / 2.0, amp=0.9 * track["drive"])
                end = beat_start + len(kick)
                if end <= len(mix):
                    mix[beat_start:end] += kick

            # Snare on 2 and 4
            if beat_idx in (1, 3):
                snare = make_snare(beat * 0.4, amp=0.5 * track["drive"])
                start = beat_start + int(0.02 * SAMPLE_RATE)
                end = start + len(snare)
                if end <= len(mix):
                    mix[start:end] += snare

            # 16th hats
            for sub in range(4):
                hat_start = beat_start + int(sub * beat * 0.25 * SAMPLE_RATE)
                loud = 0.12 if sub % 2 == 0 else 0.08
                hat = make_hat(0.06, amp=loud * track["drive"]) * (1.05 + 0.1 * np.sin(drop_index + sub))
                end = hat_start + len(hat)
                if end <= len(mix):
                    mix[hat_start:end] += hat

            # Bass motion
            if beat_idx % 2 == 0:
                bass_freq = base * (1.0 + (bar % 4) * 0.08 + (drop_index % 3) * 0.03)
                bass = make_bass(bass_freq, beat * 0.75, amp=0.8 * track["drive"])
                start = beat_start
                end = start + len(bass)
                if end <= len(mix):
                    mix[start:end] += bass

    # Lead riffs appear every 4 bars and change across drops
    for lead_bar in range(0, bars, 2):
        lead_freq = base * 2.0 * (1.0 + (lead_bar % 4) * 0.12 + drop_index * 0.03)
        lead = make_lead(lead_freq, 5.0, amp=0.24 * track["color"])
        start = int((lead_bar * 4 * beat) * SAMPLE_RATE)
        end = start + len(lead)
        if end <= len(mix):
            mix[start:end] += lead

    # Rising noise sweep at bar 6 or late in each drop
    if drop_index % 2 == 0:
        rise = make_riser(1.2, freq_start=base * 2.0, freq_end=base * 40.0, amp=0.12 * track["drive"])
        start = int((6 * 4 * beat) * SAMPLE_RATE)
        end = start + len(rise)
        if end <= len(mix):
            mix[start:end] += rise

    # Fixed pad under the whole drop
    pad = make_pad(base * 0.5, length_seconds, amp=0.08 * track["color"])
    if len(pad) <= len(mix):
        mix += pad

    # gentle clip / normalize
    mix = np.clip(mix, -1.0, 1.0)
    return mix


def write_wav(path: Path, signal):
    stereo = np.column_stack([signal, signal]).astype(np.float32)
    with path.open("wb") as f:
        wav = __import__("wave").open(f.name, "wb")
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        pcm = np.int16(np.clip(stereo, -1.0, 1.0) * 32767.0)
        wav.writeframes(pcm.tobytes())
        wav.close()


def build_album(track_count: int, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, track in enumerate(TRACKS[:track_count], 1):
        track_mix = np.zeros(0, dtype=np.float32)
        for drop_idx in range(10):
            drop = generate_drop(track, drop_idx, length_seconds=22.5)
            track_mix = np.concatenate([track_mix, drop]) if track_mix.size else drop

        file_name = f"{idx:02d}_{track['name'].lower().replace(' ', '_')}.wav"
        path = out_dir / file_name
        write_wav(path, track_mix)
        print(f"Created {path} ({len(track_mix) / SAMPLE_RATE:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="Generate a multi-track hardtekk album with 10 drops per track.")
    parser.add_argument("--tracks", type=int, default=5, help="Number of tracks to generate (max 5)")
    parser.add_argument("--output-dir", default="album", help="Directory for WAV files")
    args = parser.parse_args()

    track_count = min(max(1, args.tracks), len(TRACKS))
    build_album(track_count, Path(args.output_dir))


if __name__ == "__main__":
    main()
