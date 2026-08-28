#!/usr/bin/env python3
"""Generate TTS narration segments and measure actual durations."""

import subprocess
import json
import os
import time
import sys

EDGE_TTS = "edge-tts"
VOICE = "zh-CN-YunxiNeural"
TTS_DIR = "D:/APPs/VentureDhealthcare/video-demo/remake/tts"
RATE = "-5%"  # slightly slower for clarity

# Narration segments: (id, text, allocated_seconds)
NARRATIONS = [
    ("s01_pain", "交了这么多年医保，用的时候却看不懂。", 8.0),
    ("s02_title", "MedSignal，多模态医疗信号智能体，关键医疗信号识别。", 7.0),
    ("s03_home", "登录即推送健康预警，从被动报销到主动健康。", 15.0),
    ("s04_eeg", "脑血管、认知、精神三大风险量化，每条预警可展开证据。", 20.0),
    ("s05_policy", "脑电异常自动推荐医保政策，一年可省数千元。", 15.0),
    ("s06_imaging", "AI检测框与医师复核，医师在环的安全闭环。", 13.0),
    ("s07_multi", "多智能体协作，可信数据空间，可用不可见。", 8.0),
    ("s08_ending", "让关键医疗信号，不再被错过。", 4.0),
]


def generate_tts(text, output_path, retries=3):
    """Generate TTS with retry mechanism."""
    for attempt in range(retries):
        cmd = [EDGE_TTS, "--voice", VOICE, "--text", text, "--write-media", output_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if (
                result.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 0
            ):
                return True
            print(
                f"  Attempt {attempt + 1} failed: rc={result.returncode}",
                file=sys.stderr,
            )
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(f"  Attempt {attempt + 1} timed out", file=sys.stderr)
        time.sleep(0.5)
    return False


def get_duration(path):
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{path}"',
        shell=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def main():
    os.makedirs(TTS_DIR, exist_ok=True)
    results = []

    for seg_id, text, alloc in NARRATIONS:
        mp3_path = os.path.join(TTS_DIR, f"{seg_id}.mp3")
        print(f"Generating TTS: {seg_id} ...")

        if not generate_tts(text, mp3_path):
            print(f"FAILED: {seg_id}", file=sys.stderr)
            sys.exit(1)

        duration = get_duration(mp3_path)
        results.append(
            {
                "id": seg_id,
                "text": text,
                "alloc": alloc,
                "tts_duration": round(duration, 3),
                "mp3_path": mp3_path.replace("\\", "/"),
            }
        )
        print(f"  OK: {duration:.2f}s (alloc {alloc}s)")

    # Design timeline based on actual TTS durations
    # Key principle: narration must fit within allocated time
    # If TTS is longer than alloc, extend the segment
    timeline = []
    cursor = 0.0
    for r in results:
        seg_duration = max(
            r["alloc"], r["tts_duration"] + 1.0
        )  # +1s padding after narration
        timeline.append(
            {
                "id": r["id"],
                "text": r["text"],
                "start": round(cursor, 3),
                "duration": round(seg_duration, 3),
                "end": round(cursor + seg_duration, 3),
                "tts_start": round(
                    cursor + 0.5, 3
                ),  # 0.5s delay before narration starts
                "tts_duration": r["tts_duration"],
                "mp3_path": r["mp3_path"],
            }
        )
        cursor += seg_duration

    total = cursor
    print(f"\nTotal duration: {total:.2f}s")

    # Output timeline JSON
    timeline_path = os.path.join(TTS_DIR, "..", "timeline.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(
            {"total_duration": total, "segments": timeline},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Timeline saved to: {timeline_path}")

    # Print summary
    for t in timeline:
        print(
            f"  {t['id']}: {t['start']:.1f}-{t['end']:.1f} ({t['duration']:.1f}s) "
            f"tts@{t['tts_start']:.1f}+{t['tts_duration']:.1f}s"
        )


if __name__ == "__main__":
    main()
