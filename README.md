#!/usr/bin/env python3
"""Generate a 10-minute hardtekk-style live performance demo.

Modes:
    brutal  = much more aggressive, louder kick, more distortion feel
    club    = cleaner, punchier, more dance-floor friendly
    structured = section-labeled arrangement with clear transitions

Usage:
    python3 hardtekk_live.py --style brutal --output hardtekk_live_brutal.wav
    python3 hardtekk_live.py --style club --output hardtekk_live_club.wav
    python3 hardtekk_live.py --style structured --output hardtekk_live_structured.wav
"""

import argparse
import math
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100
BPM = 170
SECONDS_PER_BEAT = 60.0 / BPM
SIXTEENTH = SECONDS_PER_BEAT / 4.0
TOTAL_SECONDS = 10 * 60

SECTION_ORDER = [
    (0, 45, "Intro / build"),
    (45, 140, "Main groove"),
    (140, 255, "Peak intensity"),
    (255, 355, "Breakdown / reset"),
    (355, 470, "Mad rush"),
    (470, 540, "Second peak"),
    (540, 600, "Final impact"),
]

STYLES = {
    "brutal": {
        "kick_amp": 1.15,
        "snare_amp": 0.72,
        "hat_amp": 0.24,
        "bass_amp": 0.88,
        "lead_amp": 0.38,
        "pad_amp": 0.12,
        "drive": 1.6,
        "intensity": 1.35,
    },
    "club": {
        "kick_amp": 0.92,
        "snare_amp": 0.58,
        "hat_amp": 0.17,
        "bass_amp": 0.72,
        "lead_amp": 0.28,
        "pad_amp": 0.1,
        "drive": 1.1,
        "intensity": 1.0,
    },
    "structured": {
        "kick_amp": 1.0,
        "snare_amp": 0.62,
        "hat_amp": 0.19,
        "bass_amp": 0.76,
        "lead_amp": 0.3,
        "pad_amp": 0.11,
        "drive": 1.25,
        "intensity": 1.15,
    },
}


def sine(freq, t):
    return np.sin(2.0 * math.pi * freq * t)


def square(freq, t):
    return np.sign(np.sin(2.0 * math.pi * freq * t))


def triangle(freq, t):
    return 2.0 * np.abs(2.0 * ((freq * t) % 1.0) - 1.0) - 1.0


def saw(freq, t):
    return 2.0 * (freq * t - np.floor(freq * t + 0.5))


def make_kick(duration_sec, amp=0.9, sample_rate=SAMPLE_RATE):
    n = int(duration_sec * sample_rate)
    t = np.arange(n) / sample_rate
    body = np.sin(2.0 * math.pi * 52.0 * t)
    click = 0.55 * np.exp(-60.0 * t) * np.sin(2.0 * math.pi * 160.0 * t)
    env = np.exp(-12.0 * t)
    return (body + click) * env * amp


def make_snare(duration_sec, amp=0.55, sample_rate=SAMPLE_RATE):
    n = int(duration_sec * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)
    noise = rng.normal(0.0, 1.0, n)
    noise *= np.exp(-26.0 * t)
    tone = 0.5 * np.sin(2.0 * math.pi * 190.0 * t)
    return (noise + tone) * amp * 0.8


