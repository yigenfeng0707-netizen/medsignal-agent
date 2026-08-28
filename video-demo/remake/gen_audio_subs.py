#!/usr/bin/env python3
"""Generate BGM, mix TTS+BGM audio, and create ASS subtitles."""

import numpy as np
import wave
import json
import os
import struct
import subprocess
import sys

SR = 44100
WORKDIR = "D:/APPs/VentureDhealthcare/video-demo/remake"
TTS_DIR = os.path.join(WORKDIR, "tts")
AUDIO_DIR = os.path.join(WORKDIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Load timeline
with open(os.path.join(WORKDIR, "timeline.json"), "r", encoding="utf-8") as f:
    TL_DATA = json.load(f)
TOTAL_DUR = TL_DATA["total_duration"]
TIMELINE = TL_DATA["segments"]


def write_wav(samples, path, ch=1):
    s = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    if ch == 2:
        s = np.column_stack([s, s])
    with wave.open(path, "w") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(s.tobytes())


def read_wav(path):
    with wave.open(path, "r") as w:
        nc = w.getnchannels()
        data = w.readframes(w.getnframes())
        s = struct.unpack("<" + "h" * (len(data) // 2), data)
        s = np.array(s, dtype=np.float64) / 32768.0
        if nc == 2:
            s = s.reshape(-1, 2).mean(axis=1)
    return s


def mp3_to_wav(mp3_path, wav_path):
    r = subprocess.run(
        f'ffmpeg -y -i "{mp3_path}" -ar {SR} -ac 1 -f wav "{wav_path}"',
        shell=True,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"ERROR converting {mp3_path}: {r.stderr[:200]}", file=sys.stderr)
        sys.exit(1)


def gen_bgm(duration, timeline):
    """Generate light tech-style BGM: C major chord progression (C-G-Am-F)."""
    n = int(duration * SR)
    t = np.arange(n) / SR

    # Chord progression: C(I) - G(V) - Am(vi) - F(IV), each 4s
    chord_dur = 4.0
    # (root_low, root_mid, third, fifth) frequencies
    chords = [
        (130.81, 261.63, 329.63, 392.00),  # C:  C3-C4-E4-G4
        (196.00, 392.00, 493.88, 587.33),  # G:  G3-G4-B4-D5
        (220.00, 440.00, 523.25, 659.25),  # Am: A3-A4-C5-E5
        (174.61, 349.23, 440.00, 523.25),  # F:  F3-F4-A4-C5
    ]
    amps = [0.05, 0.025, 0.015, 0.008]  # decreasing amplitude per harmonic

    s = np.zeros(n)
    num_chords = int(np.ceil(duration / chord_dur))
    for i in range(num_chords):
        chord = chords[i % len(chords)]
        start_t = i * chord_dur
        end_t = min((i + 1) * chord_dur, duration)
        mask = (t >= start_t) & (t < end_t)
        tt = t[mask] - start_t
        # Soft attack/release envelope
        env = np.ones(len(tt))
        atk = min(0.5, len(tt) / SR / 3)
        rel = min(0.5, len(tt) / SR / 3)
        if int(atk * SR) > 0:
            env[: int(atk * SR)] = np.linspace(0, 1, int(atk * SR))
        if int(rel * SR) > 0:
            env[-int(rel * SR) :] = np.linspace(1, 0, int(rel * SR))
        for j, freq in enumerate(chord):
            s[mask] += amps[j] * np.sin(2 * np.pi * freq * tt) * env

    # Low frequency pad (C2)
    s += 0.018 * np.sin(2 * np.pi * 65.41 * t)

    # LFO volume modulation (0.1Hz, slow breathing)
    s *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.1 * t)

    # Segment volume: lower during narration, higher in gaps
    vol = np.ones(n) * 0.55  # default gap volume
    for seg in timeline:
        tts_s = seg["tts_start"]
        tts_e = tts_s + seg["tts_duration"]
        # Lower volume during narration
        m = (t >= tts_s - 0.3) & (t < tts_e + 0.5)
        vol[m] = 0.22  # BGM ducked during narration
        # Smooth transition
        trans = 0.3
        m_pre = (t >= tts_s - 0.3 - trans) & (t < tts_s - 0.3)
        vol[m_pre] = np.linspace(0.55, 0.22, m_pre.sum())
        m_post = (t >= tts_e + 0.5) & (t < tts_e + 0.5 + trans)
        vol[m_post] = np.linspace(0.22, 0.55, m_post.sum())

    s *= vol

    # Tail fade out (last 4 seconds)
    fade_start = duration - 4
    fm = t >= fade_start
    s[fm] *= np.maximum(0, 1 - (t[fm] - fade_start) / 4)

    # Subtle texture noise
    np.random.seed(42)
    s += np.random.uniform(-1, 1, n) * 0.0008

    return np.clip(s, -1, 1)


def mix_audio(duration, layers):
    """Mix multiple audio layers with tanh soft limiting."""
    n = int(duration * SR)
    mixed = np.zeros(n)
    for start, samples, vol in layers:
        s_idx = int(start * SR)
        length = min(len(samples), n - s_idx)
        if length > 0:
            mixed[s_idx : s_idx + length] += samples[:length] * vol
    return np.tanh(mixed * 0.9)


def sec2ass(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    cs = int((s * 100) % 100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"


def gen_ass(timeline, total_duration, output_path):
    """Generate ASS subtitles aligned with TTS narration timeline."""
    lines = [
        "[Script Info]",
        "Title: MedSignal Demo",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # Main subtitle: white text, black outline, bottom center
        "Style: main,Microsoft YaHei,52,&H00FFFFFF,&HFF000000,&H00000000,"
        "&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,120,120,90,1",
        # Ending subtitle: larger, bold, orange highlight
        "Style: ending,Microsoft YaHei,64,&H00FFFFFF,&HFF000000,&H00000000,"
        "&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,120,120,200,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text",
    ]

    for seg in timeline:
        start = seg["tts_start"]
        tts_dur = seg["tts_duration"]
        end = start + tts_dur + 0.3  # 0.3s tail after narration
        text = seg["text"]
        style = "ending" if seg["id"] == "s08_ending" else "main"

        # Typewriter effect: \kf per character
        char_count = max(len(text), 1)
        dpc = (end - start) / char_count * 100
        typed = "".join(f"{{\\kf{dpc:.0f}}}{c}" for c in text)
        typed = f"{{\\fad(150,100)}}{typed}"

        lines.append(
            f"Dialogue: 0,{sec2ass(start)},{sec2ass(end)},{style},,0,0,0,,{typed}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"ASS subtitles saved: {output_path}")


def main():
    print("=== Step 1: Convert TTS MP3 to WAV ===")
    tts_wavs = []
    for seg in TIMELINE:
        mp3 = seg["mp3_path"]
        wav = mp3.replace(".mp3", ".wav")
        mp3_to_wav(mp3, wav)
        samples = read_wav(wav)
        tts_wavs.append(samples)
        print(f"  {seg['id']}: {len(samples) / SR:.2f}s")

    print("\n=== Step 2: Generate BGM ===")
    bgm = gen_bgm(TOTAL_DUR, TIMELINE)
    bgm_path = os.path.join(AUDIO_DIR, "bgm.wav")
    write_wav(bgm, bgm_path)
    print(f"  BGM: {len(bgm) / SR:.2f}s -> {bgm_path}")

    print("\n=== Step 3: Mix TTS + BGM ===")
    layers = [(0.0, bgm, 1.0)]  # BGM full volume (already adjusted)
    for seg, samples in zip(TIMELINE, tts_wavs):
        layers.append((seg["tts_start"], samples, 0.85))  # TTS at 85% volume
    mixed = mix_audio(TOTAL_DUR, layers)
    mixed_path = os.path.join(AUDIO_DIR, "mixed.wav")
    write_wav(mixed, mixed_path, ch=2)  # stereo output
    print(f"  Mixed: {len(mixed) / SR:.2f}s -> {mixed_path}")

    print("\n=== Step 4: Generate ASS subtitles ===")
    ass_path = os.path.join(WORKDIR, "subs.ass")
    gen_ass(TIMELINE, TOTAL_DUR, ass_path)

    print(f"\n=== Done! Total: {TOTAL_DUR:.2f}s ===")
    print(f"  Audio: {mixed_path}")
    print(f"  Subs:  {ass_path}")


if __name__ == "__main__":
    main()