def make_hat(duration_sec, amp=0.22, sample_rate=SAMPLE_RATE):
    n = int(duration_sec * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(7)
    noise = rng.normal(0.0, 1.0, n)
    env = np.exp(-110.0 * t)
    return noise * env * amp


def make_bass_note(freq, duration, amp=0.7, sample_rate=SAMPLE_RATE):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    osc = 0.8 * square(freq, t) + 0.2 * sine(freq * 0.5, t)
    env = np.exp(-5.0 * t)
    return osc * env * amp


def make_pad_note(freq, duration, amp=0.18, sample_rate=SAMPLE_RATE):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    osc = 0.5 * triangle(freq, t) + 0.35 * sine(freq * 2.0, t)
    attack = np.linspace(0.0, 1.0, n, endpoint=False)
    release = np.linspace(1.0, 0.0, n, endpoint=False)
    env = np.minimum(attack, release)
    return osc * env * amp


def make_lead(freq, duration, amp=0.24, sample_rate=SAMPLE_RATE):
    n = int(duration * sample_rate)
    t = np.arange(n) / sample_rate
    osc = 0.7 * saw(freq, t) + 0.35 * sine(freq * 0.5, t)
    env = np.exp(-16.0 * t)
    return osc * env * amp


def section_for_time(seconds):
    for start, end, name in SECTION_ORDER:
        if start <= seconds < end:
            return name
    return "Final impact"


def render_track(output_path: Path, style_name: str = "structured"):
    profile = STYLES[style_name]
    total_samples = int(TOTAL_SECONDS * SAMPLE_RATE)
    mix = np.zeros(total_samples, dtype=np.float32)

    root_pattern = [110.0, 117.0, 98.0, 110.0, 98.0, 110.0, 93.0, 98.0]
    lead_pattern = [220.0, 247.0, 220.0, 196.0, 220.0, 247.0, 196.0, 220.0]

    beat_count = int(TOTAL_SECONDS / SECONDS_PER_BEAT)
    bar = 0

    for beat in range(beat_count):
        sec = beat * SECONDS_PER_BEAT
        section_name = section_for_time(sec)
        intensity = profile["intensity"]

        # Kick and snare pattern; more aggressive in brutal mode
        if beat % 4 in (0, 2):
            kick = make_kick(0.18, amp=profile["kick_amp"]) * (1.1 if "brutal" == style_name else 1.0)
            start = int(sec * SAMPLE_RATE)
            end = start + len(kick)
            if end <= len(mix):
                mix[start:end] += kick

        if beat % 4 in (1, 3):
            snare = make_snare(0.16, amp=profile["snare_amp"]) * (1.2 if "brutal" == style_name else 1.0)
            start = int((sec + 0.02) * SAMPLE_RATE)
            end = start + len(snare)
            if end <= len(mix):
                mix[start:end] += snare

        # 16th hats with slight variation by section
        for step in range(4):
            sub_sec = sec + step * SIXTEENTH
            hat_amp = profile["hat_amp"] * (1.2 if section_name in ("Peak intensity", "Mad rush", "Final impact") else 1.0)
            if section_name == "Breakdown / reset":
                hat_amp *= 0.7
            hat = make_hat(0.06, amp=hat_amp)
            start = int(sub_sec * SAMPLE_RATE)
            end = start + len(hat)
            if end <= len(mix):
                mix[start:end] += hat

        # Bassline: very heavy for brutal, tighter for club
        if beat % 2 == 0:
            freq = root_pattern[bar % len(root_pattern)]
            bass = make_bass_note(freq, 0.32, amp=profile["bass_amp"]) * (1.15 if style_name == "brutal" else 1.0)
            start = int(sec * SAMPLE_RATE)
            end = start + len(bass)
            if end <= len(mix):
                mix[start:end] += bass

        # Lead accent pattern
        if bar % 2 == 0 and section_name not in ("Breakdown / reset", "Intro / build"):
            lead_freq = lead_pattern[bar % len(lead_pattern)]
            lead_amp = profile["lead_amp"] * (1.2 if section_name in ("Peak intensity", "Mad rush", "Final impact") else 1.0)
            lead = make_lead(lead_freq, 0.16, amp=lead_amp)
            start = int((sec + 0.12) * SAMPLE_RATE)
            end = start + len(lead)
            if end <= len(mix):
                mix[start:end] += lead

        # Pads and risers for transition sections
        if section_name in ("Intro / build", "Breakdown / reset") and beat % 8 == 0:
            pad = make_pad_note(82.41, 0.8, amp=profile["pad_amp"])
            start = int((sec + 0.1) * SAMPLE_RATE)
            end = start + len(pad)
            if end <= len(mix):
                mix[start:end] += pad

        if section_name in ("Second peak", "Final impact") and beat % 4 == 0:
            pad = make_pad_note(98.0, 0.6, amp=profile["pad_amp"] * 1.3)
            start = int((sec + 0.15) * SAMPLE_RATE)
            end = start + len(pad)
            if end <= len(mix):
                mix[start:end] += pad

        if beat % 4 == 3:
            bar += 1

    # light clipping and normalization
    mix = np.clip(mix, -1.0, 1.0)
    stereo = np.column_stack([mix, mix]).astype(np.float32)

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        int_data = np.int16(np.clip(stereo, -1.0, 1.0) * 32767.0)
        wav_file.writeframes(int_data.tobytes())

    print(f"Created {output_path} using style='{style_name}'")


def main():
    parser = argparse.ArgumentParser(description="Generate a 10-minute hardtekk live performance demo.")
    parser.add_argument("--style", choices=["brutal", "club", "structured"], default="structured", help="Production style")
    parser.add_argument("--output", default="hardtekk_live_10min.wav", help="Output WAV path")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    render_track(output_path, style_name=args.style)


if __name__ == "__main__":
    main()


# Section labels in this arrangement:
# - Intro / build
# - Main groove
# - Peak intensity
# - Breakdown / reset
# - Mad rush
# - Second peak
# - Final impact
